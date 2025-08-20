#!/usr/bin/env python3
"""Fetch pricing pages and save as PDFs using Playwright."""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import click

logger = logging.getLogger(__name__)


PROVIDER_URLS = {
    "openai": {
        "pricing": "https://openai.com/api/pricing/",
        "models": "https://platform.openai.com/docs/models",
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


async def fetch_and_save_pdf(page, url: str, output_path: Path) -> bool:
    """
    Fetch a URL and save it as PDF.

    Args:
        page: Playwright page object
        url: URL to fetch
        output_path: Path to save PDF

    Returns:
        True if successful
    """
    try:
        logger.info(f"Fetching {url}")

        # Navigate to page
        await page.goto(url, wait_until="networkidle")

        # Wait a bit for any dynamic content
        await page.wait_for_timeout(2000)

        # Save as PDF
        await page.pdf(
            path=str(output_path),
            format="A4",
            print_background=True,
            margin={"top": "20px", "bottom": "20px", "left": "20px", "right": "20px"},
        )

        logger.info(f"✓ Saved to {output_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return False


async def fetch_all_pdfs(
    providers: List[str], output_dir: Path, browser_type: str = "chromium"
):
    """
    Fetch all PDFs for specified providers.

    Args:
        providers: List of provider names
        output_dir: Directory to save PDFs
        browser_type: Browser to use (chromium, firefox, webkit)
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        click.echo("❌ Playwright not installed. Run: uv add playwright")
        click.echo("   Then run: uv run playwright install chromium")
        return

    output_dir.mkdir(exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")

    async with async_playwright() as p:
        # Launch browser
        if browser_type == "chromium":
            browser = await p.chromium.launch(headless=True)
        elif browser_type == "firefox":
            browser = await p.firefox.launch(headless=True)
        else:
            browser = await p.webkit.launch(headless=True)

        # Create context with desktop viewport
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        )

        page = await context.new_page()

        success_count = 0
        total_count = 0

        for provider in providers:
            if provider not in PROVIDER_URLS:
                click.echo(f"⚠️  Unknown provider: {provider}")
                continue

            urls = PROVIDER_URLS[provider]

            for doc_type, url in urls.items():
                total_count += 1
                filename = f"{date_str}-{provider}-{doc_type}.pdf"
                output_path = output_dir / filename

                if await fetch_and_save_pdf(page, url, output_path):
                    success_count += 1

                # Small delay between requests
                await asyncio.sleep(1)

        await browser.close()

        click.echo(f"\n📊 Fetched {success_count}/{total_count} PDFs successfully")


@click.command()
@click.option(
    "--provider",
    type=click.Choice(["openai", "anthropic", "google", "all"]),
    default="all",
    help="Provider to fetch",
)
@click.option("--output-dir", default="pdfs", help="Directory to save PDFs")
@click.option(
    "--browser",
    type=click.Choice(["chromium", "firefox", "webkit"]),
    default="chromium",
    help="Browser to use",
)
def fetch_pdfs(provider, output_dir, browser):
    """
    Fetch pricing and model documentation pages as PDFs.

    This command uses Playwright to render web pages and save them as PDFs.
    Install Playwright first: uv add playwright && uv run playwright install chromium
    """
    providers = [provider] if provider != "all" else ["openai", "anthropic", "google"]
    output_path = Path(output_dir)

    click.echo(f"🌐 Fetching PDFs for: {', '.join(providers)}")
    click.echo(f"📁 Output directory: {output_path}")

    # Run async function
    asyncio.run(fetch_all_pdfs(providers, output_path, browser))


if __name__ == "__main__":
    fetch_pdfs()
