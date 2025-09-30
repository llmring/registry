#!/usr/bin/env python3
"""Automated validation of extracted models against source documentation.

This tool performs per-model validation by having an LLM:
1. Review each model's extracted data
2. Check it against the source documents
3. Flag any inconsistencies or missing data
4. Suggest corrections

Usage:
    uv run llmring-registry validate --provider openai --draft drafts/openai.2025-09-21.draft.json
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
from llmring import LLMRing
from llmring.file_utils import create_file_content
from llmring.schemas import LLMRequest, Message

logger = logging.getLogger(__name__)


@dataclass
class ValidationIssue:
    """A validation issue found for a model."""
    model_key: str
    severity: str  # "error", "warning", "info"
    field: Optional[str]
    issue: str
    suggested_fix: Optional[str] = None


@dataclass
class ModelValidationResult:
    """Result of validating a single model."""
    model_key: str
    is_valid: bool
    issues: List[ValidationIssue]
    confidence_score: float  # 0.0 to 1.0


class ModelValidator:
    """Validates extracted models against source documentation using LLM."""

    def __init__(self, debug: bool = False):
        """Initialize validator with LLMRing."""
        self.service = LLMRing()
        self.debug = debug
        if debug:
            logging.basicConfig(level=logging.DEBUG)

    def _validation_response_schema(self) -> dict:
        """Schema for validation response."""
        return {
            "type": "object",
            "properties": {
                "is_valid": {
                    "type": "boolean",
                    "description": "Whether the model data appears correct overall"
                },
                "confidence_score": {
                    "type": "number",
                    "description": "Confidence in validation (0.0 to 1.0)"
                },
                "issues": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "severity": {
                                "type": "string",
                                "enum": ["error", "warning", "info"],
                                "description": "Severity level"
                            },
                            "field": {
                                "type": "string",
                                "description": "Field with issue (or 'general')"
                            },
                            "issue": {
                                "type": "string",
                                "description": "Description of the issue"
                            },
                            "suggested_fix": {
                                "type": "string",
                                "description": "Suggested correction (if applicable)"
                            }
                        },
                        "required": ["severity", "field", "issue"]
                    }
                }
            },
            "required": ["is_valid", "confidence_score", "issues"]
        }

    def _create_validation_prompt(self, provider: str, model_data: dict) -> str:
        """Create validation prompt for a single model."""
        model_json = json.dumps(model_data, indent=2)

        return f"""You are validating extracted model data against {provider} documentation.

EXTRACTED MODEL DATA:
{model_json}

VALIDATION CHECKLIST:

1. **Model Name & Identification**
   - Is model_name the correct API identifier?
   - Are model_aliases appropriate (if any)?
   - Does display_name match official naming?

2. **Pricing** (CRITICAL)
   - Are dollars_per_million_tokens_input/output correct?
   - If pricing tier shown (free/paid), is PAID tier used?
   - Conversion correct? (e.g., $2.50/1M tokens = 2.50)
   - NEVER suggest price changes unless you see explicit pricing in the docs

3. **Token Limits** (CRITICAL)
   - max_input_tokens should be context_window - max_output_tokens
   - NOT the same as context window!
   - Zero values are errors unless model truly has no limit

4. **Capabilities**
   - supports_vision: check if multimodal
   - supports_function_calling: check for tool/function support
   - supports_json_mode: check for structured output
   - supports_streaming: most models support this
   - Other capability flags match documentation

5. **Description & Metadata**
   - Description captures key capabilities
   - Use cases appropriate (if provided)

RULES:
- Flag as ERROR if: pricing wrong, token limits obviously incorrect, model name wrong
- Flag as WARNING if: missing optional data, unclear capability
- Flag as INFO if: could add more detail but not wrong
- If you see zero prices or token limits, that's an ERROR (unless docs say unlimited)
- Only suggest fixes if you're certain from the documentation

Validate thoroughly and return structured results."""

    async def _validate_single_model(
        self,
        provider: str,
        model_key: str,
        model_data: dict,
        source_files: List[Path],
        timeout_seconds: int = 120
    ) -> ModelValidationResult:
        """Validate a single model against source documentation."""

        logger.info(f"Validating {model_key}")

        # Create prompt
        validation_prompt = self._create_validation_prompt(provider, model_data)

        # Prepare content with source documents
        # Use first document for now (could iterate through all)
        if source_files:
            # Find the most relevant document (prefer PDFs/screenshots with "pricing" or "models")
            relevant_docs = [f for f in source_files if any(keyword in f.name.lower()
                            for keyword in ['pricing', 'model', 'rate'])]
            if not relevant_docs:
                relevant_docs = source_files[:3]  # Use first 3 docs

            doc = relevant_docs[0]
            if doc.suffix.lower() == '.md':
                markdown_content = doc.read_text()
                content = f"{validation_prompt}\n\n--- SOURCE DOCUMENTATION ---\n{markdown_content}\n--- END ---"
            else:
                content = create_file_content(str(doc), validation_prompt)
        else:
            # No source docs available
            content = validation_prompt + "\n\nNote: No source documents available for validation."

        # Create request
        request = LLMRequest(
            messages=[Message(role="user", content=content)],
            model="validator",  # Use validator alias from lockfile
            temperature=0,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "validation_result",
                    "schema": self._validation_response_schema(),
                    "strict": True
                }
            }
        )

        # Call LLM with timeout
        try:
            response = await asyncio.wait_for(
                self.service.chat(request),
                timeout=timeout_seconds
            )

            # Parse response
            parsed = getattr(response, "parsed", None)
            if parsed:
                result_data = parsed
            else:
                result_data = json.loads(response.content)

            # Build result
            issues = []
            for issue_data in result_data.get("issues", []):
                issues.append(ValidationIssue(
                    model_key=model_key,
                    severity=issue_data["severity"],
                    field=issue_data.get("field", "general"),
                    issue=issue_data["issue"],
                    suggested_fix=issue_data.get("suggested_fix")
                ))

            return ModelValidationResult(
                model_key=model_key,
                is_valid=result_data.get("is_valid", False),
                issues=issues,
                confidence_score=result_data.get("confidence_score", 0.5)
            )

        except asyncio.TimeoutError:
            logger.error(f"Timeout validating {model_key}")
            return ModelValidationResult(
                model_key=model_key,
                is_valid=False,
                issues=[ValidationIssue(
                    model_key=model_key,
                    severity="error",
                    field="general",
                    issue="Validation timeout"
                )],
                confidence_score=0.0
            )
        except Exception as e:
            logger.error(f"Error validating {model_key}: {e}")
            return ModelValidationResult(
                model_key=model_key,
                is_valid=False,
                issues=[ValidationIssue(
                    model_key=model_key,
                    severity="error",
                    field="general",
                    issue=f"Validation failed: {str(e)}"
                )],
                confidence_score=0.0
            )

    async def validate_draft_async(
        self,
        draft_path: Path,
        sources_dir: Path,
        timeout_per_model: int = 120,
        sample_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Validate all models in a draft file.

        Args:
            draft_path: Path to draft JSON file
            sources_dir: Directory containing source documents
            timeout_per_model: Timeout in seconds per model validation
            sample_size: If set, only validate this many models (for testing)

        Returns:
            Validation report dict
        """
        # Load draft
        with open(draft_path) as f:
            draft_data = json.load(f)

        provider = draft_data.get("provider", "unknown")
        models = draft_data.get("models", {})

        click.echo(f"\n🔍 Validating {len(models)} models for {provider}...")

        # Find source documents
        provider_sources = sources_dir / provider
        source_files = []
        if provider_sources.exists():
            source_files.extend(provider_sources.glob("*.png"))
            source_files.extend(provider_sources.glob("*.pdf"))
            source_files.extend(provider_sources.glob("*.md"))
            source_files = sorted(source_files)

        if not source_files:
            click.echo(f"⚠️  No source documents found in {provider_sources}")
        else:
            click.echo(f"📁 Found {len(source_files)} source documents")

        # Sample if requested
        model_items = list(models.items())
        if sample_size and sample_size < len(model_items):
            import random
            model_items = random.sample(model_items, sample_size)
            click.echo(f"📊 Sampling {sample_size} models for validation")

        # Validate each model
        results: List[ModelValidationResult] = []
        for i, (model_key, model_data) in enumerate(model_items, 1):
            click.echo(f"  [{i}/{len(model_items)}] Validating {model_key}...")

            result = await self._validate_single_model(
                provider=provider,
                model_key=model_key,
                model_data=model_data,
                source_files=source_files,
                timeout_seconds=timeout_per_model
            )
            results.append(result)

            # Show immediate feedback
            if result.is_valid:
                click.echo(f"    ✅ Valid (confidence: {result.confidence_score:.2f})")
            else:
                click.echo(f"    ❌ Issues found: {len(result.issues)}")
                for issue in result.issues[:2]:  # Show first 2 issues
                    click.echo(f"       {issue.severity.upper()}: {issue.issue[:80]}")

        # Generate report
        total_models = len(results)
        valid_models = sum(1 for r in results if r.is_valid)
        models_with_errors = sum(1 for r in results if any(i.severity == "error" for i in r.issues))
        models_with_warnings = sum(1 for r in results if any(i.severity == "warning" for i in r.issues))

        all_issues = []
        for result in results:
            for issue in result.issues:
                all_issues.append({
                    "model": result.model_key,
                    "severity": issue.severity,
                    "field": issue.field,
                    "issue": issue.issue,
                    "suggested_fix": issue.suggested_fix
                })

        report = {
            "provider": provider,
            "draft_file": str(draft_path),
            "validation_date": datetime.now().isoformat(),
            "summary": {
                "total_models": total_models,
                "valid_models": valid_models,
                "models_with_errors": models_with_errors,
                "models_with_warnings": models_with_warnings,
                "average_confidence": sum(r.confidence_score for r in results) / total_models if results else 0
            },
            "issues": all_issues,
            "model_results": [
                {
                    "model_key": r.model_key,
                    "is_valid": r.is_valid,
                    "confidence": r.confidence_score,
                    "issue_count": len(r.issues)
                }
                for r in results
            ]
        }

        return report

    def validate_draft(
        self,
        draft_path: Path,
        sources_dir: Path,
        timeout_per_model: int = 120,
        sample_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """Synchronous wrapper for validation."""
        return asyncio.run(
            self.validate_draft_async(draft_path, sources_dir, timeout_per_model, sample_size)
        )


@click.command(name="validate")
@click.option("--provider", required=True, help="Provider to validate")
@click.option("--draft", type=click.Path(exists=True), help="Draft file to validate (auto-detected if not provided)")
@click.option("--drafts-dir", default="drafts", type=click.Path(), help="Directory containing drafts")
@click.option("--sources-dir", default="sources", type=click.Path(), help="Directory containing source documents")
@click.option("--output", type=click.Path(), help="Output path for validation report (default: drafts/<provider>.validation.json)")
@click.option("--timeout", default=120, help="Timeout per model in seconds (default: 120)")
@click.option("--sample", type=int, help="Validate only N random models (for testing)")
@click.option("--debug", is_flag=True, help="Enable debug logging")
def validate_command(
    provider: str,
    draft: Optional[str],
    drafts_dir: str,
    sources_dir: str,
    output: Optional[str],
    timeout: int,
    sample: Optional[int],
    debug: bool
):
    """Validate extracted models against source documentation.

    This command uses an LLM to validate each model in a draft file by:
    1. Checking the extracted data against source documentation
    2. Identifying errors, warnings, and missing data
    3. Suggesting corrections where possible

    The validation report is saved as JSON and can be reviewed before promotion.
    """
    drafts_path = Path(drafts_dir)
    sources_path = Path(sources_dir)

    # Find draft file
    if draft:
        draft_path = Path(draft)
    else:
        # Auto-detect latest draft for provider
        draft_files = sorted(
            drafts_path.glob(f"{provider}.*.draft.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        if not draft_files:
            raise click.ClickException(f"No draft found for provider '{provider}' in {drafts_dir}")
        draft_path = draft_files[0]
        click.echo(f"📄 Using draft: {draft_path.name}")

    # Determine output path
    if output:
        output_path = Path(output)
    else:
        output_path = drafts_path / f"{provider}.validation.json"

    # Run validation
    validator = ModelValidator(debug=debug)

    try:
        report = validator.validate_draft(
            draft_path=draft_path,
            sources_dir=sources_path,
            timeout_per_model=timeout,
            sample_size=sample
        )

        # Save report
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        # Display summary
        summary = report["summary"]
        click.echo(f"\n📊 Validation Summary:")
        click.echo(f"  Total models: {summary['total_models']}")
        click.echo(f"  ✅ Valid: {summary['valid_models']}")
        click.echo(f"  ❌ With errors: {summary['models_with_errors']}")
        click.echo(f"  ⚠️  With warnings: {summary['models_with_warnings']}")
        click.echo(f"  🎯 Avg confidence: {summary['average_confidence']:.2%}")

        # Show top issues
        if report["issues"]:
            click.echo(f"\n⚠️  Top Issues:")
            errors = [i for i in report["issues"] if i["severity"] == "error"]
            for issue in errors[:5]:
                click.echo(f"  - {issue['model']}: {issue['issue']}")
                if issue.get("suggested_fix"):
                    click.echo(f"    → Fix: {issue['suggested_fix']}")

        click.echo(f"\n💾 Full report saved: {output_path}")

        # Exit with error code if validation found critical issues
        if summary['models_with_errors'] > 0:
            click.echo(f"\n⚠️  Validation found {summary['models_with_errors']} models with errors")
            raise SystemExit(1)

    except Exception as e:
        click.echo(f"\n❌ Validation failed: {e}")
        if debug:
            import traceback
            traceback.print_exc()
        raise SystemExit(1)


if __name__ == "__main__":
    validate_command()