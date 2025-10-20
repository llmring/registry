#!/usr/bin/env python3
"""Promotion utility to publish draft models to production with archiving."""

from __future__ import annotations

import json
import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple

import click

# Field categories for merging
PRICING_FIELDS = {
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
    "long_context_threshold_tokens",
}

CAPABILITY_FIELDS = {
    "supports_vision",
    "supports_function_calling",
    "supports_json_mode",
    "supports_parallel_tool_calls",
    "supports_streaming",
    "supports_audio",
    "supports_documents",
    "supports_json_schema",
    "supports_logprobs",
    "supports_multiple_responses",
    "supports_caching",
    "supports_thinking",
    "supports_long_context_pricing",
    "supports_temperature",
    "supports_system_message",
    "supports_pdf_input",
    "supports_tool_choice",
    "is_reasoning_model",
    "is_active",
    "deprecated_date",
    "release_date",
    "max_input_tokens",
    "max_output_tokens",
    "max_temperature",
    "min_temperature",
    "max_tools",
    "temperature_values",
    "speed_tier",
    "intelligence_tier",
    "requires_tier",
    "requires_waitlist",
    "model_family",
    "recommended_use_cases",
    "api_endpoint",
    "requires_flat_input",
    "tool_call_format",
}

# Fields that are always updated from draft (pricing + capabilities)
UPDATE_FIELDS = PRICING_FIELDS | CAPABILITY_FIELDS


def _merge_model(current: Dict[str, Any], draft: Dict[str, Any]) -> Dict[str, Any]:
    """Merge draft model into current model.

    Updates pricing and capability fields from draft, preserves all other fields
    from current model. Only updates fields where draft has non-null values.
    """
    merged = current.copy()

    # Update pricing and capability fields from draft
    for field in UPDATE_FIELDS:
        if field in draft and draft[field] is not None:
            merged[field] = draft[field]

    return merged


def _merge_registry(current: Dict[str, Any], draft: Dict[str, Any]) -> Dict[str, Any]:
    """Merge draft registry into current registry.

    - Models in draft: merge with current (if exists) or add new
    - Models not in draft: keep as-is

    Returns merged registry with updated models dict.
    """
    # Start with current registry structure
    merged = current.copy()

    current_models = current.get("models", {})
    draft_models = draft.get("models", {})

    # Create merged models dict
    merged_models = current_models.copy()

    for model_key, draft_model in draft_models.items():
        if model_key in current_models:
            # Merge draft into current
            merged_models[model_key] = _merge_model(current_models[model_key], draft_model)
        else:
            # New model - add it
            merged_models[model_key] = draft_model

    merged["models"] = merged_models

    # Update metadata from draft
    if "extraction_date" in draft:
        merged["extraction_date"] = draft["extraction_date"]
    if "sources" in draft:
        merged["sources"] = draft["sources"]

    return merged


def _load_json(path: Path) -> Dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def _canonicalize_json(data: Dict[str, Any]) -> bytes:
    # RFC8785 JSON Canonicalization Scheme (simplified: sort keys, no spaces)
    return json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _calculate_hash(data: Dict[str, Any]) -> str:
    return hashlib.sha256(_canonicalize_json(data)).hexdigest()


def _get_current_version(models_dir: Path, provider: str) -> int:
    file = models_dir / f"{provider}.json"
    if not file.exists():
        return 0
    try:
        data = _load_json(file)
        return int(data.get("version", 0))
    except Exception:
        return 0


def _validate_for_production(data: Dict[str, Any]) -> None:
    if "models" not in data or not isinstance(data["models"], dict):
        raise click.ClickException("Draft data missing 'models' dict")
    # Basic spot checks for required fields on some records
    for key, model in list(data["models"].items())[:5]:
        for req in ["model_name", "provider"]:
            if req not in model:
                raise click.ClickException(f"Model {key} missing required field '{req}'")


def _update_manifest(manifest_path: Path, provider: str, version: int) -> None:
    manifest = {"providers": {}}
    if manifest_path.exists():
        try:
            manifest = _load_json(manifest_path)
        except Exception:
            pass
    providers = manifest.setdefault("providers", {})
    entry = providers.setdefault(provider, {})
    entry["version"] = version
    entry["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    manifest.setdefault("schema_version", "3.0")
    manifest.setdefault("updated_at", datetime.now().isoformat() + "Z")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)


def _archive_sources(provider: str, version: int, sources_dir: Path, archive_dir: Path) -> None:
    """Archive source documents for this provider and version."""
    # Look in sources/[provider] for documents
    provider_source_dir = sources_dir / provider
    if not provider_source_dir.exists():
        return

    # Find all document types
    doc_files = list(provider_source_dir.glob("*.png"))
    doc_files.extend(provider_source_dir.glob("*.pdf"))
    doc_files.extend(provider_source_dir.glob("*.md"))

    if not doc_files:
        return

    # Create archive sources directory
    archive_sources = archive_dir / "sources"
    archive_sources.mkdir(parents=True, exist_ok=True)

    # Archive all document files
    for doc_file in doc_files:
        shutil.copy2(doc_file, archive_sources / doc_file.name)


@click.command(name="promote")
@click.option("--provider", default="all", help="Provider to promote (default: all)")
@click.option("--drafts-dir", default="drafts", type=click.Path())
@click.option("--models-dir", default="models", type=click.Path())
@click.option("--pages-dir", default="pages", type=click.Path())
@click.option("--manifest", default="manifest.json", type=click.Path())
@click.option("--sources-dir", default="sources", type=click.Path(), help="Directory containing source documents")
def promote(provider: str, drafts_dir: str, models_dir: str, pages_dir: str, manifest: str, sources_dir: str):
    """Promote draft models to production.

    Promotes the latest draft files to production. If --provider is 'all' (default),
    promotes all available drafts. Otherwise promotes only the specified provider.
    """
    drafts_path = Path(drafts_dir)

    # Determine which providers to promote
    if provider == "all":
        # Find all draft files
        draft_files = list(drafts_path.glob("*.draft.json"))
        providers_to_promote = list(set(f.name.split('.')[0] for f in draft_files))
        if not providers_to_promote:
            click.echo("No draft files found to promote")
            return
        click.echo(f"Found drafts for: {', '.join(sorted(providers_to_promote))}")
    else:
        providers_to_promote = [provider]

    # Promote each provider
    successful = []
    failed = []

    for prov in sorted(providers_to_promote):
        # Find the latest draft for this provider
        draft_files = sorted(drafts_path.glob(f"{prov}.*.draft.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not draft_files:
            click.echo(f"\n⚠️  No draft found for {prov}")
            failed.append(prov)
            continue

        draft_path = draft_files[0]
        click.echo(f"\n📦 Promoting {prov} from {draft_path.name}...")

        try:
            draft_data = _load_json(draft_path)

            # Validate
            _validate_for_production(draft_data)

            # Load current registry for merging
            pages_path = Path(pages_dir)
            pages_provider_dir = pages_path / prov
            published_file = pages_provider_dir / "models.json"

            if published_file.exists():
                current_data = _load_json(published_file)
                click.echo(f"  📋 Merging with existing registry ({len(current_data.get('models', {}))} models)")

                # Merge draft into current
                merged_data = _merge_registry(current_data, draft_data)

                # Check if anything actually changed (simple: compare hash of models)
                current_hash = _calculate_hash(current_data.get("models", {}))
                merged_hash = _calculate_hash(merged_data.get("models", {}))

                if current_hash == merged_hash:
                    click.echo(f"  ⏭️  No changes detected - skipping promotion")
                    successful.append(prov)
                    continue

                click.echo(f"  ✨ Changes detected - promoting")
                data_to_promote = merged_data
            else:
                click.echo(f"  🆕 No existing registry - creating new")
                data_to_promote = draft_data

            # Version management
            models_path = Path(models_dir)
            models_path.mkdir(exist_ok=True)
            current_version = _get_current_version(models_path, prov)
            new_version = current_version + 1

            # Update production
            data_to_promote["version"] = new_version
            data_to_promote["updated_at"] = datetime.now().isoformat()
            data_to_promote["content_sha256_jcs"] = _calculate_hash(data_to_promote)

            # Write production to models/ (for local consumers)
            out_models_file = models_path / f"{prov}.json"
            out_models_file.write_text(json.dumps(data_to_promote, indent=2))

            # Publish to pages/<provider>/models.json
            pages_provider_dir.mkdir(parents=True, exist_ok=True)
            published_file.write_text(json.dumps(data_to_promote, indent=2))

            # Archive snapshot under pages/<provider>/v/<new_version>/models.json
            archive_dir = pages_provider_dir / "v" / str(new_version)
            archive_dir.mkdir(parents=True, exist_ok=True)
            archive_file = archive_dir / "models.json"
            archive_file.write_text(json.dumps(data_to_promote, indent=2))

            # Archive source documents for this version
            _archive_sources(prov, new_version, Path(sources_dir), archive_dir)

            # Update manifest
            manifest_path = Path(manifest)
            _update_manifest(manifest_path, prov, new_version)

            click.echo(f"  ✅ Promoted to version {new_version}")

            # Delete the draft file after successful promotion
            try:
                draft_path.unlink()
                click.echo(f"  🗑️  Deleted draft: {draft_path.name}")
            except Exception as e:
                click.echo(f"  ⚠️  Could not delete draft: {e}")

            successful.append(prov)

        except Exception as e:
            click.echo(f"  ❌ Failed: {e}")
            failed.append(prov)

    # Summary
    if successful and not failed:
        click.echo(f"\n✨ Successfully promoted: {', '.join(successful)}")
    elif failed and not successful:
        click.echo(f"\n❌ All promotions failed: {', '.join(failed)}")
    else:
        click.echo(f"\n⚠️  Mixed results:")
        if successful:
            click.echo(f"   ✅ Successful: {', '.join(successful)}")
        if failed:
            click.echo(f"   ❌ Failed: {', '.join(failed)}")


if __name__ == "__main__":
    promote()