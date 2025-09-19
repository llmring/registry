# LLMRing Registry

> ⚠️ Pre-release notice
>
> The pricing, token limits, and capabilities in this registry are under active validation and may be inaccurate. Do not rely on these numbers for production decisions. Always verify against the providers' official documentation.
>
> **Latest Update (2025-09-14):**
> - OpenAI: 13 models including GPT-4o, GPT-4o-mini, GPT-3.5-turbo
> - Anthropic: 14 models including Claude 3 Opus, Sonnet, Haiku, Claude 3.5 Sonnet
> - Google: 9 models including Gemini 1.5 Flash, Pro, and Ultra variants


The official model registry for LLMRing - providing up-to-date pricing, capabilities, and metadata for all major LLM providers.

## Overview

The LLMRing Registry is the source of truth for model information across the LLMRing ecosystem. It automatically extracts and maintains accurate model data from provider documentation, serving it through GitHub Pages for global, free access.

**Key Features:**
- 📅 Daily automated extraction from provider documentation
- 🔍 Dual extraction approach (HTML + PDF) for accuracy
- 📦 Versioned JSON files with historical snapshots
- 🌐 Served via GitHub Pages at `https://llmring.github.io/registry/`
- 🔓 No API keys required for access

## Architecture

```
Registry (This Repo)
├── Extraction Pipeline
│   ├── HTML Extraction (LLM-based adaptive extraction)
│   ├── PDF Analysis (via LLMRing's unified interface)
│   └── Confidence Scoring (dual-source consensus merging)
├── Review & Promotion
│   ├── Draft Generation with confidence metrics
│   ├── Diff-based review workflow
│   └── Version management and archiving
└── Output
    ├── models/         # Current production models
    ├── drafts/         # Pending changes for review
    ├── pages/          # Versioned archives
    └── manifest.json   # Registry metadata
```

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/llmring/registry.git
cd registry

# Install with uv (recommended)
uv sync
uv pip install -e .

# Or with pip
pip install -e .
```

### Default Workflow (Recommended)

```bash
# 1) Fetch both HTML and PDFs into the standard directories
uv run llmring-registry fetch --provider all

# 2) Extract comprehensively (auto-creates html_cache/, pdfs/, drafts/)
uv run llmring-registry extract --provider all --timeout 60

# 3) Review latest drafts and accept
uv run llmring-registry review-draft --provider openai --accept-all
uv run llmring-registry review-draft --provider anthropic --accept-all
uv run llmring-registry review-draft --provider google --accept-all

# 4) Promote reviewed files (auto-discovers them in drafts/)
uv run llmring-registry promote --provider openai
uv run llmring-registry promote --provider anthropic
uv run llmring-registry promote --provider google
```

### Manual Curation Workflow (Human-validated)

0. Gather source materials (optional but recommended):

```bash
# Show where to get docs and how to save PDFs
uv run llmring-registry sources

# Fetch both HTML and PDFs (recommended)
# (First time only: uv run playwright install chromium)
uv run llmring-registry fetch --provider openai
```

1. Generate a draft JSON using the extractor (best-effort), or by hand:

```bash
# Comprehensive draft generation from both HTML and PDFs
# Directories html_cache/, pdfs/, and drafts/ are auto-created if missing
# You can also set a per-PDF timeout in seconds (default 60)
uv run llmring-registry extract --provider openai --timeout 60
```
2. Review differences vs current curated file:

```bash
# Review latest draft for the provider (no path needed)
uv run llmring-registry review-draft --provider openai
# This writes a sibling diff file: drafts/<draft>.diff.json

# Accept all changes to produce a reviewed file (and delete the draft)
uv run llmring-registry review-draft --provider openai --accept-all
# This writes drafts/openai.reviewed.json and removes the original draft
```

3. Promote the reviewed file to publish and archive:

```bash
# Promote latest reviewed file for the provider (no path needed)
uv run llmring-registry promote --provider openai
# On success, the reviewed file is deleted
```

This will:
- Validate and publish to `pages/openai/models.json`
- Archive snapshot at `pages/openai/v/<version>/models.json`
- Write `models/openai.json` for local consumption
- Bump `version` and set `updated_at`
- Add `content_sha256_jcs` integrity hash

### Legacy Automation (deprecated)

Commands like `fetch`, `fetch-html`, and `extract*` remain for reference but are deprecated. The official process is manual, human-validated curation.

```bash
# View available commands
uv run llmring-registry --help

# Fetch latest documentation
uv run llmring-registry fetch-html --provider all

# Extract models from HTML
uv run llmring-registry extract-html --provider all

# Extract models with comprehensive dual-source validation
uv run llmring-registry extract --provider all --timeout 60

# List all extracted models
uv run llmring-registry list

# Export to markdown for documentation
uv run llmring-registry export --output markdown > models.md
```

## Extraction System

The registry uses a **dual extraction approach** for maximum accuracy:

### 1. HTML Extraction
- Fast regex-based extraction from provider websites
- Captures current pricing and basic model information
- No API keys required

### 2. PDF Extraction
- Uses LLMRing's unified interface (requires API keys)
- Extracts detailed capabilities and specifications
- Automatically uses optimal method per provider:
  - **OpenAI**: Assistants API for PDF processing
  - **Anthropic**: Native PDF support with Claude
  - **Google**: Direct PDF support with Gemini

### 3. Validation & Consensus
- Compares both sources for each field
- Marks confidence levels:
  - **Certain**: Both sources agree
  - **Probable**: Single source only
  - **Uncertain**: Sources conflict
- Interactive mode available for manual resolution

## Model Schema

Each provider's JSON file contains models in dictionary format with `provider:model` keys for O(1) lookup:

```json
{
  "provider": "openai",
  "version": 3,
  "updated_at": "2025-08-28T00:00:00Z",
  "models": {
    "openai:gpt-5": {
      "provider": "openai",
      "model_name": "gpt-5",
      "display_name": "GPT-5",
      "description": "Most capable model for coding and agentic tasks",
      "max_input_tokens": 200000,
      "max_output_tokens": 16384,
      "dollars_per_million_tokens_input": 1.25,
      "dollars_per_million_tokens_output": 10.0,
      "supports_vision": true,
      "supports_function_calling": true,
      "supports_json_mode": true,
      "supports_parallel_tool_calls": true,
      "is_active": true
    },
    "openai:gpt-5-mini": {
      "provider": "openai",
      "model_name": "gpt-5-mini",
      "display_name": "GPT-5 Mini",
      "description": "Faster, cheaper version for well-defined tasks",
      "max_input_tokens": 128000,
      "max_output_tokens": 16384,
      "dollars_per_million_tokens_input": 0.25,
      "dollars_per_million_tokens_output": 2.0,
      "supports_vision": true,
      "supports_function_calling": true,
      "supports_json_mode": true,
      "supports_parallel_tool_calls": true,
      "is_active": true
    }
  }
}
```

## Commands Reference

### Fetching Documentation

```bash
# Preferred: fetch everything in one step
uv run llmring-registry fetch --provider all

# Also available individually:
# - Fetch HTML pages (no browser required)
uv run llmring-registry fetch-html --provider openai
# - Fetch as PDFs (requires Playwright)
uv run llmring-registry fetch-pdf --provider all
```

### Extraction

```bash
# Comprehensive extraction from both HTML and PDFs (recommended)
uv run llmring-registry extract --provider all --timeout 60

# Extract from HTML only (uses LLM-based extraction)
uv run llmring-registry extract-html --provider all

# Extract from PDFs only (requires LLM API keys)
uv run llmring-registry extract-pdf --provider all
```

### Review & Promote

```bash
# Review the latest draft for a provider (auto-discovers drafts/)
uv run llmring-registry review-draft --provider openai

# Accept all changes to create a reviewed file (and delete the draft)
uv run llmring-registry review-draft --provider openai --accept-all

# Promote the latest reviewed file (auto-discovers drafts/)
uv run llmring-registry promote --provider openai
```

### Data Management

```bash
# List all models with pricing
uv run llmring-registry list

# Validate JSON structure
uv run llmring-registry validate

# Export for documentation
uv run llmring-registry export --output markdown
uv run llmring-registry export --output json
```

## Environment Variables

For PDF extraction (optional but recommended):

```bash
# Choose one or more providers
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="..."
```

The system will automatically use the best available model for extraction.

## Behavior Notes

- Directories `html_cache/`, `pdfs/`, and `drafts/` are auto-created if missing by `extract-comprehensive`.
- `review-draft` without `--draft` picks the most recent `drafts/<provider>*.draft.json`.
- `review-draft --accept-all` creates `drafts/<provider>.reviewed.json` and deletes the source draft.
- `promote` without `--reviewed` picks the latest `drafts/<provider>.reviewed.json` and deletes it after promotion.
- `extract-comprehensive` supports `--timeout` (seconds) per PDF; default is 60s. Timeouts are logged and skipped.

## Automation

### GitHub Actions Workflow

The registry updates automatically via GitHub Actions:

```yaml
# .github/workflows/update-registry.yml
name: Update Registry
on:
  schedule:
    - cron: '0 6 * * *'  # Daily at 6 AM UTC
  workflow_dispatch:

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - run: |
          # Install uv
          curl -LsSf https://astral.sh/uv/install.sh | sh
          echo "$HOME/.cargo/bin" >> $GITHUB_PATH
      - run: |
          # Install dependencies
          uv sync
          uv pip install -e .
      - run: uv run llmring-registry fetch-html --provider all
      - run: uv run llmring-registry extract-html --provider all
      - run: uv run llmring-registry validate
      - run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add models/
          git commit -m "Update model registry $(date +%Y-%m-%d)" || true
          git push
```

**Note:** The workflow uses `extract-html` for CI/CD since full `extract` requires LLM API keys for PDF extraction.

## Development

### Project Structure

```
registry/
├── src/registry/
│   ├── __main__.py           # CLI entry point
│   ├── extract_comprehensive.py  # Dual-source extraction
│   ├── extract_from_html.py  # HTML regex patterns
│   ├── extraction/
│   │   ├── pdf_parser.py     # LLMRing-based PDF extraction
│   │   └── model_curator.py  # Model selection logic
│   └── fetch_html.py         # Web scraping
├── models/                   # Output JSON files
├── pdfs/                     # Cached PDF documentation
└── html_cache/               # Cached HTML pages
```

### Adding a New Provider

1. Add URL mappings in `fetch_html.py`:
```python
PROVIDER_URLS = {
    "newprovider": {
        "pricing": "https://newprovider.com/pricing",
        "models": "https://newprovider.com/docs/models"
    }
}
```

2. Add extraction patterns in `extract_from_html.py`:
```python
def extract_newprovider_models(html: str) -> List[Dict[str, Any]]:
    # Add regex patterns for the provider's HTML structure
    pass
```

3. Test extraction:
```bash
uv run llmring-registry fetch-html --provider newprovider
uv run llmring-registry extract-comprehensive --provider newprovider
```

### Testing

```bash
# Run tests
uv run pytest

# Test extraction for a specific provider
uv run llmring-registry extract-comprehensive --provider openai --interactive

# Validate output
uv run llmring-registry validate --models-dir models
```

## Integration with LLMRing

The registry serves as the data source for the entire LLMRing ecosystem:

1. **Static Hosting**: JSON files are served via GitHub Pages
2. **Registry URL**: `https://llmring.github.io/registry/`
3. **Manifest**: Contains version info and provider index
4. **Updates**: Daily via GitHub Actions

Client usage:
```python
from llmring import LLMRing

# Automatically fetches latest registry
ring = LLMRing()

# Get available models
models = ring.get_available_models()
```

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Priority Areas

- [ ] Add more providers (Cohere, AI21, etc.)
- [ ] Improve extraction patterns for better accuracy
- [ ] Add support for embedding models
- [ ] Enhance capability detection

## License

MIT License - see [LICENSE](LICENSE) for details.

## Links

- **Registry Data**: https://llmring.github.io/registry/
- **Main Project**: https://github.com/llmring/llmring
- **Documentation**: https://llmring.ai/docs
- **API Reference**: https://api.llmring.ai

---

*Built with ❤️ by the LLMRing team*
