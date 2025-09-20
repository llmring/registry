#!/usr/bin/env python3
"""Promotion utility to publish reviewed draft to production with archiving."""

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
        raise click.ClickException("Reviewed data missing 'models' dict")
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


def _find_latest_reviewed(drafts_dir: Path, provider: str) -> Path | None:
    candidates = list(drafts_dir.glob(f"{provider}.reviewed.json"))
    if not candidates:
        # Fallback: any reviewed for provider
        candidates = list(drafts_dir.glob(f"{provider}*.reviewed.json"))
        if not candidates:
            return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def _archive_sources(provider: str, version: int, sources_dir: Path, archive_dir: Path) -> None:
    """Archive source documents (HTML/PDF) for this provider and version."""
    html_dir = sources_dir / "html"
    pdf_dir = sources_dir / "pdfs"

    # Find relevant source files for this provider
    html_files = list(html_dir.glob(f"*{provider}*.html")) if html_dir.exists() else []
    pdf_files = list(pdf_dir.glob(f"*{provider}*.pdf")) if pdf_dir.exists() else []

    if not html_files and not pdf_files:
        return

    # Create archive sources directory
    archive_sources = archive_dir / "sources"
    archive_sources.mkdir(parents=True, exist_ok=True)

    # Archive HTML files
    if html_files:
        html_archive = archive_sources / "html"
        html_archive.mkdir(exist_ok=True)
        for html_file in html_files:
            shutil.copy2(html_file, html_archive / html_file.name)

    # Archive PDF files
    if pdf_files:
        pdf_archive = archive_sources / "pdfs"
        pdf_archive.mkdir(exist_ok=True)
        for pdf_file in pdf_files:
            shutil.copy2(pdf_file, pdf_archive / pdf_file.name)


@click.command(name="promote")
@click.option("--provider", required=True)
@click.option("--reviewed", required=False, type=click.Path(exists=True))
@click.option("--drafts-dir", default="drafts", type=click.Path())
@click.option("--models-dir", default="models", type=click.Path())
@click.option("--pages-dir", default="pages", type=click.Path())
@click.option("--manifest", default="manifest.json", type=click.Path())
@click.option("--sources-dir", default="sources", type=click.Path(), help="Directory containing source documents")
def promote(provider: str, reviewed: str | None, drafts_dir: str, models_dir: str, pages_dir: str, manifest: str, sources_dir: str):
    """Promote reviewed models to production and archive previous version.

    If --reviewed is not provided, the latest reviewed file in --drafts-dir is used.
    Source documents (HTML/PDF) are archived alongside the models for audit trail.
    """
    reviewed_path = Path(reviewed) if reviewed else _find_latest_reviewed(Path(drafts_dir), provider)
    if not reviewed_path or not reviewed_path.exists():
        raise click.ClickException(
            f"No reviewed file provided and none found in {drafts_dir} for provider '{provider}'"
        )
    models_path = Path(models_dir)
    pages_path = Path(pages_dir) / provider / "v"
    manifest_path = Path(manifest)

    models_path.mkdir(exist_ok=True)
    pages_path.mkdir(parents=True, exist_ok=True)

    reviewed_data = _load_json(reviewed_path)

    # Validate
    _validate_for_production(reviewed_data)

    # Version management: prefer version from reviewed, else bump
    current_version = _get_current_version(models_path, provider)
    reviewed_version = reviewed_data.get("version")
    try:
        reviewed_version_int = int(reviewed_version) if reviewed_version is not None else None
    except Exception:
        reviewed_version_int = None
    new_version = reviewed_version_int or (current_version + 1)

    # Update production
    reviewed_data["version"] = new_version
    reviewed_data["updated_at"] = datetime.now().isoformat()
    reviewed_data["content_sha256_jcs"] = _calculate_hash(reviewed_data)

    # Write production to models/ (for local consumers)
    out_models_file = models_path / f"{provider}.json"
    out_models_file.write_text(json.dumps(reviewed_data, indent=2))

    # Publish to pages/<provider>/models.json
    pages_provider_dir = pages_path.parent  # pages/<provider>/
    pages_provider_dir.mkdir(parents=True, exist_ok=True)
    published_file = pages_provider_dir / "models.json"
    published_file.write_text(json.dumps(reviewed_data, indent=2))

    # Archive snapshot under pages/<provider>/v/<new_version>/models.json
    archive_dir = pages_path / str(new_version)
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_file = archive_dir / "models.json"
    archive_file.write_text(json.dumps(reviewed_data, indent=2))

    # Archive source documents for this version
    _archive_sources(provider, new_version, Path(sources_dir), archive_dir)

    # Update manifest
    _update_manifest(manifest_path, provider, new_version)

    click.echo(
        f"✅ Promoted {provider} to version {new_version}. Snapshot archived under v/{new_version}."
    )

    # Delete the reviewed file after successful promotion
    try:
        reviewed_path.unlink()
        click.echo(f"🗑️  Deleted reviewed file: {reviewed_path}")
    except Exception:
        pass


if __name__ == "__main__":
    promote()


