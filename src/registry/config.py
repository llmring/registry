"""Configuration and default paths for the registry."""

from pathlib import Path

# Cache directories for fetched content
CACHE_DIR = Path("cache")
HTML_CACHE_DIR = CACHE_DIR / "html"
PDF_CACHE_DIR = CACHE_DIR / "pdfs"
SCREENSHOT_CACHE_DIR = CACHE_DIR / "screenshots"

# Working directories
DRAFTS_DIR = Path("drafts")

# Production data directories
MODELS_DIR = Path("models")
PAGES_DIR = Path("pages")

# Legacy paths (for backward compatibility during migration)
LEGACY_HTML_CACHE_DIR = Path("html_cache")
LEGACY_PDF_DIR = Path("pdfs")