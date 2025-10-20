# LLMRing Registry - Claude Instructions

This is the LLMRing Registry project - a simplified system for maintaining model metadata (pricing, capabilities, token limits) for major LLM providers.

## Project Overview

**What this does:**
- Maintains up-to-date model information for OpenAI, Anthropic, and Google
- Serves model data via GitHub Pages for the LLMRing ecosystem
- Uses a simplified Claude-guided extraction workflow (YOU are the extractor!)

**What this is NOT:**
- Not an automated extraction pipeline (we deleted that - it was over-engineered)
- Not a data validation system (we deleted that too - it was circular)
- Not a web scraper (manual doc capture works better)

## Architecture (Simple!)

```
Workflow:
1. Juan saves provider docs → sources/{provider}/YYYY-MM-DD-models.md
2. You (Claude) read and extract → drafts/{provider}.YYYY-MM-DD.draft.json
3. review-draft command → generates diff
4. promote command → merges to production with versioning
5. Commit to git

That's it!
```

## Key Commands

**You will use these:**
- `uv run llmring-registry review-draft --provider {provider}` - Generate diff
- `uv run llmring-registry promote --provider {provider}` - Merge to production
- `uv run llmring-registry normalize --provider {provider}` - Optional schema cleanup

**You will NOT use these (they don't exist anymore):**
- ~~`extract`~~ - Deleted! You do extraction directly now
- ~~`validate`~~ - Deleted! You validate as you extract
- ~~`fetch`~~ - Deleted! Manual doc capture works better

## The update-registry Skill

**IMPORTANT:** When Juan says "update the {provider} registry", use the `update-registry` skill:

```
Skill command: update-registry
```

This skill guides you through:
1. Asking Juan to save source docs
2. Reading the source file
3. Extracting models (YOU do this!)
4. Reviewing changes
5. Promoting to production
6. Committing changes

**Read the skill file:** `.claude/skills/update-registry/SKILL.md`

## Extraction Guidelines (Critical!)

When extracting models from source documentation:

### 1. Trust the Source Documentation

**CRITICAL:**
- Your training data cutoff is January 2025
- Providers release new models AFTER your cutoff
- If docs say "Claude Sonnet 4.5" or "GPT-6" exists → IT'S REAL
- Don't second-guess model names or pricing you don't recognize
- Source file = GROUND TRUTH, not your memory

### 2. Follow the Schema Exactly

Extract to: `drafts/{provider}.YYYY-MM-DD.draft.json`

Required fields:
- `model_name` (exact API identifier)
- `display_name` (human-friendly)
- `dollars_per_million_tokens_input`
- `dollars_per_million_tokens_output`
- `max_input_tokens`
- `max_output_tokens`
- All capability flags (supports_vision, etc.)

Optional fields (set to null if not in docs):
- Cache pricing fields
- Long context pricing
- Thinking token pricing
- Metadata fields

**See the skill file for complete schema.**

### 3. Context Window vs Max Input Tokens

**CRITICAL CALCULATION:**
- If doc says: "Context Window: 200K, Max Output: 64K"
- Then: `max_input_tokens = 136000` (200K - 64K)
- **NEVER** use context window directly as max_input_tokens!

### 4. Provider-Specific Notes

**Anthropic:**
- Always supports: function_calling, json_schema, json_mode, caching
- Has 5m and 1h cache write pricing (both fields!)
- All models support extended thinking

**OpenAI:**
- Reasoning models: o1, o3, gpt-5 series
- Set `is_reasoning_model: true` for these
- Check for cached input pricing

**Google:**
- Long-context pricing tiers
- Separate input/output pricing above threshold
- Watch for thinking token pricing

## Optional: Validation Agent

If Juan wants extra confidence, you can launch an independent validation agent:

```python
# Use Task tool with general-purpose agent
# Agent reads source + draft independently
# Reports any discrepancies or errors
```

**When to suggest this:**
- Unfamiliar models (after your training cutoff)
- Complex pricing structures
- Juan explicitly asks for validation
- You're uncertain about something

## Smart Merge Logic (Preserve Production Data!)

**CRITICAL:** The promote command has smart merge logic:
- Only updates fields where draft has **non-null** values
- Preserves existing production values when draft has null
- Example: If production has `api_endpoint: "chat"` and draft has `api_endpoint: null`, production value is kept

**This means:**
- You can safely set fields to `null` when unsure
- Production metadata won't be lost
- Partial extractions are safe

## Git Workflow

**Always:**
1. Check for uncommitted changes before starting work
2. Commit the Anthropic update on main separately (already done)
3. Use descriptive commit messages

**Commit message pattern:**
```
Update {provider} models - YYYY-MM-DD

Added new models:
- Model name (description)

Updated existing models:
- Pricing changes
- New capabilities

Deprecated:
- Old models (if any)
```

## Common Tasks

### "Update the {provider} registry"
→ Use the `update-registry` skill (already created)

### "Review the registry code"
→ Focus on: promote.py, review.py, schema_utils.py

### "Fix a bug in the registry"
→ Check promote.py merge logic first (that's where bugs hide)

### "Add a new provider"
→ Just create sources/{provider}/ and pages/{provider}/
→ Use the same extraction workflow

## What NOT to Do

❌ Don't try to run `extract` or `validate` commands (they're deleted)
❌ Don't create complex extraction pipelines (we simplified on purpose)
❌ Don't doubt model names newer than Jan 2025 (trust the docs!)
❌ Don't create new documentation files without asking
❌ Don't add back complexity we removed

## Testing

**Current test status:**
- `tests/test_review_promote.py::test_promote_workflow` - FAILING (pre-existing)
- Other tests pass

**When making changes:**
- Run: `uv run pytest`
- Fix broken tests if you touch that code
- Don't add tests for deleted functionality

## Dependencies

**Only one dependency:** `click` (CLI framework)

**Why so few?**
- No LLM extraction (you do it!)
- No image processing (not needed)
- No web scraping (manual capture)
- No browser automation (not needed)

## Remember

- This project was SIMPLIFIED on 2025-10-20
- We deleted ~2,000 lines of complex extraction code
- The new workflow is: Claude reads → extracts → writes JSON
- It's much simpler, more accurate, and easier to maintain
- Keep it simple!

## Questions?

If uncertain about anything:
1. Check the skill file: `.claude/skills/update-registry/SKILL.md`
2. Check this file
3. Ask Juan

Trust yourself - you're smart enough to extract model data directly!
