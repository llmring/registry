#!/usr/bin/env python3
"""Display information about provider documentation sources.

This command helps contributors find where to download provider documentation
for extraction into the registry.
"""

import click

# Provider documentation URLs
PROVIDER_SOURCES = {
    "openai": {
        "name": "OpenAI",
        "docs_url": "https://platform.openai.com/docs/models",
        "pricing_url": "https://openai.com/api/pricing/",
        "notes": [
            "Key pages to capture:",
            "  - Models overview page",
            "  - Each individual model page (GPT-4, GPT-5, etc.)",
            "  - Pricing page",
            "Screenshot each page as PNG and save to sources/openai/",
        ]
    },
    "anthropic": {
        "name": "Anthropic",
        "docs_url": "https://docs.anthropic.com/en/docs/about-claude/models",
        "pricing_url": "https://www.anthropic.com/pricing",
        "notes": [
            "Key pages to capture:",
            "  - Models overview page",
            "  - Pricing page",
            "Can also save as Markdown from docs site",
            "Save to sources/anthropic/",
        ]
    },
    "google": {
        "name": "Google (Gemini)",
        "docs_url": "https://ai.google.dev/gemini-api/docs/models/gemini",
        "pricing_url": "https://ai.google.dev/pricing",
        "notes": [
            "Key pages to capture:",
            "  - Gemini models page",
            "  - Each model variant (Flash, Pro, etc.)",
            "  - Pricing page",
            "Screenshot each page as PNG and save to sources/google/",
        ]
    },
}


@click.command(name="sources")
@click.option(
    "--provider",
    type=click.Choice(["openai", "anthropic", "google", "all"]),
    default="all",
    help="Provider to show sources for"
)
def sources_command(provider: str):
    """Show where to find provider documentation for extraction.

    This command displays URLs and instructions for downloading provider
    documentation (screenshots, PDFs, markdown files) that will be used
    for model extraction.

    Examples:
        # Show all provider sources
        uv run llmring-registry sources

        # Show sources for specific provider
        uv run llmring-registry sources --provider openai
    """
    providers_to_show = (
        [provider] if provider != "all"
        else ["openai", "anthropic", "google"]
    )

    click.echo("\n📚 Provider Documentation Sources")
    click.echo("=" * 60)

    for prov in providers_to_show:
        if prov not in PROVIDER_SOURCES:
            continue

        info = PROVIDER_SOURCES[prov]
        click.echo(f"\n{info['name']}")
        click.echo("-" * 60)
        click.echo(f"  📄 Models:  {info['docs_url']}")
        click.echo(f"  💰 Pricing: {info['pricing_url']}")

        if info.get("notes"):
            click.echo("")
            for note in info["notes"]:
                click.echo(f"  {note}")

    click.echo("\n" + "=" * 60)
    click.echo("\n💡 Workflow:")
    click.echo("  1. Visit the URLs above")
    click.echo("  2. Take screenshots of each page (or save as PDF/MD)")
    click.echo("  3. Save to sources/<provider>/ directory")
    click.echo("     - Use descriptive names: YYYY-MM-DD-provider-topic.png")
    click.echo("     - Example: 2025-09-30-openai-pricing.png")
    click.echo("  4. Run extraction:")
    click.echo("     uv run llmring-registry extract --provider <provider>")
    click.echo("  5. Validate extracted data:")
    click.echo("     uv run llmring-registry validate --provider <provider>")
    click.echo("")


if __name__ == "__main__":
    sources_command()