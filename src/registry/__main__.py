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

        from .fetch_pdfs import fetch_pdfs

        asyncio.run(fetch_pdfs(provider, output_dir))
    except ImportError:
        click.echo(
            "❌ Playwright not installed. Install with: uv add playwright",
            err=True,
        )
        raise click.Abort()
    except Exception as e:
        click.echo(f"❌ Failed to fetch PDFs: {e}", err=True)
        raise click.Abort()


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
    Fetch pricing and model pages as HTML.

    Saves raw HTML for extraction.
    """
    from .fetch_html import fetch_html as fetch_func

    ctx = click.get_current_context()
    ctx.invoke(fetch_func, provider=provider, output_dir=output_dir)


@cli.command()
@click.option(
    "--provider",
    type=click.Choice(["openai", "anthropic", "google", "all"]),
    default="all",
    help="Provider to show",
)
def sources(provider):
    """Show where to find pricing info for each provider."""
    urls = {
        "openai": [
            "https://openai.com/api/pricing/",
            "https://platform.openai.com/docs/models",
        ],
        "anthropic": [
            "https://www.anthropic.com/pricing",
            "https://docs.anthropic.com/en/docs/about-claude/models",
        ],
        "google": [
            "https://ai.google.dev/pricing",
            "https://cloud.google.com/vertex-ai/generative-ai/pricing",
        ],
    }

    providers = [provider] if provider != "all" else list(urls.keys())

    for prov in providers:
        click.echo(f"\n📚 {prov.upper()} Sources:")
        for url in urls[prov]:
            click.echo(f"   • {url}")

    click.echo(
        "\n💡 Tip: Use 'llmring-registry fetch' to automatically download these as PDFs"
    )


@cli.command()
@click.option(
    "--provider",
    type=click.Choice(["openai", "anthropic", "google", "all"]),
    default="all",
    help="Provider to extract",
)
@click.option(
    "--html-dir",
    default="html_cache",
    type=click.Path(exists=True),
    help="Directory containing HTML files",
)
@click.option(
    "--models-dir",
    default="models",
    type=click.Path(),
    help="Directory to save extracted models",
)
@click.option(
    "--validate/--no-validate",
    default=True,
    help="Run validation pass on extracted models",
)
def extract(provider, html_dir, models_dir, validate):
    """Extract model information from HTML using LLM-based extraction.
    
    Uses adaptive LLM extraction that handles website structure changes.
    """
    ctx = click.get_current_context()
    ctx.invoke(
        extract_with_llm,
        provider=provider,
        html_dir=html_dir,
        models_dir=models_dir,
        validate=validate,
    )


# Add the extract-llm alias for backward compatibility
cli.add_command(extract, name="extract-llm")


@cli.command(name="list")
@click.option("--models-dir", default="models", help="Directory containing model JSONs")
@click.option(
    "--provider",
    type=click.Choice(["openai", "anthropic", "google", "all"]),
    default="all",
    help="Filter by provider",
)
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def list_models(models_dir, provider, output_json):
    """List all available models and their pricing."""
    models_path = Path(models_dir)

    if not models_path.exists():
        click.echo(
            "No models directory found. Run 'llmring-registry extract' to create model files.",
            err=True,
        )
        return

    providers = (
        [provider] if provider != "all" else ["openai", "anthropic", "google"]
    )

    all_models = {}
    total_count = 0

    for provider in providers:
        json_file = models_path / f"{provider}.json"
        if not json_file.exists():
            continue

        with open(json_file) as f:
            data = json.load(f)
            
            # Handle both dict format (new) and list format (old)
            models = data.get("models", {})
            if isinstance(models, dict):
                model_list = list(models.values())
            else:
                model_list = models
            
            if output_json:
                all_models[provider] = model_list
            else:
                if not model_list:
                    continue
                
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
    "--provider",
    type=click.Choice(["openai", "anthropic", "google", "all"]),
    default="all",
    help="Provider to validate",
)
@click.option("--verbose", "-v", is_flag=True, help="Show validation details")
def validate(models_dir, provider, verbose):
    """Validate model JSON files for consistency and completeness."""
    models_path = Path(models_dir)

    if not models_path.exists():
        click.echo("No models directory found.", err=True)
        return

    providers = (
        [provider] if provider != "all" else ["openai", "anthropic", "google"]
    )

    has_errors = False

    for prov in providers:
        json_file = models_path / f"{prov}.json"
        if not json_file.exists():
            if verbose:
                click.echo(f"⚠️  No file for {prov}")
            continue

        with open(json_file) as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                click.echo(f"❌ {prov}: Invalid JSON - {e}", err=True)
                has_errors = True
                continue

        # Check structure
        if "models" not in data:
            click.echo(f"❌ {prov}: Missing 'models' field", err=True)
            has_errors = True
            continue

        models = data["models"]
        
        # Handle both dict and list formats
        if isinstance(models, dict):
            model_list = list(models.values())
        else:
            model_list = models

        # Validate each model
        errors = []
        for i, model in enumerate(model_list):
            model_errors = []

            # Required fields
            required = ["model_name", "provider"]
            for field in required:
                if field not in model:
                    model_errors.append(f"Missing '{field}'")

            # Numeric fields
            numeric_fields = [
                "dollars_per_million_tokens_input",
                "dollars_per_million_tokens_output",
                "max_input_tokens",
                "max_output_tokens",
            ]
            for field in numeric_fields:
                if field in model:
                    val = model[field]
                    if val is not None and not isinstance(val, (int, float)):
                        model_errors.append(f"'{field}' must be numeric, got {type(val).__name__}")
                    elif val is not None and val < 0:
                        model_errors.append(f"'{field}' cannot be negative")

            # Boolean fields
            bool_fields = [
                "supports_vision",
                "supports_function_calling", 
                "supports_json_mode",
                "supports_parallel_tool_calls",
            ]
            for field in bool_fields:
                if field in model and not isinstance(model.get(field), bool):
                    model_errors.append(f"'{field}' must be boolean")

            if model_errors:
                model_name = model.get("model_name", f"index_{i}")
                errors.append(f"  Model '{model_name}': {', '.join(model_errors)}")

        if errors:
            click.echo(f"❌ {prov}: Validation errors", err=True)
            if verbose:
                for error in errors:
                    click.echo(error, err=True)
            has_errors = True
        elif verbose:
            click.echo(f"✅ {prov}: Valid ({len(model_list)} models)")

    if not has_errors:
        click.echo("✅ All model files are valid")
    else:
        raise click.Abort()


@cli.command()
@click.option("--models-dir", default="models", help="Directory containing model JSONs")
@click.option(
    "--output", default="manifest.json", help="Output manifest filename"
)
def manifest(models_dir, output):
    """Generate a manifest file listing all available models."""
    models_path = Path(models_dir)

    if not models_path.exists():
        click.echo("No models directory found.", err=True)
        return

    manifest_data = {
        "version": datetime.now().strftime("%Y-%m-%d"),
        "updated_at": datetime.now().isoformat() + "Z",
        "providers": {},
        "schema_version": "2.0",
        "registry_url": "https://llmring.github.io/registry/",
        "extraction_methods": {
            "llm": "LLM-based extraction via LLMRing unified interface"
        }
    }

    for provider in ["openai", "anthropic", "google"]:
        json_file = models_path / f"{provider}.json"
        if json_file.exists():
            with open(json_file) as f:
                data = json.load(f)
                models = data.get("models", {})
                model_count = len(models) if isinstance(models, dict) else len(models)
                manifest_data["providers"][provider] = {
                    "file": f"models/{provider}.json",
                    "model_count": model_count,
                    "last_updated": data.get("last_updated", datetime.now().strftime("%Y-%m-%d"))
                }

    with open(output, "w") as f:
        json.dump(manifest_data, f, indent=2)

    total_models = sum(p["model_count"] for p in manifest_data["providers"].values())
    click.echo(f"✅ Generated manifest with {total_models} models from {len(manifest_data['providers'])} providers")


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()