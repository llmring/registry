# Registry Validation Workflow

This document describes the enhanced validation workflow for the LLMRing registry, which ensures high data quality through automated LLM-based validation.

## Overview

The new workflow adds two critical steps between extraction and promotion:

1. **Normalization**: Standardizes schema format (null vs empty arrays, metadata structure)
2. **Validation**: Uses an LLM to verify each model against source documentation

## Complete Workflow

```
1. Extract    →  2. Normalize  →  3. Validate  →  4. Review  →  5. Promote
   (LLM)          (Auto)           (LLM)           (Manual)     (Auto)
```

### Step 1: Extract Models from Documentation

```bash
# Extract from all document types (PNG, PDF, MD)
uv run llmring-registry extract --provider openai
```

**What it does:**
- Processes screenshots, PDFs, and markdown files
- Uses `extractor` alias (gemini-2.5-pro) to extract structured model data
- Automatically normalizes output schema
- Creates `drafts/openai.YYYY-MM-DD.draft.json`

**Output:**
- Draft file with standardized metadata:
  ```json
  {
    "provider": "openai",
    "extraction_date": "2025-09-30T...",
    "sources": {
      "documents": 29,
      "png_files": 29,
      "pdf_files": 0,
      "md_files": 0,
      "models_extracted": 25
    },
    "models": { ... }
  }
  ```

### Step 2: Normalize Schema (Optional, Auto-Applied)

```bash
# Check compliance
uv run llmring-registry normalize --provider openai --report

# Apply normalization manually if needed
uv run llmring-registry normalize --provider openai
```

**What it does:**
- Standardizes null vs empty array handling
- Ensures consistent metadata format
- Validates required fields
- Sets appropriate defaults

**Schema Rules:**
- `model_aliases`: `[]` not `null`
- `recommended_use_cases`: `[]` not `null`
- Optional strings: `null` not `""`
- Booleans: explicit `true`/`false`
- Token limits: `0` not `null` (if unknown)
- Pricing: must be > 0 (validation catches missing)

### Step 3: Validate Against Source Docs (NEW!)

```bash
# Validate all models
uv run llmring-registry validate --provider openai

# Quick check (sample 5 random models)
uv run llmring-registry validate --provider openai --sample 5

# Adjust timeout for large documents
uv run llmring-registry validate --provider openai --timeout 180
```

**What it does:**
- For **each model** in the draft:
  1. Loads the source documentation
  2. Uses `validator` alias (claude-3-7-sonnet) to check:
     - Model name correctness
     - Pricing accuracy (critical!)
     - Token limit calculations (context_window vs max_input_tokens)
     - Capability flags
     - Description completeness
  3. Flags errors, warnings, and improvement suggestions
  4. Generates structured validation report

**Validation Output:**
```
🔍 Validating 25 models for openai...
📁 Found 29 source documents
  [1/25] Validating openai:gpt-5...
    ✅ Valid (confidence: 0.95)
  [2/25] Validating openai:gpt-4.1...
    ❌ Issues found: 2
       ERROR: max_input_tokens should be 999232 (1M context - 768 output), not 967232
       WARNING: Description could include information about tool calling capabilities

📊 Validation Summary:
  Total models: 25
  ✅ Valid: 18
  ❌ With errors: 5
  ⚠️  With warnings: 7
  🎯 Avg confidence: 87%

⚠️  Top Issues:
  - openai:gpt-4.1-mini: max_input_tokens is 0, should be calculated from context window
    → Fix: Set max_input_tokens based on context_window - max_output_tokens
  - openai:o3-pro: Pricing appears to be per-token, not per-million-tokens
    → Fix: Multiply by 1,000,000 to convert to per-million rate

💾 Full report saved: drafts/openai.validation.json
```

**Validation Report Schema:**
```json
{
  "provider": "openai",
  "draft_file": "drafts/openai.2025-09-30.draft.json",
  "validation_date": "2025-09-30T...",
  "summary": {
    "total_models": 25,
    "valid_models": 18,
    "models_with_errors": 5,
    "models_with_warnings": 7,
    "average_confidence": 0.87
  },
  "issues": [
    {
      "model": "openai:gpt-4.1-mini",
      "severity": "error",
      "field": "max_input_tokens",
      "issue": "Value is 0, should be calculated from context window",
      "suggested_fix": "Set to context_window - max_output_tokens"
    }
  ],
  "model_results": [ ... ]
}
```

### Step 4: Review and Fix Issues

Based on validation report:

1. **Critical errors** (pricing, token limits): Fix manually in draft
2. **Apply suggested fixes** from validation report
3. **Re-run validation** after fixes:
   ```bash
   uv run llmring-registry validate --provider openai
   ```
4. **Iterate until clean** (or acceptable error rate)

Optional: Use the diff-based review:
```bash
# Generate diff against current registry
uv run llmring-registry review-draft --provider openai

# Review diff, then accept
uv run llmring-registry review-draft --provider openai --accept-all
```

### Step 5: Promote to Production

```bash
# Promote single provider
uv run llmring-registry promote --provider openai

# Promote all available drafts
uv run llmring-registry promote --provider all
```

**What it does:**
- Increments version number
- Calculates RFC 8785 JCS hash
- Writes to `models/openai.json`
- Publishes to `pages/openai/models.json`
- Archives to `pages/openai/v/N/models.json`
- Archives source documents with the version
- Updates `manifest.json`
- Deletes draft file

## Configuration

### Model Aliases in llmring.lock

```toml
[[profiles.default.bindings]]
alias = "extractor"
provider = "google"
model = "gemini-2.5-pro"
rationale = "Best extraction accuracy with strong JSON schema compliance"

[[profiles.default.bindings]]
alias = "validator"
provider = "anthropic"
model = "claude-3-7-sonnet-20250219"
rationale = "Best reasoning and analysis for validating extracted data"
```

**Why these models?**
- **Extractor (Gemini 2.5 Pro)**:
  - Excellent structured output compliance
  - Strong vision capabilities for screenshots
  - Good at following complex extraction rules

- **Validator (Claude 3.7 Sonnet)**:
  - Superior reasoning for validation tasks
  - Strong attention to detail
  - Better at catching subtle inconsistencies

## Best Practices

### When to Use Each Command

1. **After initial extraction**: Always run `validate`
   ```bash
   uv run llmring-registry extract --provider openai
   uv run llmring-registry validate --provider openai
   ```

2. **During development**: Use `--sample` for quick checks
   ```bash
   uv run llmring-registry validate --provider openai --sample 5
   ```

3. **Before promotion**: Full validation required
   ```bash
   uv run llmring-registry validate --provider openai
   # Fix issues, then:
   uv run llmring-registry promote --provider openai
   ```

4. **Schema compliance check**: Use `normalize --report`
   ```bash
   uv run llmring-registry normalize --provider openai --report
   ```

### Handling Validation Failures

**Zero token limits:**
```json
// BAD:
"max_input_tokens": 0

// GOOD:
"max_input_tokens": 128000  // context_window - max_output_tokens
```

**Context window confusion:**
```
Context Window: 128K
Max Output: 4K

// WRONG:
"max_input_tokens": 128000  // This is the TOTAL

// RIGHT:
"max_input_tokens": 124000  // 128K - 4K
```

**Pricing conversions:**
```
// Docs say: $2.50 per 1M tokens
"dollars_per_million_tokens_input": 2.50  ✅

// Docs say: $0.0025 per 1K tokens
"dollars_per_million_tokens_input": 2.50  ✅ ($0.0025 * 1000)

// Docs say: Free tier: $0, Paid tier: $5
"dollars_per_million_tokens_input": 5.0  ✅ (use PAID tier)
```

## CI/CD Integration

### GitHub Actions Workflow

```yaml
name: Validate Registry Updates

on:
  pull_request:
    paths:
      - 'drafts/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          uv sync

      - name: Validate drafts
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
        run: |
          # Validate all draft files
          for draft in drafts/*.draft.json; do
            provider=$(basename "$draft" | cut -d. -f1)
            uv run llmring-registry validate --provider "$provider" --draft "$draft"
          done

      - name: Upload validation reports
        uses: actions/upload-artifact@v3
        with:
          name: validation-reports
          path: drafts/*.validation.json
```

## Troubleshooting

### Validation timeouts

```bash
# Increase timeout (default: 120s)
uv run llmring-registry validate --provider openai --timeout 300
```

### No source documents found

```
⚠️  No source documents found in sources/openai
```

**Solution**: Ensure documents are in `sources/[provider]/` directory
```bash
ls -la sources/openai/
# Should show *.png, *.pdf, or *.md files
```

### Validation suggests wrong prices

**Issue**: Validator sees free-tier pricing

**Solution**: Ensure source docs show paid tier pricing, or manually fix and document

### High error rate

If validation finds >20% errors:
1. Check source document quality
2. Review extraction prompt in `document_parser.py`
3. Consider re-extracting with updated prompts
4. Use `--debug` flag for detailed logs

## Performance

**Extraction time** (per provider):
- ~5-10 minutes for 20-30 documents
- Varies with document size and complexity

**Validation time** (per provider):
- ~2-3 minutes per model (default timeout: 120s)
- 25 models ≈ 50-75 minutes total
- Use `--sample` for faster testing

**Total workflow** (extract → validate → promote):
- ~1-2 hours per provider (full validation)
- ~15-20 minutes per provider (with sampling)

## Future Enhancements

- [ ] Parallel validation (validate multiple models simultaneously)
- [ ] Incremental validation (only validate changed models)
- [ ] Confidence-based sampling (validate low-confidence models first)
- [ ] Auto-fix suggestions (apply suggested fixes automatically with confirmation)
- [ ] Validation caching (skip re-validation if docs unchanged)