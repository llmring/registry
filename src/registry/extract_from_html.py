#!/usr/bin/env python3
"""Extract model information from fetched HTML pages."""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def extract_number(text: str) -> Optional[float]:
    """Extract a number from text like '$2.50' or '128,000'."""
    if not text:
        return None
    # Remove currency symbols and commas
    cleaned = re.sub(r"[$,]", "", text)
    # Find first number (including decimals)
    match = re.search(r"[\d.]+", cleaned)
    if match:
        try:
            return float(match.group())
        except ValueError:
            return None
    return None


def extract_openai_models(html: str) -> List[Dict[str, Any]]:
    """Extract OpenAI model information from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    models = []

    text = soup.get_text()

    # Extract GPT-5 models (from the pricing page)
    # Looking for patterns like "GPT-5" followed by pricing info
    gpt5_patterns = [
        # GPT-5 (base)
        (
            r"GPT-5(?![\s-](?:mini|nano)).*?(?:Input|input)[:\s]*\$?([\d.]+)\s*/\s*1M\s*tokens.*?(?:Output|output)[:\s]*\$?([\d.]+)\s*/\s*1M\s*tokens",
            "gpt-5",
            "GPT-5",
        ),
        # GPT-5 mini
        (
            r"GPT-5[\s-]mini.*?(?:Input|input)[:\s]*\$?([\d.]+)\s*/\s*1M\s*tokens.*?(?:Output|output)[:\s]*\$?([\d.]+)\s*/\s*1M\s*tokens",
            "gpt-5-mini",
            "GPT-5 Mini",
        ),
        # GPT-5 nano
        (
            r"GPT-5[\s-]nano.*?(?:Input|input)[:\s]*\$?([\d.]+)\s*/\s*1M\s*tokens.*?(?:Output|output)[:\s]*\$?([\d.]+)\s*/\s*1M\s*tokens",
            "gpt-5-nano",
            "GPT-5 Nano",
        ),
    ]

    for pattern, model_id, display_name in gpt5_patterns:
        match = re.search(pattern, text, re.I | re.S)
        if match:
            try:
                input_price = float(match.group(1))
                output_price = float(match.group(2))

                # Set context and capabilities based on model tier
                if model_id == "gpt-5":
                    context = 200000
                    description = "Most capable model for coding and agentic tasks"
                elif model_id == "gpt-5-mini":
                    context = 128000
                    description = "Faster, cheaper version for well-defined tasks"
                else:  # nano
                    context = 128000
                    description = (
                        "Fastest, cheapest for summarization and classification"
                    )

                models.append(
                    {
                        "model_id": model_id,
                        "display_name": display_name,
                        "description": description,
                        "dollars_per_million_tokens_input": input_price,
                        "dollars_per_million_tokens_output": output_price,
                        "max_context": context,
                        "max_output_tokens": 16384,
                        "supports_vision": True,
                        "supports_function_calling": True,
                        "supports_json_mode": True,
                        "supports_parallel_tool_calls": True,
                    }
                )
            except (ValueError, AttributeError):
                continue

    # Also look for GPT-4 models
    gpt4_patterns = [
        (
            r"gpt-4o-mini.*?(?:Input|input)[:\s]*\$?([\d.]+)\s*/\s*1M\s*tokens.*?(?:Output|output)[:\s]*\$?([\d.]+)\s*/\s*1M\s*tokens",
            "gpt-4o-mini",
            "GPT-4o Mini",
        ),
        (
            r"gpt-4o(?![\s-]mini).*?(?:Input|input)[:\s]*\$?([\d.]+)\s*/\s*1M\s*tokens.*?(?:Output|output)[:\s]*\$?([\d.]+)\s*/\s*1M\s*tokens",
            "gpt-4o",
            "GPT-4o",
        ),
        (
            r"gpt-4[\s-]turbo.*?(?:Input|input)[:\s]*\$?([\d.]+)\s*/\s*1M\s*tokens.*?(?:Output|output)[:\s]*\$?([\d.]+)\s*/\s*1M\s*tokens",
            "gpt-4-turbo",
            "GPT-4 Turbo",
        ),
        (
            r"gpt-3\.5[\s-]turbo.*?(?:Input|input)[:\s]*\$?([\d.]+)\s*/\s*1M\s*tokens.*?(?:Output|output)[:\s]*\$?([\d.]+)\s*/\s*1M\s*tokens",
            "gpt-3.5-turbo",
            "GPT-3.5 Turbo",
        ),
    ]

    for pattern, model_id, display_name in gpt4_patterns:
        match = re.search(pattern, text, re.I | re.S)
        if match:
            try:
                input_price = float(match.group(1))
                output_price = float(match.group(2))

                models.append(
                    {
                        "model_id": model_id,
                        "display_name": display_name,
                        "dollars_per_million_tokens_input": input_price,
                        "dollars_per_million_tokens_output": output_price,
                        "max_context": 128000 if "4" in model_id else 16385,
                        "max_output_tokens": 16384 if "4o" in model_id else 4096,
                        "supports_vision": "gpt-4o" in model_id
                        or "gpt-4-turbo" in model_id,
                        "supports_function_calling": True,
                        "supports_json_mode": True,
                        "supports_parallel_tool_calls": True,
                    }
                )
            except (ValueError, AttributeError):
                continue

    # Also check for o1 models
    o1_patterns = [
        (
            r"o1-preview.*?(?:Input|input)[:\s]*\$?([\d.]+)\s*/\s*1M\s*tokens.*?(?:Output|output)[:\s]*\$?([\d.]+)\s*/\s*1M\s*tokens",
            "o1-preview",
            "o1 Preview",
        ),
        (
            r"o1-mini.*?(?:Input|input)[:\s]*\$?([\d.]+)\s*/\s*1M\s*tokens.*?(?:Output|output)[:\s]*\$?([\d.]+)\s*/\s*1M\s*tokens",
            "o1-mini",
            "o1 Mini",
        ),
    ]

    for pattern, model_id, display_name in o1_patterns:
        match = re.search(pattern, text, re.I | re.S)
        if match:
            try:
                input_price = float(match.group(1))
                output_price = float(match.group(2))

                models.append(
                    {
                        "model_id": model_id,
                        "display_name": display_name,
                        "dollars_per_million_tokens_input": input_price,
                        "dollars_per_million_tokens_output": output_price,
                        "max_context": 128000,
                        "max_output_tokens": 32768,
                        "supports_vision": False,
                        "supports_function_calling": False,
                        "supports_json_mode": True,
                        "supports_parallel_tool_calls": False,
                    }
                )
            except (ValueError, AttributeError):
                continue

    return models


def extract_anthropic_models(html: str) -> List[Dict[str, Any]]:
    """Extract Anthropic model information from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    models = []

    text = soup.get_text()

    # Look for Claude models with more precise patterns
    # Using (?:Input|input) and looking for dollar signs or "per" to avoid matching model dates
    model_patterns = [
        (
            r"Claude[\s-]3[\s-]5[\s-]Sonnet.*?(?:Input|input)[:\s]*\$?([\d.]+)\s*(?:per|/)\s*(?:1M|million).*?(?:Output|output)[:\s]*\$?([\d.]+)",
            "claude-3-5-sonnet-20241022",
            "Claude 3.5 Sonnet",
        ),
        (
            r"Claude[\s-]3[\s-]5[\s-]Haiku.*?(?:Input|input)[:\s]*\$?([\d.]+)\s*(?:per|/)\s*(?:1M|million).*?(?:Output|output)[:\s]*\$?([\d.]+)",
            "claude-3-5-haiku-20241022",
            "Claude 3.5 Haiku",
        ),
        (
            r"Claude[\s-]3[\s-]Opus.*?(?:Input|input)[:\s]*\$?([\d.]+)\s*(?:per|/)\s*(?:1M|million).*?(?:Output|output)[:\s]*\$?([\d.]+)",
            "claude-3-opus-20240229",
            "Claude 3 Opus",
        ),
        (
            r"Claude[\s-]3[\s-]Sonnet(?!.*3[\s-]5).*?(?:Input|input)[:\s]*\$?([\d.]+)\s*(?:per|/)\s*(?:1M|million).*?(?:Output|output)[:\s]*\$?([\d.]+)",
            "claude-3-sonnet-20240229",
            "Claude 3 Sonnet",
        ),
        (
            r"Claude[\s-]3[\s-]Haiku(?!.*3[\s-]5).*?(?:Input|input)[:\s]*\$?([\d.]+)\s*(?:per|/)\s*(?:1M|million).*?(?:Output|output)[:\s]*\$?([\d.]+)",
            "claude-3-haiku-20240307",
            "Claude 3 Haiku",
        ),
    ]

    for pattern, model_id, display_name in model_patterns:
        match = re.search(pattern, text, re.I | re.S)
        if match:
            try:
                input_price = float(match.group(1))
                output_price = float(match.group(2))

                # Don't override extracted prices - if they look wrong, flag them
                if "opus" in model_id:
                    desc = "Most capable Claude model"
                elif "sonnet" in model_id:
                    desc = "Balanced performance and cost"
                else:  # haiku
                    desc = "Fast and affordable"

                # Flag suspicious prices
                if input_price > 1000 or output_price > 1000:
                    desc += " [WARNING: Extracted price may be incorrect]"
                    logger.warning(
                        f"Suspicious price for {model_id}: ${input_price}/$M input, ${output_price}/$M output"
                    )

                models.append(
                    {
                        "model_id": model_id,
                        "display_name": display_name,
                        "description": desc,
                        "dollars_per_million_tokens_input": input_price,
                        "dollars_per_million_tokens_output": output_price,
                        "max_context": 200000,
                        "max_output_tokens": 8192 if "3-5" in model_id else 4096,
                        "supports_vision": True,
                        "supports_function_calling": True,
                        "supports_json_mode": False,
                        "supports_parallel_tool_calls": True,
                    }
                )
            except (ValueError, AttributeError):
                continue

    # If no models found, log a warning - don't use defaults
    if not models:
        logger.warning(
            "No Anthropic models could be extracted from HTML - regex patterns may need updating"
        )

    return models


def extract_google_models(html: str) -> List[Dict[str, Any]]:
    """Extract Google/Gemini model information from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    models = []

    text = soup.get_text()

    # Look for Gemini models
    model_patterns = [
        (
            r"gemini-1\.5-pro.*?\$?([\d.]+).*?input.*?\$?([\d.]+).*?output",
            "gemini-1.5-pro",
        ),
        (
            r"gemini-1\.5-flash(?!-8b).*?\$?([\d.]+).*?input.*?\$?([\d.]+).*?output",
            "gemini-1.5-flash",
        ),
        (
            r"gemini-1\.5-flash-8b.*?\$?([\d.]+).*?input.*?\$?([\d.]+).*?output",
            "gemini-1.5-flash-8b",
        ),
        (r"gemini-pro.*?\$?([\d.]+).*?input.*?\$?([\d.]+).*?output", "gemini-pro"),
    ]

    for pattern, model_id in model_patterns:
        match = re.search(pattern, text, re.I | re.S)
        if match:
            try:
                input_price = float(match.group(1))
                output_price = float(match.group(2))

                model_name = model_id.replace("-", " ").title()

                # Determine context size based on model
                if "1.5-pro" in model_id:
                    context = 2097152  # 2M tokens
                elif "1.5-flash" in model_id:
                    context = 1048576  # 1M tokens
                else:
                    context = 32768

                models.append(
                    {
                        "model_id": model_id,
                        "display_name": model_name,
                        "dollars_per_million_tokens_input": input_price,
                        "dollars_per_million_tokens_output": output_price,
                        "max_context": context,
                        "max_output_tokens": 8192,
                        "supports_vision": "1.5" in model_id,
                        "supports_function_calling": True,
                        "supports_json_mode": True,
                        "supports_parallel_tool_calls": False,
                    }
                )
            except (ValueError, AttributeError):
                continue

    return models


def merge_with_existing(new_models: List[Dict], existing_file: Path) -> List[Dict]:
    """Merge newly extracted models with existing ones, updating prices."""
    if not existing_file.exists():
        return new_models

    with open(existing_file) as f:
        existing_data = json.load(f)

    existing_models = {m["model_id"]: m for m in existing_data.get("models", [])}

    # Update existing models with new data
    for new_model in new_models:
        model_id = new_model["model_id"]
        if model_id in existing_models:
            # Update pricing and keep other fields
            existing_models[model_id].update(
                {
                    "dollars_per_million_tokens_input": new_model.get(
                        "dollars_per_million_tokens_input"
                    ),
                    "dollars_per_million_tokens_output": new_model.get(
                        "dollars_per_million_tokens_output"
                    ),
                    "last_price_update": datetime.now().isoformat(),
                }
            )
        else:
            # Add new model
            existing_models[model_id] = new_model

    return list(existing_models.values())


@click.command()
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
def extract_from_html(provider, html_dir, models_dir, merge):
    """
    Extract model information from cached HTML files.

    This command processes HTML files saved by 'fetch-html' and extracts:
    - Model names and IDs
    - Pricing (input/output per million tokens)
    - Context windows and output limits
    - Capabilities (vision, functions, JSON mode)
    """
    providers = [provider] if provider != "all" else ["openai", "anthropic", "google"]
    html_path = Path(html_dir)
    models_path = Path(models_dir)
    models_path.mkdir(exist_ok=True)

    if not html_path.exists():
        click.echo(f"❌ HTML directory not found: {html_path}")
        click.echo("   Run 'registry fetch-html' first to download pricing pages")
        return

    extractors = {
        "openai": extract_openai_models,
        "anthropic": extract_anthropic_models,
        "google": extract_google_models,
    }

    for prov in providers:
        click.echo(f"\n📄 Extracting {prov} models from HTML...")

        # Find HTML files for this provider
        html_files = list(html_path.glob(f"*{prov}*.html"))
        if not html_files:
            click.echo(f"  ⚠️  No HTML files found for {prov}")
            continue

        all_models = []

        for html_file in html_files:
            click.echo(f"  Processing {html_file.name}")

            with open(html_file, "r", encoding="utf-8") as f:
                html_content = f.read()

            # Extract models
            extractor = extractors.get(prov)
            if extractor:
                models = extractor(html_content)
                all_models.extend(models)
                click.echo(f"    Found {len(models)} models")

        if all_models:
            # Remove duplicates and validate
            unique_models = {}
            for model in all_models:
                model_id = model.get("model_id")
                if model_id and model_id not in unique_models:
                    # Validate the extracted data
                    issues = []

                    # Check for missing required fields
                    if not model.get("dollars_per_million_tokens_input"):
                        issues.append("missing input price")
                    if not model.get("dollars_per_million_tokens_output"):
                        issues.append("missing output price")

                    # Check for suspicious values
                    input_price = model.get("dollars_per_million_tokens_input", 0)
                    output_price = model.get("dollars_per_million_tokens_output", 0)

                    if input_price > 100:
                        issues.append(f"suspiciously high input price: ${input_price}")
                    if output_price > 500:
                        issues.append(
                            f"suspiciously high output price: ${output_price}"
                        )
                    if input_price > output_price:
                        issues.append("input price higher than output price")

                    if issues:
                        model["extraction_warnings"] = issues
                        click.echo(f"    ⚠️  {model_id}: {', '.join(issues)}")

                    unique_models[model_id] = model

            final_models = list(unique_models.values())

            # Merge with existing if requested
            output_file = models_path / f"{prov}.json"
            if merge and output_file.exists():
                final_models = merge_with_existing(final_models, output_file)
                click.echo(f"  ✓ Merged with existing {output_file.name}")

            # Create output data
            output_data = {
                "provider": prov,
                "last_updated": datetime.now().strftime("%Y-%m-%d"),
                "source": "html_extraction",
                "extraction_date": datetime.now().isoformat(),
                "models": final_models,
            }

            # Save to JSON
            with open(output_file, "w") as f:
                json.dump(output_data, f, indent=2)

            click.echo(f"  ✅ Saved {len(final_models)} models to {output_file}")
        else:
            click.echo(f"  ⚠️  No models extracted for {prov}")

    click.echo("\n💡 Use 'registry validate' to check the extracted data")
    click.echo("   Use 'registry list' to view all models")


if __name__ == "__main__":
    extract_from_html()
