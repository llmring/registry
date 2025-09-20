"""Configuration and default paths for the registry."""

from pathlib import Path

# Source document directories (audit trail - keep for reference)
SOURCES_DIR = Path("sources")
HTML_SOURCES_DIR = SOURCES_DIR / "html"
PDF_SOURCES_DIR = SOURCES_DIR / "pdfs"
SCREENSHOT_SOURCES_DIR = SOURCES_DIR / "screenshots"

# Working directories
DRAFTS_DIR = Path("drafts")

# Production data directories
MODELS_DIR = Path("models")
PAGES_DIR = Path("pages")

# Legacy paths (for backward compatibility during migration)
LEGACY_HTML_CACHE_DIR = Path("html_cache")
LEGACY_PDF_DIR = Path("pdfs")
LEGACY_CACHE_DIR = Path("cache")