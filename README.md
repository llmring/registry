# LLMRing Registry

> ⚠️ Pre-release notice
>
> The pricing, token limits, and capabilities in this registry are under active validation and may be inaccurate. Do not rely on these numbers for production decisions. Always verify against the providers' official documentation.

*Complies with source-of-truth v3.5*

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
│   ├── HTML Scraping (BeautifulSoup + Regex)
│   └── PDF Analysis (via LLMRing's unified interface)
│       ├── OpenAI: Assistants API
│       ├── Anthropic: Direct PDF support
│       └── Google: Direct PDF support
└── Output
    ├── models/
    │   ├── openai.json
    │   ├── anthropic.json
    │   └── google.json
    └── manifest.json
```

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/llmring/registry.git
cd registry

# Install with uv (recommended)
uv sync

# Or with pip
pip install -e .
```

### Manual Curation Workflow (Human-validated)

0. Gather source materials (optional but recommended):

```bash
# Show where to get docs and how to save PDFs
uv run registry sources

# Fetch pricing/docs HTML (lightweight)
uv run registry fetch-html --provider openai --output-dir html_cache

# Generate PDFs with a headless browser (requires Playwright)
uv run registry fetch --provider openai --output-dir pdfs
```

1. Generate a draft JSON using the extractor (best-effort), or by hand:

```bash
# Best-effort draft generation from PDFs (writes to drafts/ only)
uv run registry extract --provider openai --pdfs-dir pdfs
```
2. Review differences vs current curated file:

```bash
uv run registry review-draft --provider openai --draft drafts/openai.2025-08-20.json
# Inspect the generated .diff.json report

# Optionally accept all to create a reviewed file
uv run registry review-draft --provider openai --draft drafts/openai.2025-08-20.json --accept-all
```

3. Promote the reviewed file to publish and archive:

```bash
uv run registry promote --provider openai --reviewed drafts/openai.reviewed.json
```

This will:
- Bump `version` and `updated_at`
- Write `openai/v/<version>/models.json`
- Replace `openai/models.json`

### Legacy Automation (deprecated)

Commands like `fetch`, `fetch-html`, and `extract*` remain for reference but are deprecated. The official process is manual, human-validated curation.

```bash
# View available commands
uv run registry --help

# Fetch latest documentation
uv run registry fetch-html --provider all

# Extract models with comprehensive dual-source validation
uv run registry extract-comprehensive --provider all

# List all extracted models
uv run registry list

# Export to markdown for documentation
uv run registry export --output markdown > models.md
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

Each provider's JSON file contains models with this structure (dictionary, not list):

```json
{
  "provider": "openai",
  "version": 2,
  "updated_at": "2025-08-20T00:00:00Z",
  "models": {
    "openai:gpt-4o-mini": {
      "provider": "openai",
      "model_name": "gpt-4o-mini",
      "display_name": "GPT-4 Optimized Mini",
      "max_input_tokens": 128000,
      "max_output_tokens": 16384,
      "dollars_per_million_tokens_input": 0.15,
      "dollars_per_million_tokens_output": 0.60,
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
# Fetch HTML pages (no browser required)
uv run registry fetch-html --provider openai

# Fetch as PDFs (requires Playwright)
uv run registry fetch --provider all
```

### Extraction

```bash
# Extract from HTML only
uv run registry extract-html --provider all

# Extract from PDFs only (requires LLM API keys)
uv run registry extract --provider all

# Comprehensive extraction (recommended)
uv run registry extract-comprehensive --provider all

# Interactive mode for conflict resolution
uv run registry extract-comprehensive --provider all --interactive
```

### Data Management

```bash
# List all models with pricing
uv run registry list

# Validate JSON structure
uv run registry validate

# Export for documentation
uv run registry export --output markdown
uv run registry export --output json
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
      - run: pip install uv
      - run: uv sync
      - run: uv run registry fetch-html --provider all
      - run: uv run registry extract-comprehensive --provider all
      - run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add models/
          git commit -m "Update model registry $(date +%Y-%m-%d)" || true
          git push
```

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
uv run registry fetch-html --provider newprovider
uv run registry extract-comprehensive --provider newprovider
```

### Testing

```bash
# Run tests
uv run pytest

# Test extraction for a specific provider
uv run registry extract-comprehensive --provider openai --interactive

# Validate output
uv run registry validate --models-dir models
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