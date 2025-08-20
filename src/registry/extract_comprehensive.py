#!/usr/bin/env python3
"""Comprehensive model extraction using both HTML regex and PDF LLM extraction."""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import click

# Try to load .env file
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)


@dataclass
class ModelField:
    """Represents a single field with multiple possible values."""

    name: str
    html_value: Optional[Any] = None
    pdf_value: Optional[Any] = None
    agreed_value: Optional[Any] = None
    confidence: str = "uncertain"  # certain, probable, uncertain

    def get_consensus(self) -> Tuple[Optional[Any], str]:
        """Get consensus value and confidence level."""
        if self.html_value == self.pdf_value and self.html_value is not None:
            return self.html_value, "certain"
        elif self.html_value is not None and self.pdf_value is None:
            return self.html_value, "probable"
        elif self.pdf_value is not None and self.html_value is None:
            return self.pdf_value, "probable"
        else:
            # Disagreement or both None
            return None, "uncertain"


@dataclass
class ModelExtraction:
    """Complete extraction for a model from all sources."""

    model_id: str
    fields: Dict[str, ModelField] = field(default_factory=dict)

    def add_html_data(self, data: Dict[str, Any]):
        """Add data extracted from HTML."""
        for key, value in data.items():
            if key not in self.fields:
                self.fields[key] = ModelField(name=key)
            self.fields[key].html_value = value

    def add_pdf_data(self, data: Dict[str, Any]):
        """Add data extracted from PDF."""
        for key, value in data.items():
            if key not in self.fields:
                self.fields[key] = ModelField(name=key)
            self.fields[key].pdf_value = value

    def get_consensus_model(self) -> Dict[str, Any]:
        """Get the consensus model with confidence indicators."""
        result = {"model_id": self.model_id}
        uncertain_fields = []

        for field_name, field in self.fields.items():
            value, confidence = field.get_consensus()
            if value is not None:
                result[field_name] = value
                if confidence != "certain":
                    uncertain_fields.append(field_name)
            elif field.html_value is not None or field.pdf_value is not None:
                # Disagreement - include both values for transparency
                result[f"{field_name}_conflict"] = {
                    "html": field.html_value,
                    "pdf": field.pdf_value,
                }
                uncertain_fields.append(field_name)

        if uncertain_fields:
            result["_uncertain_fields"] = uncertain_fields

        return result


def extract_from_pdf_with_llm(pdf_path: Path, provider: str) -> List[Dict[str, Any]]:
    """
    Extract models from PDF using LLMRing's unified interface.

    LLMRing automatically handles:
    - Anthropic: Direct PDF support
    - OpenAI: Assistants API for PDFs
    - Google: Direct PDF support
    """
    models = []

    try:
        # Use the existing PDF extraction code with LLMRing
        from .extraction.pdf_parser import ModelInfo, PDFParser

        parser = PDFParser()  # Now uses LLMRing internally

        # Extract from PDF
        raw_models = parser.parse_provider_docs(provider, [pdf_path])

        # Convert ModelInfo objects to dictionaries
        for model in raw_models:
            if isinstance(model, ModelInfo):
                model_dict = {
                    "model_id": model.model_id,
                    "display_name": model.display_name,
                    "description": model.description,
                    "max_context": model.max_context,
                    "max_output_tokens": model.max_output_tokens,
                    "supports_vision": model.supports_vision,
                    "supports_function_calling": model.supports_function_calling,
                    "supports_json_mode": model.supports_json_mode,
                    "supports_parallel_tool_calls": model.supports_parallel_tool_calls,
                    "dollars_per_million_tokens_input": model.dollars_per_million_tokens_input,
                    "dollars_per_million_tokens_output": model.dollars_per_million_tokens_output,
                }
                # Add optional fields if present
                if model.use_cases:
                    model_dict["use_cases"] = model.use_cases
                if model.release_date:
                    model_dict["release_date"] = model.release_date
                if model.deprecation_date:
                    model_dict["deprecation_date"] = model.deprecation_date
                if model.notes:
                    model_dict["notes"] = model.notes
                models.append(model_dict)

    except ImportError as e:
        logger.warning(f"LLMRing not available: {e}")
        logger.warning("Install with: uv add llmring")
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")

    return models


# Removed provider-specific extraction functions - now using LLMRing's unified interface


def compare_extractions(
    html_models: List[Dict[str, Any]], pdf_models: List[Dict[str, Any]]
) -> Dict[str, ModelExtraction]:
    """
    Compare HTML and PDF extractions to find agreements and conflicts.
    """
    extractions = {}

    # Add HTML models
    for model in html_models:
        model_id = model.get("model_id")
        if model_id:
            if model_id not in extractions:
                extractions[model_id] = ModelExtraction(model_id)
            extractions[model_id].add_html_data(model)

    # Add PDF models
    for model in pdf_models:
        model_id = model.get("model_id")
        if model_id:
            if model_id not in extractions:
                extractions[model_id] = ModelExtraction(model_id)
            extractions[model_id].add_pdf_data(model)

    return extractions


def interactive_resolution(extraction: ModelExtraction) -> Dict[str, Any]:
    """
    Interactively resolve conflicts and uncertain fields.
    """
    click.echo(f"\n🔍 Resolving model: {extraction.model_id}")
    result = {"model_id": extraction.model_id}

    for field_name, field in extraction.fields.items():
        if field_name == "model_id":
            continue

        value, confidence = field.get_consensus()

        if confidence == "certain":
            result[field_name] = value
        else:
            click.echo(f"\n  Field: {field_name}")

            choices = []
            if field.html_value is not None:
                click.echo(f"    1) HTML extraction: {field.html_value}")
                choices.append(("1", field.html_value))
            if field.pdf_value is not None:
                click.echo(f"    2) PDF extraction: {field.pdf_value}")
                choices.append(("2", field.pdf_value))

            if not choices:
                click.echo("    No values found")
                manual = click.prompt(
                    "    Enter value (or press Enter to skip)",
                    default="",
                    show_default=False,
                )
                if manual:
                    result[field_name] = manual
            else:
                click.echo("    3) Enter different value")
                click.echo("    4) Skip this field")

                choice = click.prompt(
                    "    Choose option",
                    type=click.Choice([c[0] for c in choices] + ["3", "4"]),
                )

                if choice in [c[0] for c in choices]:
                    result[field_name] = next(c[1] for c in choices if c[0] == choice)
                elif choice == "3":
                    manual = click.prompt("    Enter value")
                    result[field_name] = manual
                # choice == "4" means skip

    return result


@click.command()
@click.option(
    "--provider",
    type=click.Choice(["openai", "anthropic", "google", "all"]),
    default="all",
    help="Provider to extract",
)
@click.option(
    "--html-dir", default="html_cache", help="Directory containing HTML files"
)
@click.option("--pdf-dir", default="pdfs", help="Directory containing PDF files")
@click.option("--models-dir", default="models", help="Directory to save model JSONs")
@click.option("--interactive", is_flag=True, help="Interactively resolve conflicts")
@click.option(
    "--llm-model",
    default="best",
    help="LLM model to use for PDF extraction (best/gpt-4o/claude-3-5-sonnet)",
)
def extract_comprehensive(
    provider, html_dir, pdf_dir, models_dir, interactive, llm_model
):
    """
    Extract models using both HTML regex and PDF LLM extraction.

    This command:
    1. Extracts from HTML using regex patterns
    2. Extracts from PDFs using the best available LLM
    3. Compares both extractions
    4. Marks fields as certain (both agree), probable (one source), or uncertain (conflict)
    5. Optionally allows interactive resolution of conflicts
    """
    from .extract_from_html import (
        extract_anthropic_models,
        extract_google_models,
        extract_openai_models,
    )

    providers = [provider] if provider != "all" else ["openai", "anthropic", "google"]
    html_path = Path(html_dir)
    pdf_path = Path(pdf_dir)
    models_path = Path(models_dir)
    models_path.mkdir(exist_ok=True)

    html_extractors = {
        "openai": extract_openai_models,
        "anthropic": extract_anthropic_models,
        "google": extract_google_models,
    }

    for prov in providers:
        click.echo(f"\n📊 Comprehensive extraction for {prov}")

        # Extract from HTML
        html_models = []
        html_files = list(html_path.glob(f"*{prov}*.html"))
        if html_files:
            click.echo(f"  📄 Extracting from {len(html_files)} HTML files...")
            for html_file in html_files:
                with open(html_file, "r", encoding="utf-8") as f:
                    html_content = f.read()
                extractor = html_extractors.get(prov)
                if extractor:
                    models = extractor(html_content)
                    html_models.extend(models)
            click.echo(f"     Found {len(html_models)} models from HTML")

        # Extract from PDFs
        pdf_models = []
        pdf_files = list(pdf_path.glob(f"*{prov}*.pdf"))
        if pdf_files:
            click.echo(f"  📑 Extracting from {len(pdf_files)} PDF files using LLM...")
            for pdf_file in pdf_files:
                models = extract_from_pdf_with_llm(pdf_file, prov)
                pdf_models.extend(models)
            click.echo(f"     Found {len(pdf_models)} models from PDFs")

        # Compare extractions
        extractions = compare_extractions(html_models, pdf_models)

        if not extractions:
            click.echo(f"  ⚠️  No models found for {prov}")
            continue

        # Report agreement statistics
        total_fields = 0
        certain_fields = 0
        conflicts = 0

        for model_id, extraction in extractions.items():
            for field_name, field in extraction.fields.items():
                if field_name == "model_id":
                    continue
                total_fields += 1
                value, confidence = field.get_consensus()
                if confidence == "certain":
                    certain_fields += 1
                elif (
                    field.html_value != field.pdf_value
                    and field.html_value
                    and field.pdf_value
                ):
                    conflicts += 1

        if total_fields > 0:
            click.echo(f"\n  📈 Extraction confidence:")
            click.echo(
                f"     Certain fields: {certain_fields}/{total_fields} ({certain_fields*100//total_fields}%)"
            )
            click.echo(f"     Conflicts: {conflicts}")

        # Resolve conflicts
        final_models = []
        for model_id, extraction in extractions.items():
            if interactive and conflicts > 0:
                model_data = interactive_resolution(extraction)
            else:
                model_data = extraction.get_consensus_model()
            final_models.append(model_data)

        # Save results
        output_data = {
            "provider": prov,
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "extraction_method": "comprehensive",
            "extraction_sources": {
                "html_files": [f.name for f in html_files],
                "pdf_files": [f.name for f in pdf_files],
            },
            "extraction_date": datetime.now().isoformat(),
            "extraction_confidence": {
                "certain_fields": certain_fields,
                "total_fields": total_fields,
                "conflicts": conflicts,
            },
            "models": final_models,
        }

        output_file = models_path / f"{prov}.json"
        with open(output_file, "w") as f:
            json.dump(output_data, f, indent=2)

        click.echo(f"\n  ✅ Saved {len(final_models)} models to {output_file}")

        # Show uncertain fields if any
        uncertain_count = sum(1 for m in final_models if "_uncertain_fields" in m)
        if uncertain_count > 0:
            click.echo(f"  ⚠️  {uncertain_count} models have uncertain fields")
            if not interactive:
                click.echo(f"     Run with --interactive to resolve conflicts")


if __name__ == "__main__":
    extract_comprehensive()
