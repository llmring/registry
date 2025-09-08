#!/usr/bin/env python3
"""Registry CLI - Main command-line interface for model registry management."""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path

import click

from .extract_with_llm import extract_with_llm

# Configure logging
logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx, verbose):
    """
    Registry CLI for managing LLM model data.

    Extract and version model information from provider documentation.
    """
    if verbose:
        logging.getLogger().setLevel(logging.INFO)
    ctx.ensure_object(dict)


@cli.command()
@click.option(
    "--provider",
    type=click.Choice(["openai", "anthropic", "google", "all"]),
    default="all",
    help="Provider to fetch",
)
@click.option("--output-dir", default="pdfs", help="Directory to save PDFs")
def fetch(provider, output_dir):
    """
    Fetch pricing and model pages as PDFs (requires Playwright).

    Install browsers for Playwright first:
      uv run playwright install chromium
    """
    try:
        import asyncio

        from .fetch_pdfs import fetch_all_pdfs

        providers = (
            [provider] if provider != "all" else ["openai", "anthropic", "google"]
        )
        output_path = Path(output_dir)

        click.echo(f"🌐 Fetching PDFs for: {', '.join(providers)}")
        click.echo(f"📁 Output directory: {output_path}")

        # Run async function
        asyncio.run(fetch_all_pdfs(providers, output_path))

    except ImportError:
        click.echo("❌ Playwright not installed!")
        click.echo("\nTo install:")
        click.echo("  uv add playwright")
        click.echo("  uv run playwright install chromium")
        click.echo("\nAlternatively, use 'registry sources' to see manual instructions")


@cli.command(name="fetch-html")
@click.option(
    "--provider",
    type=click.Choice(["openai", "anthropic", "google", "all"]),
    default="all",
    help="Provider to fetch",
)
@click.option("--output-dir", default="html_cache", help="Directory to save HTML")
def fetch_html(provider, output_dir):
    """
    Fetch pricing pages as HTML (lightweight, no browser needed).

    This doesn't require Playwright but won't capture JavaScript-rendered content.
    """
    try:
        from .fetch_html import fetch_html_pages
        # Lazy import inside the function; availability verified in try/except
    except ImportError as e:
        click.echo(f"❌ Missing dependencies: {e}")
        click.echo("\nTo install:")
        click.echo("  uv add requests beautifulsoup4")
        return

    # Call the fetch function with defaults
    ctx = click.get_current_context()
    ctx.invoke(
        fetch_html_pages, provider=provider, output_dir=output_dir, format="both"
    )


@cli.command()
def sources():
    """Show where to get pricing documentation for each provider."""

    sources_info = {
        "OpenAI": {
            "url": "https://openai.com/api/pricing/",
            "docs": "https://platform.openai.com/docs/models",
            "instructions": [
                "1. Visit the pricing page",
                "2. Press Cmd+P (Mac) or Ctrl+P (Windows/Linux)",
                "3. Save as PDF to registry/pdfs/YYYY-MM-DD-openai-pricing.pdf",
                "4. Also save the models documentation page",
            ],
        },
        "Anthropic": {
            "url": "https://www.anthropic.com/pricing",
            "docs": "https://docs.anthropic.com/en/docs/models-overview",
            "instructions": [
                "1. Visit the pricing page",
                "2. Press Cmd+P (Mac) or Ctrl+P (Windows/Linux)",
                "3. Save as PDF to registry/pdfs/YYYY-MM-DD-anthropic-pricing.pdf",
                "4. Also save the models overview documentation",
            ],
        },
        "Google": {
            "url": "https://ai.google.dev/pricing",
            "docs": "https://ai.google.dev/gemini-api/docs/models/gemini",
            "instructions": [
                "1. Visit the Gemini API pricing page",
                "2. Press Cmd+P (Mac) or Ctrl+P (Windows/Linux)",
                "3. Save as PDF to registry/pdfs/YYYY-MM-DD-google-pricing.pdf",
                "4. Also save the models documentation",
            ],
        },
    }

    click.echo("📚 Model Documentation Sources\n")
    click.echo("Save PDFs to: registry/pdfs/\n")

    for provider, info in sources_info.items():
        click.echo(f"🏢 {provider}")
        click.echo(f"   💰 Pricing: {info['url']}")
        click.echo(f"   📖 Docs:    {info['docs']}")
        click.echo("\n   Instructions:")
        for instruction in info["instructions"]:
            click.echo(f"      {instruction}")
        click.echo()


@cli.command(name="extract-comprehensive")
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
def extract_comprehensive(provider, html_dir, pdf_dir, models_dir, interactive):
    """
    Extract models using BOTH HTML regex and PDF LLM extraction.

    Compares both sources and marks uncertain fields.
    """
    from .extract_comprehensive import extract_comprehensive as extract_func

    ctx = click.get_current_context()
    ctx.invoke(
        extract_func,
        provider=provider,
        html_dir=html_dir,
        pdf_dir=pdf_dir,
        models_dir=models_dir,
        interactive=interactive,
        llm_model="best",
    )


@cli.command(name="extract-html")
@click.option(
    "--provider",
    type=click.Choice(["openai", "anthropic", "google", "all"]),
    default="all",
    help="Provider to extract",
)
@click.option(
    "--html-dir", default="html_cache", help="Directory containing HTML files"
)
@click.option("--models-dir", default="models", help="Directory to save model JSONs")
@click.option("--merge", is_flag=True, help="Merge with existing model files")
def extract_html(provider, html_dir, models_dir, merge):
    """
    Extract model details from cached HTML files.

    Extracts model names, pricing, token limits, and capabilities.
    """
    from .extract_from_html import extract_from_html as extract_func

    ctx = click.get_current_context()
    ctx.invoke(
        extract_func,
        provider=provider,
        html_dir=html_dir,
        models_dir=models_dir,
        merge=merge,
    )


@cli.command()
@click.option(
    "--provider",
    type=click.Choice(["openai", "anthropic", "google", "all"]),
    default="all",
    help="Provider to extract",
)
@click.option("--pdfs-dir", default="pdfs", help="Directory containing PDFs")
@click.option("--models-dir", default="models", help="Directory for model JSONs")
@click.option(
    "--versions-dir", default="versions", help="Directory for versioned JSONs"
)
@click.option("--force", is_flag=True, help="Force update even if no changes")
def extract(provider, pdfs_dir, models_dir, versions_dir, force):
    """Generate draft models from PDFs into the drafts/ directory (does not publish)."""
    from .extract_with_versioning import (
        archive_old_version,
        compare_json_models,
        extract_models_from_pdfs,
    )

    pdfs_path = Path(pdfs_dir)
    models_path = Path(models_dir)
    versions_path = Path(versions_dir)
    drafts_path = Path("drafts")

    # Ensure directories exist
    models_path.mkdir(exist_ok=True)

    providers_to_process = (
        [provider] if provider != "all" else ["openai", "anthropic", "google"]
    )

    updated_providers = []

    for prov in providers_to_process:
        click.echo(f"\n📄 Processing {prov}...")

        # Check for PDFs
        pdf_files = list(pdfs_path.glob(f"*{prov}*.pdf"))
        if not pdf_files:
            click.echo(f"  ⚠️  No PDFs found for {prov}")
            click.echo("      Run 'registry sources' to see where to get them")
            continue

        click.echo(f"  Found {len(pdf_files)} PDF(s)")

        # Extract from PDFs
        new_data = extract_models_from_pdfs(prov, pdfs_path)
        if not new_data:
            click.echo(f"  ⚠️  No data extracted for {prov}")
            continue

        # Always write to drafts directory (manual review required)
        drafts_path.mkdir(exist_ok=True)
        draft_file = drafts_path / f"{prov}.{datetime.now().strftime('%Y-%m-%d')}.json"
        with open(draft_file, "w") as f:
            json.dump(new_data, f, indent=2)
        click.echo(f"  ✍️  Wrote draft: {draft_file}")
        click.echo(
            f"  Next: uv run llmring-registry review-draft --provider {prov} --draft {draft_file}"
        )

        # Also maintain previous behavior for models_dir if explicitly requested via --force
        existing_file = models_path / f"{prov}.json"

        if existing_file.exists():
            # Load existing data
            with open(existing_file) as f:
                old_data = json.load(f)

            # Compare
            if compare_json_models(old_data, new_data) or force:
                click.echo(f"  🔄 Changes detected in {prov} models")

                # Archive old version
                archive_old_version(existing_file, versions_path)

                # Write new version
                with open(existing_file, "w") as f:
                    json.dump(new_data, f, indent=2)
                click.echo(f"  ✅ Updated {existing_file}")
                updated_providers.append(prov)
            else:
                click.echo(f"  ✓ No changes in {prov} models")
        else:
            # New file, just write it
            with open(existing_file, "w") as f:
                json.dump(new_data, f, indent=2)
            click.echo(f"  ✅ Created {existing_file}")
            updated_providers.append(prov)

    # Update summary
    if updated_providers:
        summary_file = models_path / "summary.json"
        summary = {
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "providers": providers_to_process,
            "updated_providers": updated_providers,
            "total_models": sum(
                len(json.load(open(models_path / f"{p}.json"))["models"])
                for p in providers_to_process
                if (models_path / f"{p}.json").exists()
            ),
        }

        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)

        click.echo(f"\n📊 Summary: Updated {len(updated_providers)} providers")
        click.echo(f"   Total models: {summary['total_models']}")
    else:
        click.echo("\n✓ No updates needed")


@cli.command(name="list")
@click.option("--models-dir", default="models", help="Directory containing model JSONs")
def list_models(models_dir):
    """List all models in the registry."""
    models_path = Path(models_dir)
    if not models_path.exists():
        click.echo("❌ Models directory not found")
        click.echo(
            "   Place curated files under provider directories (e.g., openai/models.json)"
        )
        return

    total_count = 0

    for provider in ["openai", "anthropic", "google"]:
        json_file = models_path / f"{provider}.json"
        if json_file.exists():
            with open(json_file) as f:
                data = json.load(f)

            models = data.get("models", {})
            if models:
                # Handle both dict (v3.5) and list (legacy) formats
                if isinstance(models, dict):
                    model_list = list(models.values())
                else:
                    model_list = models
                
                click.echo(f"\n📦 {provider.upper()} ({len(model_list)} models)")
                click.echo(f"   Last updated: {data.get('last_updated', 'Unknown')}")

                for model in model_list:
                    mid = model.get("model_id") or model.get("model_name", "unknown")
                    inp = model.get("dollars_per_million_tokens_input")
                    outp = model.get("dollars_per_million_tokens_output")
                    
                    if inp is not None and outp is not None:
                        click.echo(
                            f"   • {mid}: ${inp:.2f}/$M input, ${outp:.2f}/$M output"
                        )
                    else:
                        click.echo(f"   • {mid}: pricing not available")

                total_count += len(model_list)

    if total_count > 0:
        click.echo(f"\n📊 Total: {total_count} models")
    else:
        click.echo("No models found. Run 'registry extract' to create model files.")


@cli.command()
@click.option("--models-dir", default="models", help="Directory containing model JSONs")
@click.option(
    "--output",
    type=click.Choice(["json", "markdown"]),
    default="markdown",
    help="Output format",
)
def export(models_dir, output):
    """Export registry data for documentation or API use."""
    models_path = Path(models_dir)

    all_models = []
    for provider in ["openai", "anthropic", "google"]:
        json_file = models_path / f"{provider}.json"
        if json_file.exists():
            with open(json_file) as f:
                data = json.load(f)
                for model in data.get("models", []):
                    model["provider"] = provider
                    all_models.append(model)

    if output == "json":
        result = {
            "export_date": datetime.now().isoformat(),
            "total_models": len(all_models),
            "models": all_models,
        }
        click.echo(json.dumps(result, indent=2))

    elif output == "markdown":
        click.echo("# LLM Model Registry")
        click.echo(f"\n*Updated: {datetime.now().strftime('%Y-%m-%d')}*")
        click.echo(f"\n**Total Models:** {len(all_models)}")

        for provider in ["openai", "anthropic", "google"]:
            provider_models = [m for m in all_models if m["provider"] == provider]
            if provider_models:
                click.echo(f"\n## {provider.title()}")
                click.echo(
                    "\n| Model | Input $/M | Output $/M | Context | Vision | Functions |"
                )
                click.echo(
                    "|-------|-----------|------------|---------|--------|-----------|"
                )

                for model in provider_models:
                    vision = "✓" if model.get("supports_vision") else ""
                    functions = "✓" if model.get("supports_function_calling") else ""
                    mid = model.get("model_id") or model.get("model_name", "unknown")
                    ctx = model.get("max_context") or model.get("max_input_tokens", 0)
                    click.echo(
                        f"| {mid} | "
                        f"${model.get('dollars_per_million_tokens_input', 0):.2f} | "
                        f"${model.get('dollars_per_million_tokens_output', 0):.2f} | "
                        f"{ctx:,} | "
                        f"{vision} | {functions} |"
                    )


@cli.command()
@click.option("--models-dir", default="models", help="Directory containing model JSONs")
def validate(models_dir):
    """Validate model JSON files."""
    models_path = Path(models_dir)

    if not models_path.exists():
        click.echo("❌ Models directory not found")
        return 1

    required_fields = [
        # v3.5 schema
        "model_name",
        "display_name",
        "dollars_per_million_tokens_input",
        "dollars_per_million_tokens_output",
    ]

    errors = []
    warnings = []

    for provider in ["openai", "anthropic", "google"]:
        json_file = models_path / f"{provider}.json"

        if not json_file.exists():
            warnings.append(f"Missing {provider}.json")
            continue

        try:
            with open(json_file) as f:
                data = json.load(f)

            # Check structure
            if "models" not in data:
                errors.append(f"{provider}.json: Missing 'models' field")
                continue

            # Support both list and dict formats
            models_section = data.get("models")
            if isinstance(models_section, dict):
                iterator = models_section.items()
                for model_key, model in iterator:
                    for field in required_fields:
                        if field not in model:
                            label = model.get("model_name", model_key)
                            errors.append(
                                f"{provider}.json: Model {label} missing '{field}'"
                            )
            else:
                for i, model in enumerate(models_section or []):
                    for field in required_fields:
                        if field not in model:
                            label = model.get("model_name", i)
                            errors.append(
                                f"{provider}.json: Model {label} missing '{field}'"
                            )

        except json.JSONDecodeError as e:
            errors.append(f"{provider}.json: Invalid JSON - {e}")

    # Report results
    if errors:
        click.echo("❌ Validation failed:")
        for error in errors:
            click.echo(f"   • {error}")
    else:
        click.echo("✅ All model files are valid")

    if warnings:
        click.echo("\n⚠️  Warnings:")
        for warning in warnings:
            click.echo(f"   • {warning}")

    return 0 if len(errors) == 0 else 1


def main():
    """Main entry point."""
    cli()


# -------- Manual Curation Workflow Commands & helpers (appended) --------


def _load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


from typing import Any, Dict, List, Tuple


def _diff_models_dict(old: dict, new: dict) -> dict:
    """Compute a field-by-field diff between two models dicts (prefers v3.5 dict schema)."""

    def to_dict(data: dict) -> dict:
        models = data.get("models", {})
        if isinstance(models, dict):
            return models
        # convert list -> dict if needed using provider+model_name/id
        result = {}
        provider = data.get("provider")
        for m in models or []:
            name = m.get("model_name") or m.get("model_id")
            key = f"{provider}:{name}" if provider and name else name
            if key:
                result[key] = m
        return result

    old_models = to_dict(old)
    new_models = to_dict(new)

    diff: Dict[str, Any] = {"added_models": {}, "removed_models": [], "changed_models": {}}

    for key in new_models.keys() - old_models.keys():
        diff["added_models"][key] = new_models[key]
    for key in old_models.keys() - new_models.keys():
        diff["removed_models"].append(key)
    for key in new_models.keys() & old_models.keys():
        changes: Dict[str, Dict[str, Any]] = {}
        old_m = old_models[key]
        new_m = new_models[key]
        all_fields = set(old_m.keys()) | set(new_m.keys())
        for field in sorted(all_fields):
            if old_m.get(field) != new_m.get(field):
                changes[field] = {"old": old_m.get(field), "new": new_m.get(field)}
        if changes:
            diff["changed_models"][key] = changes
    return diff


def _strip_digest_fields(obj: object) -> object:
    if isinstance(obj, dict):
        return {
            k: _strip_digest_fields(v)
            for k, v in obj.items()
            if k not in {"content_sha256_jcs"}
        }
    if isinstance(obj, list):
        return [_strip_digest_fields(v) for v in obj]
    return obj


def _compute_content_sha256_jcs(data: dict) -> str:
    # Compute a stable SHA-256 over a JCS-like canonical JSON (sorted keys, no extra whitespace),
    # excluding the digest field itself.
    stripped = _strip_digest_fields(data)
    canonical = json.dumps(
        stripped, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@cli.command(name="review-draft")
@click.option(
    "--provider", required=True, type=click.Choice(["openai", "anthropic", "google"])
)
@click.option("--draft", "draft_path", required=True, type=click.Path(path_type=Path))
@click.option("--current", "current_path", type=click.Path(path_type=Path))
@click.option("--output", "output_path", type=click.Path(path_type=Path))
@click.option("--accept-all", is_flag=True, help="Accept all changes without prompting")
def review_draft(provider, draft_path, current_path, output_path, accept_all):
    """Review a draft models.json against the current curated file.

    Produces a diff summary and an optionally merged reviewed file.
    """
    # Default to the published site structure under pages/<provider>/models.json
    default_current = Path("pages") / provider / "models.json"
    current_file = Path(current_path) if current_path else default_current
    if not current_file.exists():
        click.echo(
            f"⚠️  No current file found at {current_file}. Starting review against empty set."
        )
        current_data = {
            "provider": provider,
            "version": 0,
            "updated_at": None,
            "models": {},
        }
    else:
        current_data = _load_json(current_file)

    draft_data = _load_json(draft_path)
    draft_data["provider"] = provider

    diff = _diff_models_dict(current_data, draft_data)

    click.echo(f"\n📋 Review Summary for {provider}")
    click.echo(f"  Added models: {len(diff['added_models'])}")
    click.echo(f"  Removed models: {len(diff['removed_models'])}")
    click.echo(f"  Changed models: {len(diff['changed_models'])}")

    if not accept_all:
        report_path = draft_path.with_suffix(".diff.json")
        _write_json(report_path, diff)
        click.echo(f"\n📝 Wrote diff report: {report_path}")
        click.echo(
            "Run again with --accept-all to generate a reviewed merged file, or edit the draft and rerun."
        )
        return

    reviewed = dict(draft_data)
    reviewed["version"] = (current_data.get("version") or 0) + 1
    from datetime import UTC
    reviewed["updated_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    if output_path is None:
        output_path = draft_path.with_name(f"{provider}.reviewed.json")
    _write_json(Path(output_path), reviewed)
    click.echo(f"\n✅ Wrote reviewed file: {output_path}")
    click.echo("Next: run 'registry promote' to archive and publish.")


@cli.command(name="promote")
@click.option(
    "--provider", required=True, type=click.Choice(["openai", "anthropic", "google"])
)
@click.option(
    "--reviewed", "reviewed_path", required=True, type=click.Path(path_type=Path)
)
def promote_reviewed(provider, reviewed_path):
    """Promote a reviewed file: bump version, archive to v/<n>/models.json, and update current models.json."""
    reviewed = _load_json(reviewed_path)

    # Publish under the site structure pages/<provider>
    provider_dir = Path("pages") / provider
    current_file = provider_dir / "models.json"

    current_version = 0
    if current_file.exists():
        current_data = _load_json(current_file)
        current_version = int(current_data.get("version") or 0)

    new_version = int(reviewed.get("version") or (current_version + 1))
    reviewed["version"] = new_version
    reviewed["provider"] = provider
    from datetime import UTC
    reviewed["updated_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    reviewed["content_sha256_jcs"] = _compute_content_sha256_jcs(reviewed)

    archive_path = provider_dir / "v" / str(new_version) / "models.json"
    _write_json(archive_path, reviewed)
    _write_json(current_file, reviewed)

    click.echo(f"📦 Archived: {archive_path}")
    click.echo(f"📤 Published: {current_file}")


# Add the LLM extraction command
cli.add_command(extract_with_llm, name="extract-llm")


if __name__ == "__main__":
    main()
