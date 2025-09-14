"""Registry configuration and global constants."""

import os


# Single source of truth for the extraction model used across the pipeline.
# Override via env var to experiment without code changes.
# Example: export LLMRING_EXTRACTION_MODEL="anthropic:claude-sonnet-4-20250514"
DEFAULT_EXTRACTION_MODEL: str = os.getenv(
    "LLMRING_EXTRACTION_MODEL", "anthropic:claude-opus-4-1-20250805"
)


