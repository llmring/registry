#!/usr/bin/env python3
"""Automated validation of extracted models against source documentation.

This validator compares the generated draft JSON with the per-source
`.extracted.json` snapshots that were produced during extraction.

Usage:
    uv run llmring-registry validate --provider openai --draft drafts/openai.2025-09-21.draft.json
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import click

from .schema_utils import normalize_model_data

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
    """Validates extracted models against source documentation using local snapshots."""

    def __init__(self, debug: bool = False):
        self.debug = debug
        if debug:
            logging.basicConfig(level=logging.DEBUG)

    @staticmethod
    def _is_paid_model(model: Dict[str, Any]) -> bool:
        try:
            input_price = float(model.get("dollars_per_million_tokens_input", 0))
            output_price = float(model.get("dollars_per_million_tokens_output", 0))
        except (TypeError, ValueError):
            return False
        return input_price > 0 and output_price > 0

    def _merge_model_record(self, existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        merged = existing.copy()

        pricing_fields = {
            "dollars_per_million_tokens_input",
            "dollars_per_million_tokens_output",
            "dollars_per_million_tokens_cached_input",
            "dollars_per_million_tokens_cache_write_5m",
            "dollars_per_million_tokens_cache_write_1h",
            "dollars_per_million_tokens_cache_read",
            "dollars_per_million_tokens_input_long_context",
            "dollars_per_million_tokens_output_long_context",
            "dollars_per_million_tokens_output_thinking",
            "cache_storage_cost_per_million_tokens_per_hour",
        }

        for field in pricing_fields:
            if field not in new:
                continue
            try:
                value = float(new[field])
            except (TypeError, ValueError):
                continue
            if value > 0:
                merged[field] = value

        int_fields = {"max_input_tokens", "max_output_tokens", "requires_tier", "long_context_threshold_tokens"}
        for field in int_fields:
            if field in new and new[field] is not None:
                try:
                    merged[field] = int(new[field])
                except (TypeError, ValueError):
                    continue

        list_fields = {"model_aliases", "recommended_use_cases"}
        for field in list_fields:
            if field in new and new[field] is not None:
                merged[field] = list(new[field])

        bool_fields = [key for key in new.keys() if key.startswith("supports_") or key in {"is_active", "requires_waitlist"}]
        for field in bool_fields:
            merged[field] = bool(new.get(field))

        for field, value in new.items():
            if field in pricing_fields or field in int_fields or field in list_fields or field in bool_fields:
                continue
            if value is not None:
                merged[field] = value

        return merged

    def _load_expected_models(self, provider: str, sources_dir: Path) -> Dict[str, Dict[str, Any]]:
        expected: Dict[str, Dict[str, Any]] = {}
        base_dir = sources_dir / provider
        if not base_dir.exists():
            return expected

        snapshot_files = sorted(base_dir.glob("*.extracted.json"))
        if not snapshot_files:
            snapshot_files = sorted(base_dir.glob("*.md"))
        for snapshot in snapshot_files:
            try:
                text = snapshot.read_text()
            except Exception as exc:
                logger.warning(f"Failed to read snapshot {snapshot}: {exc}")
                continue

            def _normalize_entries(raw_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
                normalized: List[Dict[str, Any]] = []
                for entry in raw_entries:
                    if not isinstance(entry, dict):
                        continue
                    normalized.append(normalize_model_data(entry))
                return normalized

            entries: List[Dict[str, Any]] = []
            if snapshot.suffix == ".md":
                block = self._extract_json_from_markdown(text)
                if block:
                    try:
                        parsed = json.loads(block)
                        if isinstance(parsed, dict) and isinstance(parsed.get("models"), dict):
                            entries = _normalize_entries(list(parsed["models"].values()))
                        elif isinstance(parsed, list):
                            entries = _normalize_entries(parsed)
                    except json.JSONDecodeError:
                        continue
            else:
                try:
                    parsed = json.loads(text)
                except Exception as exc:
                    logger.warning(f"Failed to parse JSON snapshot {snapshot}: {exc}")
                    continue

                if isinstance(parsed, dict) and isinstance(parsed.get("models"), dict):
                    entries = _normalize_entries(list(parsed["models"].values()))
                elif isinstance(parsed, list):
                    entries = _normalize_entries(parsed)
                else:
                    continue

            for model in entries:
                if not isinstance(model, dict):
                    continue
                if not self._is_paid_model(model):
                    continue
                model_name = model.get("model_name")
                if not model_name:
                    continue

                if model_name in expected:
                    expected[model_name] = self._merge_model_record(expected[model_name], model)
                else:
                    expected[model_name] = model

        return expected

    @staticmethod
    def _extract_json_from_markdown(text: str) -> Optional[str]:
        marker = "<JSON>"
        end_marker = "</JSON>"
        start = text.find(marker)
        if start == -1:
            return None
        start += len(marker)
        end = text.find(end_marker, start)
        if end == -1:
            return None
        return text[start:end].strip()

    def _to_float(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _to_int(self, value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _compare_models(
        self,
        model_key: str,
        expected: Dict[str, Any],
        actual: Dict[str, Any]
    ) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        pricing_fields = {
            "dollars_per_million_tokens_input",
            "dollars_per_million_tokens_output",
            "dollars_per_million_tokens_cached_input",
            "dollars_per_million_tokens_cache_write_5m",
            "dollars_per_million_tokens_cache_write_1h",
            "dollars_per_million_tokens_cache_read",
            "dollars_per_million_tokens_input_long_context",
            "dollars_per_million_tokens_output_long_context",
            "dollars_per_million_tokens_output_thinking",
            "cache_storage_cost_per_million_tokens_per_hour",
        }
        int_fields = {"max_input_tokens", "max_output_tokens", "requires_tier", "long_context_threshold_tokens"}
        list_fields = {"model_aliases", "recommended_use_cases"}

        for field, expected_value in expected.items():
            actual_value = actual.get(field)

            if field in pricing_fields:
                expected_float = self._to_float(expected_value)
                actual_float = self._to_float(actual_value)
                if expected_float is None:
                    continue
                if actual_float is None or abs(expected_float - actual_float) > 1e-6:
                    issues.append(ValidationIssue(
                        model_key=model_key,
                        severity="error",
                        field=field,
                        issue=f"Expected {expected_float}, found {actual_value}",
                        suggested_fix=f"Set {field} to {expected_float}"
                    ))
                continue

            if field in int_fields:
                expected_int = self._to_int(expected_value)
                actual_int = self._to_int(actual_value)
                if expected_int is None:
                    continue
                if actual_int != expected_int:
                    issues.append(ValidationIssue(
                        model_key=model_key,
                        severity="error",
                        field=field,
                        issue=f"Expected {expected_int}, found {actual_value}",
                        suggested_fix=f"Set {field} to {expected_int}"
                    ))
                continue

            if field in list_fields:
                expected_list = expected_value or []
                actual_list = actual_value or []
                if sorted(expected_list) != sorted(actual_list):
                    issues.append(ValidationIssue(
                        model_key=model_key,
                        severity="warning",
                        field=field,
                        issue=f"Expected {expected_list}, found {actual_list}",
                        suggested_fix=f"Update {field} to {expected_list}"
                    ))
                continue

            if field.startswith("supports_") or field in {"is_active", "requires_waitlist"}:
                expected_bool = bool(expected_value)
                actual_bool = bool(actual_value)
                if expected_bool != actual_bool:
                    issues.append(ValidationIssue(
                        model_key=model_key,
                        severity="error",
                        field=field,
                        issue=f"Expected {expected_bool}, found {actual_bool}",
                        suggested_fix=f"Set {field} to {expected_bool}"
                    ))
                continue

            # Compare strings or other scalar values
            if expected_value is not None and actual_value is not None:
                if str(expected_value).strip() != str(actual_value).strip():
                    issues.append(ValidationIssue(
                        model_key=model_key,
                        severity="warning",
                        field=field,
                        issue=f"Expected '{expected_value}', found '{actual_value}'",
                        suggested_fix=f"Update {field} to '{expected_value}'"
                    ))
            elif expected_value is not None and actual_value is None:
                issues.append(ValidationIssue(
                    model_key=model_key,
                    severity="warning",
                    field=field,
                    issue=f"Expected value '{expected_value}' but field is missing",
                    suggested_fix=f"Add {field} with value '{expected_value}'"
                ))

        return issues

    def validate(
        self,
        provider: str,
        draft_path: Path,
        sources_dir: Path
    ) -> Dict[str, Any]:
        with open(draft_path) as f:
            draft_data = json.load(f)

        draft_models = draft_data.get("models", {})
        draft_by_name = {}
        for key, model in draft_models.items():
            name = model.get("model_name")
            if name:
                draft_by_name[name] = (key, model)

        expected_map = self._load_expected_models(provider, sources_dir)

        click.echo(f"\n🔍 Validating {len(draft_models)} models for {provider} using local snapshots...")

        results: List[ModelValidationResult] = []
        all_issues: List[ValidationIssue] = []

        for key, model in draft_models.items():
            model_name = model.get("model_name")
            if not model_name:
                issue = ValidationIssue(
                    model_key=key,
                    severity="error",
                    field="model_name",
                    issue="Model entry missing model_name"
                )
                all_issues.append(issue)
                results.append(ModelValidationResult(key, False, [issue], 0.0))
                continue

            expected = expected_map.get(model_name)
            if not expected:
                issue = ValidationIssue(
                    model_key=key,
                    severity="error",
                    field="model_name",
                    issue="No extracted data found for this model"
                )
                all_issues.append(issue)
                results.append(ModelValidationResult(key, False, [issue], 0.0))
                continue

            issues = self._compare_models(key, expected, model)
            if issues:
                all_issues.extend(issues)
                results.append(ModelValidationResult(key, False, issues, 0.0))
            else:
                results.append(ModelValidationResult(key, True, [], 1.0))

        # Detect models present in documentation but missing in draft
        for model_name, expected in expected_map.items():
            if model_name not in draft_by_name:
                issue = ValidationIssue(
                    model_key=f"{provider}:{model_name}",
                    severity="error",
                    field="model_name",
                    issue="Model extracted from documentation but missing in draft",
                    suggested_fix="Add this model to the draft or confirm it should be excluded"
                )
                all_issues.append(issue)
                results.append(ModelValidationResult(f"{provider}:{model_name}", False, [issue], 0.0))

        total_models = len(draft_models)
        valid_models = sum(1 for r in results if r.is_valid)
        models_with_errors = sum(1 for r in results if any(i.severity == "error" for i in r.issues))
        models_with_warnings = sum(1 for r in results if not any(i.severity == "error" for i in r.issues) and r.issues)

        report = {
            "provider": provider,
            "draft_file": str(draft_path),
            "validation_date": datetime.now().isoformat(),
            "summary": {
                "total_models": total_models,
                "valid_models": valid_models,
                "models_with_errors": models_with_errors,
                "models_with_warnings": models_with_warnings,
                "average_confidence": sum(r.confidence_score for r in results) / len(results) if results else 0.0
            },
            "issues": [
                {
                    "model": issue.model_key,
                    "severity": issue.severity,
                    "field": issue.field,
                    "issue": issue.issue,
                    "suggested_fix": issue.suggested_fix
                }
                for issue in all_issues
            ],
            "model_results": [
                {
                    "model_key": r.model_key,
                    "is_valid": r.is_valid,
                    "confidence": r.confidence_score,
                    "issues": [
                        {
                            "severity": i.severity,
                            "field": i.field,
                            "issue": i.issue,
                            "suggested_fix": i.suggested_fix
                        }
                        for i in r.issues
                    ]
                }
                for r in results
            ]
        }

        return report


@click.command(name="validate")
@click.option("--provider", required=True, help="Provider to validate")
@click.option("--draft", type=click.Path(exists=True), help="Draft file to validate (auto-detected if not provided)")
@click.option("--drafts-dir", default="drafts", type=click.Path(), help="Directory containing drafts")
@click.option("--sources-dir", default="sources", type=click.Path(), help="Directory containing source documents")
@click.option("--output", type=click.Path(), help="Output path for validation report (default: drafts/<provider>.validation.json)")
@click.option("--debug", is_flag=True, help="Enable debug logging")
def validate_command(
    provider: str,
    draft: Optional[str],
    drafts_dir: str,
    sources_dir: str,
    output: Optional[str],
    debug: bool
):
    """Validate a draft against the locally extracted source snapshots."""
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
        report = validator.validate(
            provider=provider,
            draft_path=draft_path,
            sources_dir=sources_path
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