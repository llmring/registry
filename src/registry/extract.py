#!/usr/bin/env python3
"""Screenshot-based extraction into drafts for later review/promotion."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import click

from .document_parser import DocumentParser, ModelInfo
from .schema_utils import normalize_draft_file


def _screenshot_model_to_registry_dict(provider: str, m: ModelInfo) -> Dict[str, Any]:
    return {
        "provider": provider,
        "model_name": m.model_id,
        "display_name": m.display_name,
        "description": m.description,
        "model_aliases": m.model_aliases,  # Add model aliases
        "dollars_per_million_tokens_input": m.dollars_per_million_tokens_input,
        "dollars_per_million_tokens_output": m.dollars_per_million_tokens_output,
        "max_input_tokens": m.max_input_tokens,
        "max_output_tokens": m.max_output_tokens,
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


def _screenshot_models_to_keyed(provider: str, models: List[ModelInfo]) -> Dict[str, Dict[str, Any]]:
    keyed: Dict[str, Dict[str, Any]] = {}
    for m in models:
        if not m.model_id:
            continue
        key = f"{provider}:{m.model_id}"
        keyed[key] = _screenshot_model_to_registry_dict(provider, m)
    return keyed


@click.command(name="extract-from-documents")
@click.option("--provider", type=click.Choice(["openai", "anthropic", "google", "all"]), default="all")
@click.option("--sources-dir", default="sources", type=click.Path())
@click.option("--drafts-dir", default="drafts", type=click.Path())
@click.option("--timeout", default=180, help="Per-document extraction timeout in seconds (default: 180)")
@click.option("--debug", is_flag=True, help="Enable debug logging")
def extract_from_documents(provider: str, sources_dir: str, drafts_dir: str, timeout: int, debug: bool):
    """Extract models from various document types (PNG, PDF, MD) and write a draft file per provider."""
    import logging

    # Configure logging if debug flag is set
    if debug:
        logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')
        click.echo("🔍 Debug logging enabled")

    providers = [provider] if provider != "all" else ["openai", "anthropic", "google"]
    sources_path = Path(sources_dir)
    sources_path.mkdir(exist_ok=True)
    drafts_path = Path(drafts_dir)
    drafts_path.mkdir(exist_ok=True)

    parser = DocumentParser()
    date_str = datetime.now().strftime("%Y-%m-%d")

    # Track success/failure
    successful_providers = []
    failed_providers = []

    for prov in providers:
        click.echo(f"\n📄 Document extraction for {prov}...")

        # Look for documents in sources/[provider]
        provider_dir = sources_path / prov
        document_files = []

        if provider_dir.exists():
            # Get all supported document types
            png_files = sorted(provider_dir.glob("*.png"))
            pdf_files = sorted(provider_dir.glob("*.pdf"))
            md_files = sorted(provider_dir.glob("*.md"))
            document_files = png_files + pdf_files + md_files
            document_files.sort(key=lambda x: x.name)  # Sort all files alphabetically

        click.echo(f"  📁 Documents found: {len(document_files)}")
        if document_files:
            file_types = {}
            for f in document_files:
                ext = f.suffix.lower()
                file_types[ext] = file_types.get(ext, 0) + 1
            type_summary = ", ".join([f"{count} {ext}" for ext, count in file_types.items()])
            click.echo(f"  📊 File types: {type_summary}")
            click.echo(f"  📑 Processing order: {', '.join(f.name for f in document_files)}")

        models = parser.parse_provider_docs(prov, document_files, timeout_seconds=timeout)
        keyed = _screenshot_models_to_keyed(prov, models)

        # Post-processing: Set Anthropic-specific capabilities
        if prov == "anthropic" and keyed:
            for model_key in keyed:
                keyed[model_key]["supports_function_calling"] = True
                keyed[model_key]["supports_json_schema"] = True
                keyed[model_key]["supports_json_mode"] = True

        # Only write draft if we actually extracted something
        if keyed:
            # Count document types
            png_count = len([f for f in document_files if f.suffix.lower() == '.png'])
            pdf_count = len([f for f in document_files if f.suffix.lower() == '.pdf'])
            md_count = len([f for f in document_files if f.suffix.lower() == '.md'])

            draft = {
                "provider": prov,
                "extraction_date": datetime.now().isoformat(),
                "sources": {
                    "documents": len(document_files),
                    "png_files": png_count,
                    "pdf_files": pdf_count,
                    "md_files": md_count,
                    "models_extracted": len(keyed)
                },
                "models": keyed,
            }

            # Normalize the draft before writing
            draft = normalize_draft_file(draft)

            out = drafts_path / f"{prov}.{date_str}.draft.json"
            out.write_text(json.dumps(draft, indent=2))
            click.echo(f"  ✅ Draft written: {out} ({len(keyed)} models)")
            successful_providers.append(prov)
        else:
            click.echo(f"  ⚠️  No models extracted for {prov}, skipping draft")
            failed_providers.append(prov)

    # Final summary
    if successful_providers and not failed_providers:
        click.echo(f"\n✨ Document extraction complete for: {', '.join(successful_providers)}")
    elif failed_providers and not successful_providers:
        click.echo(f"\n❌ Document extraction failed for all providers: {', '.join(failed_providers)}")
        click.echo("   Check the errors above for details.")
    else:
        click.echo(f"\n⚠️  Mixed results:")
        if successful_providers:
            click.echo(f"   ✅ Successful: {', '.join(successful_providers)}")
        if failed_providers:
            click.echo(f"   ❌ Failed: {', '.join(failed_providers)}")


if __name__ == "__main__":
    extract_from_documents()


