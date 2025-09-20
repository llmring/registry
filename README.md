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
├── sources/            # Source documents for audit trail
│   ├── html/           # HTML documents from provider websites
│   ├── pdfs/           # PDF documentation files
│   └── screenshots/    # Visual captures if needed
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

## Setup

### Installation

```bash
# Clone the repository
git clone https://github.com/llmring/registry.git
cd registry

# Install with uv (recommended)
uv sync
uv pip install -e .

# First time only: install browser for PDF fetching
uv run playwright install chromium
```

### Environment Configuration

Create a `.env` file with your API keys for model extraction:

```bash
ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
```

## How to Update Models

When providers release new models or change pricing, follow these steps:

### 1. Fetch Latest Documentation

```bash
# Fetch HTML, PDFs, and screenshots from all providers
uv run llmring-registry fetch --provider all
```

This downloads:
- HTML pages to `sources/html/[provider]/`
- PDFs to `sources/pdfs/[provider]/`
- Screenshots to `sources/screenshots/[provider]/`

### 2. Extract Model Information

```bash
# Extract models using LLM-based extraction
uv run llmring-registry extract --provider all --timeout 120
```

This creates draft files in `drafts/` with extracted model information.

### 3. Review and Accept Changes

```bash
# Review changes for each provider
uv run llmring-registry review-draft --provider openai
uv run llmring-registry review-draft --provider anthropic
uv run llmring-registry review-draft --provider google

# If everything looks good, accept all changes
uv run llmring-registry review-draft --provider openai --accept-all
uv run llmring-registry review-draft --provider anthropic --accept-all
uv run llmring-registry review-draft --provider google --accept-all
```

### 4. Publish New Version

```bash
# Promote to production
uv run llmring-registry promote --provider openai
uv run llmring-registry promote --provider anthropic
uv run llmring-registry promote --provider google
```

This creates:
- Updated models at `pages/[provider]/models.json`
- Version snapshot at `pages/[provider]/v/[N]/models.json`
- Archived sources at `pages/[provider]/v/[N]/sources/`

### 5. Commit and Push

```bash
git add -A
git commit -m "Update models for [providers]"
git push
```

## Single Provider Update

To update just one provider (e.g., after OpenAI announces new models):

```bash
# Complete workflow for single provider
uv run llmring-registry fetch --provider openai
uv run llmring-registry extract --provider openai
uv run llmring-registry review-draft --provider openai --accept-all
uv run llmring-registry promote --provider openai

# Commit
git add -A && git commit -m "Update OpenAI models" && git push
```

## Directory Structure

```
registry/
├── sources/                # Source documents (working directory)
│   ├── html/              # HTML pages by provider
│   │   ├── google/
│   │   ├── anthropic/
│   │   └── openai/
│   ├── pdfs/              # PDF documents by provider
│   │   └── [provider]/
│   └── screenshots/       # Page screenshots by provider
│       └── [provider]/
├── drafts/                # Extracted model drafts pending review
├── models/                # Current production models
├── pages/                 # Versioned archives for GitHub Pages
│   └── [provider]/
│       ├── models.json    # Current version
│       └── v/             # Historical versions
│           └── [N]/
│               ├── models.json
│               └── sources/    # Archived source docs
└── llmring.lock          # Model aliases for extraction
```

## Troubleshooting

- **Extraction timeout**: Increase `--timeout` parameter (default 60 seconds)
- **Missing models**: Check screenshots to verify page loaded fully
- **Wrong data extracted**: Manually edit draft JSON before review
- **API key errors**: Ensure `.env` file has valid API keys

## Additional Commands

```bash
# List all models in the registry
uv run llmring-registry list

# Export models to markdown
uv run llmring-registry export --output markdown > models.md

# Validate registry data
uv run llmring-registry validate

# Show help for any command
uv run llmring-registry [command] --help
```

## Model Schema

Each provider's JSON file contains models in dictionary format with `provider:model` keys for fast lookup:

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

- Directories `sources/html/`, `sources/pdfs/`, and `drafts/` are auto-created if missing by `extract`.
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
├── sources/                  # Source documents for audit trail
│   ├── html/                 # HTML pages from providers
│   ├── pdfs/                 # PDF documentation files
│   └── screenshots/          # Visual captures if needed
├── models/                   # Current production JSON files
└── drafts/                   # Work-in-progress extractions
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
