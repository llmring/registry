#!/usr/bin/env python3
"""Fetch pricing pages as HTML (lightweight alternative to PDF)."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import click

logger = logging.getLogger(__name__)


PROVIDER_URLS = {
    "openai": {
        "pricing": "https://platform.openai.com/docs/pricing",
        "models": "https://platform.openai.com/docs/models",
        "api_pricing": "https://api.openai.com/v1/models",  # API endpoint
    },
    "anthropic": {
        "pricing": "https://docs.anthropic.com/en/docs/about-claude/pricing",
        "models": "https://docs.anthropic.com/en/docs/about-claude/models/overview",
    },
    "google": {
        "pricing": "https://ai.google.dev/pricing",
        "models": "https://ai.google.dev/gemini-api/docs/models/gemini",
    },
}


def fetch_html(url: str) -> Optional[str]:
    """
    Fetch HTML content from a URL.

    Args:
        url: URL to fetch

    Returns:
        HTML content as string
    """
    import requests

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return None


def is_minimal_html(text: str) -> bool:
    """Heuristic to detect client-rendered shells with little usable content."""
    if not text:
        return True
    return len(text) < 2000 and "<script" in text and "<main" not in text and "data-rh" not in text


def fetch_rendered_html(url: str) -> Optional[str]:
    """Fetch server-rendered content via a reader proxy as a fallback for SPAs."""
    import requests

    try:
        # Use Jina Reader proxy to get rendered HTML
        # It expects an http URL appended; use the host+path from original URL
        from urllib.parse import urlparse

        parsed = urlparse(url)
        host_path = f"{parsed.netloc}{parsed.path or ''}"
        rendered_url = f"https://r.jina.ai/http://{host_path}"
        resp = requests.get(rendered_url, timeout=30)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        logger.error(f"Rendered HTML fallback failed for {url}: {e}")
        return None




@click.command()
@click.option(
    "--provider",
    type=click.Choice(["openai", "anthropic", "google", "all"]),
    default="all",
    help="Provider to fetch",
)
@click.option(
    "--output-dir",
    default="sources/html",
    help="Directory to save HTML and extracted data",
)
def fetch_html_pages(provider, output_dir):
    """
    Fetch pricing pages as HTML (lightweight, no browser needed).

    This is a simpler alternative to PDF fetching that doesn't require Playwright.
    The HTML may not include JavaScript-rendered content.
    """
    providers = [provider] if provider != "all" else ["openai", "anthropic", "google"]
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")

    click.echo(f"🌐 Fetching HTML for: {', '.join(providers)}")
    click.echo(f"📁 Output directory: {output_path}")

    success_count = 0
    total_count = 0

    for prov in providers:
        if prov not in PROVIDER_URLS:
            click.echo(f"⚠️  Unknown provider: {prov}")
            continue

        # Create provider-specific directory
        provider_dir = output_path / prov
        provider_dir.mkdir(parents=True, exist_ok=True)

        urls = PROVIDER_URLS[prov]

        for doc_type, url in urls.items():
            if doc_type == "api_pricing":
                continue  # Skip API endpoints for now

            total_count += 1
            click.echo(f"\nFetching {prov} {doc_type}: {url}")

            html = fetch_html(url)
            if html:
                success_count += 1

                # Save HTML in provider subdirectory
                html_file = provider_dir / f"{date_str}-{prov}-{doc_type}.html"
                with open(html_file, "w", encoding="utf-8") as f:
                    f.write(html)
                click.echo(f"  ✓ Saved HTML to {html_file}")

                # If the HTML looks minimal (SPA shell), try rendered fallback
                if is_minimal_html(html):
                    click.echo("  ⚠️  HTML looks client-rendered; trying rendered fallback…")
                    rendered = fetch_rendered_html(url)
                    if rendered:
                        rendered_file = provider_dir / f"{date_str}-{prov}-{doc_type}.rendered.html"
                        with open(rendered_file, "w", encoding="utf-8") as rf:
                            rf.write(rendered)
                        click.echo(f"     ✓ Saved rendered HTML to {rendered_file}")
                    else:
                        click.echo("     ✗ Rendered fallback failed")
            else:
                click.echo("  ✗ Failed to fetch")

    click.echo(f"\n📊 Fetched {success_count}/{total_count} pages successfully")
    click.echo("\n💡 Tip: Use 'llmring-registry extract' to properly extract model information from these files")


if __name__ == "__main__":
    fetch_html_pages()
