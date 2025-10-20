#!/usr/bin/env python3
"""Display provider documentation URLs for manual capture."""

import click
from datetime import datetime

PROVIDER_URLS = {
    "anthropic": {
        "url": "https://docs.anthropic.com/en/docs/about-claude/models/overview",
        "pricing_url": "https://www.anthropic.com/pricing",
        "description": "Claude models overview page (has pricing table)",
    },
    "openai": {
        "url": "https://platform.openai.com/docs/models",
        "pricing_url": "https://openai.com/api/pricing/",
        "description": "OpenAI models documentation (pricing separate)",
    },
    "google": {
        "url": "https://ai.google.dev/gemini-api/docs/models",
        "pricing_url": "https://ai.google.dev/pricing",
        "description": "Google Gemini models (pricing separate)",
    },
}


@click.command(name="sources")
@click.option("--provider", type=click.Choice(["openai", "anthropic", "google", "all"]), default="all")
def sources_info(provider: str):
    """Show provider documentation URLs for manual capture.

    Displays the URLs where you should go to get the latest model documentation,
    and the filename pattern to use when saving.
    """
    providers = [provider] if provider != "all" else ["anthropic", "openai", "google"]
    date_str = datetime.now().strftime("%Y-%m-%d")

    click.echo("\n📚 Provider Documentation Sources\n")

    for prov in providers:
        info = PROVIDER_URLS.get(prov)
        if not info:
            continue

        click.echo(f"🔹 {prov.upper()}")
        click.echo(f"   Models: {info['url']}")
        if "pricing_url" in info:
            click.echo(f"   Pricing: {info['pricing_url']}")
        click.echo(f"   Note: {info['description']}")
        click.echo(f"   Save to: sources/{prov}/{date_str}-models.md")
        click.echo()

    click.echo("💡 Quick Start:")
    click.echo("   1. Visit the model documentation URL")
    click.echo("   2. Save page as markdown to the path shown above")
    click.echo("   3. In Claude Code, run: update-registry skill")
    click.echo()
    click.echo("   Or manually: Claude reads source file → extracts → review → promote")
    click.echo()


if __name__ == "__main__":
    sources_info()
