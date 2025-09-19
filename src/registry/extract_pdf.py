#!/usr/bin/env python3
"""PDF-only extraction into drafts for later review/promotion."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import click

from .extraction.pdf_parser import PDFParser, ModelInfo


def _pdf_model_to_registry_dict(provider: str, m: ModelInfo) -> Dict[str, Any]:
    return {
        "provider": provider,
        "model_name": m.model_id,
        "display_name": m.display_name,
        "description": m.description,
        "dollars_per_million_tokens_input": m.dollars_per_million_tokens_input,
        "dollars_per_million_tokens_output": m.dollars_per_million_tokens_output,
        "max_input_tokens": None,
        "max_output_tokens": m.max_output_tokens,
        "context_window_tokens": m.max_context or m.context_window_tokens,
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
        "speed_tier": m.speed_tier,
        "intelligence_tier": m.intelligence_tier,
        "requires_tier": m.requires_tier,
        "requires_waitlist": m.requires_waitlist,
        "model_family": m.model_family,
        "recommended_use_cases": m.recommended_use_cases,
        "is_active": m.is_active,
        "release_date": m.release_date,
        "deprecated_date": getattr(m, "deprecation_date", None),
        "added_date": m.added_date,
    }


def _pdf_models_to_keyed(provider: str, models: List[ModelInfo]) -> Dict[str, Dict[str, Any]]:
    keyed: Dict[str, Dict[str, Any]] = {}
    for m in models:
        if not m.model_id:
            continue
        key = f"{provider}:{m.model_id}"
        keyed[key] = _pdf_model_to_registry_dict(provider, m)
    return keyed


@click.command(name="extract-pdf")
@click.option("--provider", type=click.Choice(["openai", "anthropic", "google", "all"]), default="all")
@click.option("--pdf-dir", default="cache/pdfs", type=click.Path())
@click.option("--drafts-dir", default="drafts", type=click.Path())
@click.option("--timeout", default=60, help="Per-PDF extraction timeout in seconds")
def extract_pdf(provider: str, pdf_dir: str, drafts_dir: str, timeout: int):
    """Extract models from PDFs only and write a draft file per provider."""
    providers = [provider] if provider != "all" else ["openai", "anthropic", "google"]
    pdf_path = Path(pdf_dir); pdf_path.mkdir(exist_ok=True)
    drafts_path = Path(drafts_dir); drafts_path.mkdir(exist_ok=True)

    parser = PDFParser()
    date_str = datetime.now().strftime("%Y-%m-%d")

    for prov in providers:
        click.echo(f"\n📄 PDF extraction for {prov}...")
        pdf_files = list(pdf_path.glob(f"*{prov}*.pdf"))
        click.echo(f"  📚 PDFs found: {len(pdf_files)}")
        models = parser.parse_provider_docs(prov, pdf_files, timeout_seconds=timeout)
        keyed = _pdf_models_to_keyed(prov, models)

        draft = {
            "provider": prov,
            "extraction_date": datetime.now().isoformat(),
            "sources": {"html": 0, "pdf": len(keyed)},
            "models": keyed,
        }
        out = drafts_path / f"{prov}.{date_str}.draft.json"
        out.write_text(json.dumps(draft, indent=2))
        click.echo(f"  ✅ Draft written: {out}")

    click.echo("\n✨ PDF extraction complete")


if __name__ == "__main__":
    extract_pdf()


