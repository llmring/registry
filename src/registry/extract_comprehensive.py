#!/usr/bin/env python3
"""Comprehensive extraction from both HTML and PDF sources with consensus merging."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import click

from .extract_with_llm import (
    extract_models_from_html,
    validate_extracted_models,
)
from .extraction.pdf_parser import PDFParser, ModelInfo
from .extraction.confidence import (
    merge_with_consensus,
    calculate_confidence_summary,
)


def _html_models_to_keyed(provider: str, models: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    keyed: Dict[str, Dict[str, Any]] = {}
    for m in models:
        name = m.get("model_name") or m.get("model_id")
        if not name:
            continue
        key = f"{provider}:{name}"
        m["provider"] = provider
        keyed[key] = m
    return keyed


def _pdf_model_to_registry_dict(provider: str, m: ModelInfo) -> Dict[str, Any]:
    # Map ModelInfo to registry model schema
    model: Dict[str, Any] = {
        "provider": provider,
        "model_name": m.model_id,
        "display_name": m.display_name,
        "description": m.description,
        # Pricing
        "dollars_per_million_tokens_input": m.dollars_per_million_tokens_input,
        "dollars_per_million_tokens_output": m.dollars_per_million_tokens_output,
        # Token limits
        "max_input_tokens": None,
        "max_output_tokens": m.max_output_tokens,
        "context_window_tokens": m.max_context or m.context_window_tokens,
        # Capabilities
        "supports_vision": m.supports_vision,
        "supports_function_calling": m.supports_function_calling,
        "supports_json_mode": m.supports_json_mode,
        "supports_parallel_tool_calls": m.supports_parallel_tool_calls,
        "supports_streaming": m.supports_streaming,
        "supports_audio": m.supports_audio,
        "supports_documents": m.supports_documents,
        "supports_json_schema": m.supports_json_schema,
        "supports_logprobs": m.supports_logprobs,
        "supports_multiple_responses": m.supports_multiple_responses,
        "supports_caching": m.supports_caching,
        "is_reasoning_model": m.is_reasoning_model,
        # Characteristics
        "speed_tier": m.speed_tier,
        "intelligence_tier": m.intelligence_tier,
        "requires_tier": m.requires_tier,
        "requires_waitlist": m.requires_waitlist,
        "model_family": m.model_family,
        "recommended_use_cases": m.recommended_use_cases,
        # Status & dates
        "is_active": m.is_active,
        "release_date": m.release_date,
        "deprecated_date": getattr(m, "deprecation_date", None),
        "added_date": m.added_date,
    }
    return model


def _pdf_models_to_keyed(provider: str, models: List[ModelInfo]) -> Dict[str, Dict[str, Any]]:
    keyed: Dict[str, Dict[str, Any]] = {}
    for m in models:
        if not m.model_id:
            continue
        key = f"{provider}:{m.model_id}"
        keyed[key] = _pdf_model_to_registry_dict(provider, m)
    return keyed


@click.command(name="extract-comprehensive")
@click.option(
    "--provider",
    type=click.Choice(["openai", "anthropic", "google", "all"]),
    default="all",
    help="Provider to extract",
)
@click.option(
    "--html-dir",
    default="cache/html",
    type=click.Path(),
    help="Directory containing HTML files",
)
@click.option(
    "--pdf-dir",
    default="cache/pdfs",
    type=click.Path(),
    help="Directory containing PDF files",
)
@click.option(
    "--drafts-dir",
    default="drafts",
    type=click.Path(),
    help="Directory to write draft files",
)
@click.option(
    "--validate/--no-validate",
    default=True,
    help="Run validation pass on HTML extracted models",
)
@click.option("--timeout", default=60, help="Per-PDF extraction timeout in seconds")
def extract_comprehensive(provider: str, html_dir: str, pdf_dir: str, drafts_dir: str, validate: bool, timeout: int):
    """Extract from both HTML and PDF, merge with consensus, and write a draft JSON."""
    import asyncio

    async def run():
        providers = [provider] if provider != "all" else ["openai", "anthropic", "google"]
        html_path = Path(html_dir)
        pdf_path = Path(pdf_dir)
        drafts_path = Path(drafts_dir)
        # Auto-create directories if missing
        html_path.mkdir(exist_ok=True)
        pdf_path.mkdir(exist_ok=True)
        drafts_path.mkdir(exist_ok=True)

        for prov in providers:
            click.echo(f"\n🧪 Comprehensive extraction for {prov}...")

            # HTML extraction
            # Prefer rendered files when present
            html_files = sorted(html_path.glob(f"*{prov}*.rendered.html")) or sorted(html_path.glob(f"*{prov}*.html"))
            html_models: List[Dict[str, Any]] = []
            for html_file in html_files:
                click.echo(f"  🌐 HTML: {html_file.name}")
                content = html_file.read_text(encoding="utf-8")
                models = await extract_models_from_html(prov, content)
                if models:
                    html_models.extend(models)
            if validate and html_models:
                click.echo(f"  🔍 Validating {len(html_models)} HTML models...")
                html_models = await validate_extracted_models(html_models, prov)

            html_keyed = _html_models_to_keyed(prov, html_models)

            # PDF extraction
            pdf_files = list(pdf_path.glob(f"*{prov}*.pdf"))
            click.echo(f"  📚 PDFs found: {len(pdf_files)}")
            parser = PDFParser()
            click.echo("  ⏳ Parsing PDFs (with timeouts)...")
            # Use async parser to avoid nested asyncio.run() inside our event loop
            pdf_models = await parser.parse_provider_docs_async(prov, pdf_files, timeout_seconds=timeout)
            pdf_keyed = _pdf_models_to_keyed(prov, pdf_models)

            # Merge with consensus
            merged = merge_with_consensus(html_keyed, pdf_keyed)
            confidence_summary = calculate_confidence_summary(merged)

            # Write draft
            date_str = datetime.now().strftime("%Y-%m-%d")
            output_file = drafts_path / f"{prov}.{date_str}.draft.json"
            draft_data = {
                "provider": prov,
                "extraction_date": datetime.now().isoformat(),
                "sources": {"html": len(html_keyed), "pdf": len(pdf_keyed)},
                "models": merged,
                "confidence_summary": confidence_summary,
            }
            output_file.write_text(json.dumps(draft_data, indent=2))
            click.echo(f"  ✅ Draft written: {output_file}")

        click.echo("\n✨ Comprehensive extraction complete. Use 'review-draft' to review changes.")

    asyncio.run(run())


if __name__ == "__main__":
    extract_comprehensive()


