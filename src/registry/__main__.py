#!/usr/bin/env python3
"""Registry CLI - Main command-line interface for model registry management."""

import json
import logging
from datetime import datetime
from pathlib import Path

import click

from .review import review_draft
from .promote import promote
from .export_cmd import export_cmd
from .extract import extract_from_documents
from .validate import validate_command
from .normalize import normalize_command
from .sources_cmd import sources_command

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


# Add commands
cli.add_command(sources_command, name="sources")
cli.add_command(extract_from_documents, name="extract-from-documents")
cli.add_command(extract_from_documents, name="extract-from-screenshot")  # Backward compatibility
cli.add_command(extract_from_documents, name="extract")  # Simplified alias
cli.add_command(validate_command, name="validate")
cli.add_command(normalize_command, name="normalize")
cli.add_command(review_draft, name="review-draft")
cli.add_command(promote, name="promote")
cli.add_command(export_cmd, name="export")


@cli.command()
@click.option(
    "--provider",
    type=click.Choice(["openai", "anthropic", "google", "all"]),
    default="all",
    help="Provider to show stats for",
)
def stats(provider):
    """Show model statistics from registry."""
    models_dir = Path("models")

    providers = [provider] if provider != "all" else ["openai", "anthropic", "google"]

    for prov in providers:
        model_file = models_dir / f"{prov}.json"
        if not model_file.exists():
            click.echo(f"\n{prov}: No models found")
            continue

        with open(model_file) as f:
            data = json.load(f)

        models = data.get("models", {})
        click.echo(f"\n{prov}: {len(models)} models")

        # Count by capabilities
        vision_count = sum(1 for m in models.values() if m.get("supports_vision"))
        function_count = sum(1 for m in models.values() if m.get("supports_function_calling"))
        json_count = sum(1 for m in models.values() if m.get("supports_json_mode"))

        click.echo(f"  - Vision support: {vision_count}")
        click.echo(f"  - Function calling: {function_count}")
        click.echo(f"  - JSON mode: {json_count}")


@cli.command()
def list_drafts():
    """List available draft files."""
    drafts_dir = Path("drafts")
    if not drafts_dir.exists():
        click.echo("No drafts directory found")
        return

    draft_files = sorted(drafts_dir.glob("*.draft.json"))
    if not draft_files:
        click.echo("No draft files found")
        return

    click.echo("Available drafts:")
    for f in draft_files:
        # Get file stats
        stat = f.stat()
        size_kb = stat.st_size / 1024
        modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")

        # Try to read model count
        try:
            with open(f) as file:
                data = json.load(file)
                model_count = len(data.get("models", {}))
                click.echo(f"  - {f.name}: {model_count} models, {size_kb:.1f}KB, modified {modified}")
        except Exception:
            click.echo(f"  - {f.name}: {size_kb:.1f}KB, modified {modified}")


def main():
    """Main entry point."""
    try:
        cli(standalone_mode=False)
    except click.exceptions.NoArgsIsHelpError:
        # Show help when no arguments provided
        cli(["--help"])
    except Exception:
        # Allow other exceptions to propagate for debugging
        raise


if __name__ == "__main__":
    main()