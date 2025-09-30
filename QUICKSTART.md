# Registry Quick Start Guide

Quick reference for common registry operations.

## Setup

```bash
# Install dependencies
uv sync

# Install Playwright for screenshots (first time only)
uv run playwright install chromium

# Set up API keys (create .env file)
echo "ANTHROPIC_API_KEY=your_key" > .env
echo "GOOGLE_API_KEY=your_key" >> .env
```

## Common Commands

### 1. Find Documentation Sources

```bash
# Show where to get provider documentation
uv run llmring-registry sources

# For specific provider
uv run llmring-registry sources --provider openai
```

### 2. Extract Models

```bash
# Extract from documents in sources/<provider>/
uv run llmring-registry extract --provider openai

# Extract all providers
uv run llmring-registry extract --provider all

# Increase timeout for large documents
uv run llmring-registry extract --provider openai --timeout 300
```

### 3. Validate Extracted Data (NEW!)

```bash
# Validate all models in draft
uv run llmring-registry validate --provider openai

# Quick check (5 random models)
uv run llmring-registry validate --provider openai --sample 5

# With debug output
uv run llmring-registry validate --provider openai --debug
```

### 4. Check Schema Compliance

```bash
# Generate compliance report
uv run llmring-registry normalize --provider openai --report

# Apply normalization (creates backup)
uv run llmring-registry normalize --provider openai

# Dry run (preview changes)
uv run llmring-registry normalize --provider openai --dry-run
```

### 5. Review Changes

```bash
# Show diff against current registry
uv run llmring-registry review-draft --provider openai

# Accept all changes
uv run llmring-registry review-draft --provider openai --accept-all
```

### 6. Promote to Production

```bash
# Promote single provider
uv run llmring-registry promote --provider openai

# Promote all available drafts
uv run llmring-registry promote --provider all
```

## Full Workflow Example

```bash
# 1. Check where to get docs
uv run llmring-registry sources --provider openai

# 2. Add screenshots/PDFs to sources/openai/
#    (manually download from URLs shown by sources command)

# 3. Extract models
uv run llmring-registry extract --provider openai

# 4. Validate extracted data
uv run llmring-registry validate --provider openai

# 5. Review validation report
cat drafts/openai.validation.json | jq '.issues[] | select(.severity=="error")'

# 6. Fix any critical issues in the draft file
#    (edit drafts/openai.YYYY-MM-DD.draft.json)

# 7. Re-validate after fixes
uv run llmring-registry validate --provider openai

# 8. Check compliance
uv run llmring-registry normalize --provider openai --report

# 9. Promote to production
uv run llmring-registry promote --provider openai
```

## Utility Commands

```bash
# List available drafts
uv run llmring-registry list-drafts

# Show registry statistics
uv run llmring-registry stats --provider openai

# Export data
uv run llmring-registry export --output markdown
```

## File Structure

```
registry/
├── sources/                    # Source documents (INPUT)
│   ├── openai/
│   │   ├── 2025-09-30-openai-pricing.png
│   │   ├── 2025-09-30-openai-models.png
│   │   └── ...
│   ├── anthropic/
│   └── google/
│
├── drafts/                     # Work in progress
│   ├── openai.2025-09-30.draft.json
│   ├── openai.validation.json
│   └── ...
│
├── models/                     # Current production (OUTPUT)
│   ├── openai.json
│   ├── anthropic.json
│   └── google.json
│
└── pages/                      # Published with versions
    ├── openai/
    │   ├── models.json         # Current version
    │   └── v/
    │       ├── 1/models.json
    │       └── 2/models.json   # Archived versions
    └── ...
```

## Troubleshooting

### "No draft found"
```bash
# Check drafts directory
ls -la drafts/

# Extract first if no draft exists
uv run llmring-registry extract --provider openai
```

### "No source documents found"
```bash
# Check sources directory
ls -la sources/openai/

# Use sources command to find URLs
uv run llmring-registry sources --provider openai

# Download documentation and save to sources/openai/
```

### Validation timeout
```bash
# Increase timeout (default: 120s)
uv run llmring-registry validate --provider openai --timeout 300
```

### Extraction fails
```bash
# Enable debug logging
uv run llmring-registry extract --provider openai --debug

# Check for image size issues (will auto-resize)
# Check API key is set in .env
```

## Configuration

### Model Aliases (llmring.lock)

The registry uses two model aliases:

- **extractor**: Used for extraction (default: `gemini-2.5-pro`)
- **validator**: Used for validation (default: `claude-3-7-sonnet`)

To change:

```toml
[[profiles.default.bindings]]
alias = "extractor"
provider = "openai"
model = "gpt-5"

[[profiles.default.bindings]]
alias = "validator"
provider = "anthropic"
model = "claude-opus-4-1"
```

## Best Practices

1. **Always validate after extraction**
   ```bash
   uv run llmring-registry extract --provider openai
   uv run llmring-registry validate --provider openai
   ```

2. **Fix critical errors before promotion**
   - Zero token limits
   - Missing/zero pricing
   - Incorrect model names

3. **Use descriptive file names** for sources
   - Good: `2025-09-30-openai-gpt5-pricing.png`
   - Bad: `screenshot.png`

4. **Keep sources organized**
   - One directory per provider
   - Include date in filename
   - Save both overview and detail pages

5. **Review validation reports carefully**
   ```bash
   # Focus on errors first
   jq '.issues[] | select(.severity=="error")' drafts/openai.validation.json
   ```

## Getting Help

```bash
# Command help
uv run llmring-registry --help
uv run llmring-registry validate --help

# Verbose output
uv run llmring-registry -v extract --provider openai

# Debug mode
uv run llmring-registry extract --provider openai --debug
```

## See Also

- [VALIDATION_WORKFLOW.md](VALIDATION_WORKFLOW.md) - Detailed validation workflow
- [README.md](README.md) - Full documentation
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contributing guidelines