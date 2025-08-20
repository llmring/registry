#!/usr/bin/env python3
"""Extract models from provider PDFs with versioning support."""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import click

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_models_from_pdfs(provider: str, pdf_dir: Path) -> Dict[str, Any]:
    """
    Extract models from provider PDFs.

    For now, this returns hardcoded data, but it should use the actual
    PDF extraction code in extraction/ and pricing/ directories.
    """
    # TODO: Use actual PDF extraction from pricing modules
    # For now, using hardcoded data as placeholder

    if provider == "openai":
        # Find OpenAI PDFs
        pdf_files = list(pdf_dir.glob("*openai*.pdf"))
        logger.info(f"Found OpenAI PDFs: {pdf_files}")

        models = [
            {
                "model_id": "gpt-4o",
                "display_name": "GPT-4o",
                "description": "Most capable model, multimodal",
                "max_context": 128000,
                "max_output_tokens": 16384,
                "supports_vision": True,
                "supports_function_calling": True,
                "supports_json_mode": True,
                "supports_parallel_tool_calls": True,
                "dollars_per_million_tokens_input": 2.50,
                "dollars_per_million_tokens_output": 10.00,
            },
            {
                "model_id": "gpt-4o-mini",
                "display_name": "GPT-4o Mini",
                "description": "Affordable small model",
                "max_context": 128000,
                "max_output_tokens": 16384,
                "supports_vision": True,
                "supports_function_calling": True,
                "supports_json_mode": True,
                "supports_parallel_tool_calls": True,
                "dollars_per_million_tokens_input": 0.15,
                "dollars_per_million_tokens_output": 0.60,
            },
        ]

    elif provider == "anthropic":
        pdf_files = list(pdf_dir.glob("*anthropic*.pdf"))
        logger.info(f"Found Anthropic PDFs: {pdf_files}")

        models = [
            {
                "model_id": "claude-3-5-sonnet-20241022",
                "display_name": "Claude 3.5 Sonnet",
                "description": "Most intelligent model",
                "max_context": 200000,
                "max_output_tokens": 8192,
                "supports_vision": True,
                "supports_function_calling": True,
                "supports_json_mode": False,
                "supports_parallel_tool_calls": True,
                "dollars_per_million_tokens_input": 3.00,
                "dollars_per_million_tokens_output": 15.00,
            },
            {
                "model_id": "claude-3-5-haiku-20241022",
                "display_name": "Claude 3.5 Haiku",
                "description": "Fast and affordable",
                "max_context": 200000,
                "max_output_tokens": 8192,
                "supports_vision": True,
                "supports_function_calling": True,
                "supports_json_mode": False,
                "supports_parallel_tool_calls": True,
                "dollars_per_million_tokens_input": 1.00,
                "dollars_per_million_tokens_output": 5.00,
            },
        ]

    elif provider == "google":
        pdf_files = list(pdf_dir.glob("*google*.pdf"))
        logger.info(f"Found Google PDFs: {pdf_files}")

        models = [
            {
                "model_id": "gemini-1.5-pro",
                "display_name": "Gemini 1.5 Pro",
                "description": "Advanced reasoning across modalities",
                "max_context": 2097152,
                "max_output_tokens": 8192,
                "supports_vision": True,
                "supports_function_calling": True,
                "supports_json_mode": True,
                "supports_parallel_tool_calls": False,
                "dollars_per_million_tokens_input": 1.25,
                "dollars_per_million_tokens_output": 5.00,
            },
            {
                "model_id": "gemini-1.5-flash",
                "display_name": "Gemini 1.5 Flash",
                "description": "Fast and versatile",
                "max_context": 1048576,
                "max_output_tokens": 8192,
                "supports_vision": True,
                "supports_function_calling": True,
                "supports_json_mode": True,
                "supports_parallel_tool_calls": False,
                "dollars_per_million_tokens_input": 0.075,
                "dollars_per_million_tokens_output": 0.30,
            },
        ]
    else:
        return None

    # Format with metadata
    return {
        "provider": provider,
        "last_updated": datetime.now().strftime("%Y-%m-%d"),
        "source": "pdf",
        "extraction_date": datetime.now().isoformat(),
        "models": models,
    }


def compare_json_models(old_data: Dict, new_data: Dict) -> bool:
    """
    Compare two JSON model files to see if they're different.

    Returns True if they differ (ignoring metadata like extraction_date).
    """
    # Compare models list only, not metadata
    old_models = old_data.get("models", [])
    new_models = new_data.get("models", [])

    if len(old_models) != len(new_models):
        return True

    # Sort by model_id for comparison
    old_sorted = sorted(old_models, key=lambda x: x.get("model_id", ""))
    new_sorted = sorted(new_models, key=lambda x: x.get("model_id", ""))

    for old, new in zip(old_sorted, new_sorted):
        # Compare relevant fields
        for field in [
            "model_id",
            "max_context",
            "max_output_tokens",
            "dollars_per_million_tokens_input",
            "dollars_per_million_tokens_output",
            "supports_vision",
            "supports_function_calling",
        ]:
            if old.get(field) != new.get(field):
                logger.info(
                    f"Difference found in {field}: {old.get(field)} vs {new.get(field)}"
                )
                return True

    return False


def archive_old_version(model_file: Path, versions_dir: Path):
    """
    Archive the old version of a model file.
    """
    # Read the file to get its last_updated date
    with open(model_file) as f:
        data = json.load(f)

    # Use last_updated or file modification time
    date_str = data.get("last_updated")
    if not date_str:
        # Use file modification time
        mtime = model_file.stat().st_mtime
        date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")

    # Create version directory
    version_dir = versions_dir / date_str
    version_dir.mkdir(parents=True, exist_ok=True)

    # Copy file to version directory
    dest_file = version_dir / model_file.name
    shutil.copy2(model_file, dest_file)
    logger.info(f"Archived {model_file.name} to {dest_file}")


@click.command()
@click.option(
    "--provider",
    type=click.Choice(["openai", "anthropic", "google", "all"]),
    default="all",
    help="Provider to extract",
)
@click.option("--pdfs-dir", default="pdfs", help="Directory containing PDFs")
@click.option(
    "--models-dir", default="models", help="Directory for current model JSONs"
)
@click.option(
    "--versions-dir", default="versions", help="Directory for versioned JSONs"
)
@click.option("--force", is_flag=True, help="Force update even if no changes detected")
def extract_and_version(provider, pdfs_dir, models_dir, versions_dir, force):
    """
    Extract models from PDFs and version existing JSONs if changed.

    Process:
    1. Extract models from PDFs in pdfs_dir
    2. Compare with existing JSONs in models_dir
    3. If different, archive old JSONs to versions_dir with date
    4. Replace with new extracted JSONs
    """
    pdfs_path = Path(pdfs_dir)
    models_path = Path(models_dir)
    versions_path = Path(versions_dir)

    # Ensure directories exist
    models_path.mkdir(exist_ok=True)

    providers_to_process = (
        [provider] if provider != "all" else ["openai", "anthropic", "google"]
    )

    updated_providers = []

    for prov in providers_to_process:
        click.echo(f"\n📄 Processing {prov}...")

        # Extract from PDFs
        new_data = extract_models_from_pdfs(prov, pdfs_path)
        if not new_data:
            click.echo(f"  ⚠️  No data extracted for {prov}")
            continue

        # Check if existing JSON exists
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

    # Update summary file if any providers were updated
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


if __name__ == "__main__":
    extract_and_version()
