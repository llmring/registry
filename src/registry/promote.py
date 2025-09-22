#!/usr/bin/env python3
"""Promotion utility to publish draft models to production with archiving."""

from __future__ import annotations

import json
import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import click


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

            # Version management
            models_path = Path(models_dir)
            models_path.mkdir(exist_ok=True)
            current_version = _get_current_version(models_path, prov)
            new_version = current_version + 1

            # Update production
            draft_data["version"] = new_version
            draft_data["updated_at"] = datetime.now().isoformat()
            draft_data["content_sha256_jcs"] = _calculate_hash(draft_data)

            # Write production to models/ (for local consumers)
            out_models_file = models_path / f"{prov}.json"
            out_models_file.write_text(json.dumps(draft_data, indent=2))

            # Publish to pages/<provider>/models.json
            pages_path = Path(pages_dir)
            pages_provider_dir = pages_path / prov
            pages_provider_dir.mkdir(parents=True, exist_ok=True)
            published_file = pages_provider_dir / "models.json"
            published_file.write_text(json.dumps(draft_data, indent=2))

            # Archive snapshot under pages/<provider>/v/<new_version>/models.json
            archive_dir = pages_provider_dir / "v" / str(new_version)
            archive_dir.mkdir(parents=True, exist_ok=True)
            archive_file = archive_dir / "models.json"
            archive_file.write_text(json.dumps(draft_data, indent=2))

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