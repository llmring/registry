#!/usr/bin/env python3
"""Review draft diffs against current provider models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import click


def _load_json(path: Path) -> Dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def _load_current_models(models_dir: Path, provider: str) -> Dict[str, Any]:
    """Load current models from models/<provider>.json, falling back to pages/<provider>/models.json."""
    file = models_dir / f"{provider}.json"
    if file.exists():
        return _load_json(file)
    # Fallback to pages structure
    pages_file = Path("pages") / provider / "models.json"
    if pages_file.exists():
        return _load_json(pages_file)
    return {"provider": provider, "models": {}}


def _generate_diff(current: Dict[str, Any], draft: Dict[str, Any]) -> Dict[str, Any]:
    current_models = current.get("models", {})
    draft_models = draft.get("models", {})

    added = {k: v for k, v in draft_models.items() if k not in current_models}
    removed = {k: v for k, v in current_models.items() if k not in draft_models}

    changed = {}
    for key in current_models.keys() & draft_models.keys():
        cur = current_models[key]
        new = draft_models[key]
        field_changes = {}
        for fk in set(cur.keys()) | set(new.keys()):
            if fk == "_confidence":
                continue
            if cur.get(fk) != new.get(fk):
                field_changes[fk] = {"old": cur.get(fk), "new": new.get(fk)}
        if field_changes:
            changed[key] = field_changes

    return {"added": added, "removed": removed, "changed": changed}


def _apply_diff(current: Dict[str, Any], diff: Dict[str, Any]) -> Dict[str, Any]:
    models = current.get("models", {}).copy()
    for k in diff.get("removed", {}).keys():
        models.pop(k, None)
    for k, v in diff.get("added", {}).items():
        models[k] = v
    for k, changes in diff.get("changed", {}).items():
        base = models.get(k, {}).copy()
        for fk, vals in changes.items():
            base[fk] = vals.get("new")
        models[k] = base
    result = current.copy()
    result["models"] = models
    return result


def _find_latest_draft(drafts_dir: Path, provider: str) -> Optional[Path]:
    candidates = list(drafts_dir.glob(f"{provider}*.draft.json"))
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


@click.command(name="review-draft")
@click.option("--provider", required=True)
@click.option("--draft", required=False, type=click.Path(exists=True))
@click.option("--drafts-dir", default="drafts", type=click.Path())
@click.option("--models-dir", default="models", type=click.Path())
@click.option("--accept-all", is_flag=True)
def review_draft(provider: str, draft: Optional[str], drafts_dir: str, models_dir: str, accept_all: bool):
    """Review draft changes against current registry and optionally accept all.

    If --draft is not provided, the most recent draft in --drafts-dir is used.
    """
    models_path = Path(models_dir)
    drafts_path = Path(drafts_dir)
    drafts_path.mkdir(exist_ok=True)

    draft_path = Path(draft) if draft else _find_latest_draft(drafts_path, provider)
    if not draft_path or not draft_path.exists():
        raise click.ClickException(
            f"No draft provided and none found in {drafts_path} for provider '{provider}'"
        )

    current = _load_current_models(models_path, provider)
    draft_data = _load_json(draft_path)
    # Basic validation for draft structure
    if not isinstance(draft_data, dict) or "models" not in draft_data or not isinstance(draft_data["models"], dict):
        raise click.ClickException("Draft file is invalid: missing 'models' dict")

    diff = _generate_diff(current, draft_data)

    if not accept_all:
        # Write alongside the draft as <name>.diff.json
        diff_path = draft_path.with_suffix('.diff.json')
        diff_path.write_text(json.dumps(diff, indent=2))
        click.echo(f"📝 Diff written: {diff_path}")
        click.echo(
            f"Added: {len(diff['added'])}, Removed: {len(diff['removed'])}, Changed: {len(diff['changed'])}"
        )
        return

    reviewed = _apply_diff(current, diff)
    # Preserve top-level metadata from draft when available
    reviewed["provider"] = provider
    if "version" in draft_data:
        reviewed["version"] = draft_data["version"]
    reviewed_path = draft_path.with_name(f"{provider}.reviewed.json")
    reviewed_path.write_text(json.dumps(reviewed, indent=2))
    click.echo(f"✅ Reviewed file written: {reviewed_path}")

    # Delete the original draft after successful review
    try:
        draft_path.unlink()
        click.echo(f"🗑️  Deleted draft: {draft_path}")
    except Exception:
        pass


if __name__ == "__main__":
    review_draft()


