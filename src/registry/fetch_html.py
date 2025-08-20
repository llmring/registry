#!/usr/bin/env python3
"""Fetch pricing pages as HTML (lightweight alternative to PDF)."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict

import click

logger = logging.getLogger(__name__)


PROVIDER_URLS = {
    "openai": {
        "pricing": "https://openai.com/api/pricing/",
        "models": "https://platform.openai.com/docs/models",
        "api_pricing": "https://api.openai.com/v1/models",  # API endpoint
    },
    "anthropic": {
        "pricing": "https://www.anthropic.com/pricing",
        "models": "https://docs.anthropic.com/en/docs/models-overview",
    },
    "google": {
        "pricing": "https://ai.google.dev/pricing",
        "models": "https://ai.google.dev/gemini-api/docs/models/gemini",
    },
}


def fetch_html(url: str) -> str:
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
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return None


def extract_pricing_info(html: str, provider: str) -> Dict:
    """
    Extract basic pricing information from HTML.

    This is a simple extraction - for full extraction use the LLM-based extractors.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")

    # Extract title and basic text
    title = soup.title.string if soup.title else "Unknown"

    # Find pricing-related text (very basic)
    pricing_keywords = ["price", "pricing", "cost", "per", "token", "million", "$"]
    relevant_text = []

    for element in soup.find_all(["p", "li", "td", "div", "span"]):
        text = element.get_text(strip=True)
        if text and any(keyword in text.lower() for keyword in pricing_keywords):
            if len(text) < 500:  # Skip very long blocks
                relevant_text.append(text)

    return {
        "provider": provider,
        "title": title,
        "extracted_at": datetime.now().isoformat(),
        "pricing_mentions": relevant_text[:50],  # Limit to 50 items
        "note": "This is raw HTML extraction. Use 'registry extract' for proper model extraction.",
    }


@click.command()
@click.option(
    "--provider",
    type=click.Choice(["openai", "anthropic", "google", "all"]),
    default="all",
    help="Provider to fetch",
)
@click.option(
    "--output-dir",
    default="html_cache",
    help="Directory to save HTML and extracted data",
)
@click.option(
    "--format",
    type=click.Choice(["html", "json", "both"]),
    default="both",
    help="Output format",
)
def fetch_html_pages(provider, output_dir, format):
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

        urls = PROVIDER_URLS[prov]
        extracted_data = {}

        for doc_type, url in urls.items():
            if doc_type == "api_pricing":
                continue  # Skip API endpoints for now

            total_count += 1
            click.echo(f"\nFetching {prov} {doc_type}: {url}")

            html = fetch_html(url)
            if html:
                success_count += 1

                # Save HTML if requested
                if format in ["html", "both"]:
                    html_file = output_path / f"{date_str}-{prov}-{doc_type}.html"
                    with open(html_file, "w", encoding="utf-8") as f:
                        f.write(html)
                    click.echo(f"  ✓ Saved HTML to {html_file}")

                # Extract basic info
                if format in ["json", "both"]:
                    extracted_data[doc_type] = extract_pricing_info(html, prov)
            else:
                click.echo(f"  ✗ Failed to fetch")

        # Save extracted data as JSON
        if format in ["json", "both"] and extracted_data:
            json_file = output_path / f"{date_str}-{prov}-extracted.json"
            with open(json_file, "w") as f:
                json.dump(extracted_data, f, indent=2)
            click.echo(f"  ✓ Saved extracted data to {json_file}")

    click.echo(f"\n📊 Fetched {success_count}/{total_count} pages successfully")

    if format in ["json", "both"]:
        click.echo(
            "\n💡 Tip: Use 'registry extract' to properly extract model information from these files"
        )


if __name__ == "__main__":
    fetch_html_pages()
