#!/usr/bin/env python3
"""Fetch pricing pages and save as PDFs using Playwright."""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import List

import click

logger = logging.getLogger(__name__)


PROVIDER_URLS = {
    "openai": {
        "pricing": "https://platform.openai.com/docs/pricing",
        "models": "https://platform.openai.com/docs/models",
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


async def fetch_and_save_pdf(page, url: str, output_path: Path, timeout_ms: int = 60000, screenshot_dir: Path | None = None) -> bool:
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

        # Navigate with a resilient strategy (dynamic docs often never reach networkidle)
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        except Exception:
            try:
                await page.goto(url, wait_until="load", timeout=timeout_ms)
            except Exception:
                # As a last resort, try minimal wait
                await page.goto(url, timeout=timeout_ms)

        # Try to wait for meaningful content
        try:
            await page.wait_for_selector("main, article, #__next, body", timeout=min(30000, timeout_ms // 2))
        except Exception:
            pass

        # Attempt incremental scroll to trigger lazy loading
        try:
            for _ in range(5):
                await page.evaluate("window.scrollBy(0, document.body.scrollHeight/4)")
                await page.wait_for_timeout(500)
        except Exception:
            pass

        # Check content length; if too small, wait a bit more
        try:
            body_len = await page.evaluate("(document.body && document.body.innerText || '').length")
            if body_len < 500:
                await page.wait_for_timeout(3000)
        except Exception:
            pass

        # Ensure screen media for better PDF output
        try:
            await page.emulate_media(media="screen")
        except Exception:
            pass

        # Optional: save a diagnostic screenshot
        try:
            if screenshot_dir is not None:
                screenshot_dir.mkdir(parents=True, exist_ok=True)
                shot_path = screenshot_dir / (output_path.stem + ".png")
                await page.screenshot(path=str(shot_path), full_page=True)
        except Exception:
            pass

        # Save as PDF
        await page.pdf(
            path=str(output_path),
            format="A4",
            print_background=True,
            margin={"top": "20px", "bottom": "20px", "left": "20px", "right": "20px"},
            prefer_css_page_size=True,
        )

        logger.info(f"✓ Saved to {output_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return False


async def fetch_all_pdfs(
    providers: List[str], output_dir: Path, browser_type: str = "chromium", timeout_seconds: int = 60
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

        # Create context with desktop viewport and sane defaults for SPAs
        context = await browser.new_context(
            viewport={"width": 1366, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            java_script_enabled=True,
            bypass_csp=True,
            locale="en-US",
            timezone_id="UTC",
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
                "Upgrade-Insecure-Requests": "1",
                "DNT": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                # A generic referer to look more like a human session
                "Referer": "https://www.google.com/",
            },
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

                screenshots_dir = output_dir / "_screenshots"

                if await fetch_and_save_pdf(page, url, output_path, timeout_ms=timeout_seconds * 1000, screenshot_dir=screenshots_dir):
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
