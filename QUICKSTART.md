# Registry Quick Start Guide

Quick reference for common registry operations using the simplified Claude-guided workflow.

## Setup

```bash
# Install dependencies
uv sync

# That's it! No API keys or browser automation needed.
```

## Updating Models (Claude-Guided Workflow)

The simplest way to update the registry is using the `update-registry` skill in Claude Code:

```
In Claude Code:
> Update the anthropic registry

Claude will guide you through:
1. Saving the latest documentation
2. Extracting models
3. Reviewing changes
4. Promoting to production
5. Committing changes
```

## Manual Commands

If you prefer to work with individual commands:

### 1. Save Source Documentation

Manually save provider documentation to `sources/{provider}/YYYY-MM-DD-models.md`

**Provider URLs:**
- **Anthropic**: https://docs.anthropic.com/en/docs/about-claude/models/overview
- **OpenAI**: https://platform.openai.com/docs/models
- **Google**: https://ai.google.dev/gemini-api/docs/models

### 2. Extract Models (with Claude)

Ask Claude Code to read the source file and create a draft JSON following the registry schema.

The draft should be saved to: `drafts/{provider}.YYYY-MM-DD.draft.json`

See `.claude/skills/update-registry/SKILL.md` for complete extraction guidelines.

### 3. Review Changes

```bash
# Show diff against current registry
uv run llmring-registry review-draft --provider anthropic

# This creates: drafts/anthropic.YYYY-MM-DD.draft.diff.json
```

### 4. Promote to Production

```bash
# Promote single provider
uv run llmring-registry promote --provider anthropic

# Promote all available drafts
uv run llmring-registry promote --provider all
```

### 5. Commit Changes

```bash
git add sources/ pages/ models/ manifest.json
git commit -m "Update Anthropic models - 2025-10-20"
git push
```

## Utility Commands

### Check Schema Compliance

```bash
# Generate compliance report
uv run llmring-registry normalize --provider anthropic --report

# Apply normalization (creates backup)
uv run llmring-registry normalize --provider anthropic

# Dry run (preview changes)
uv run llmring-registry normalize --provider anthropic --dry-run
```

### List and Export

```bash
# List available drafts
uv run llmring-registry list-drafts

# Show registry statistics
uv run llmring-registry stats --provider anthropic

# Export data
uv run llmring-registry export --output markdown
```

## Full Workflow Example

```bash
# In Claude Code:
> Update the OpenAI registry

# Claude asks you to save documentation
# Visit: https://platform.openai.com/docs/models
# Save to: sources/openai/2025-10-20-models.md

# Claude extracts models and creates draft
# Claude runs review and shows you changes
# You approve
# Claude promotes to production
# Claude commits changes

# Done!
```

## Manual Workflow Example

If working without Claude Code:

```bash
# 1. Save documentation manually
# Visit provider docs and save to sources/openai/2025-10-20-models.md

# 2. Create draft JSON manually (or ask Claude to help)
# Follow schema in .claude/skills/update-registry/SKILL.md
# Save to: drafts/openai.2025-10-20.draft.json

# 3. Review changes
uv run llmring-registry review-draft --provider openai

# 4. Check the diff
cat drafts/openai.2025-10-20.draft.diff.json

# 5. Promote if satisfied
uv run llmring-registry promote --provider openai

# 6. Commit
git add sources/openai/ pages/openai/ models/openai.json manifest.json
git commit -m "Update OpenAI models - 2025-10-20"
git push
```

## File Structure

```
registry/
├── sources/                    # Source documentation
│   ├── anthropic/
│   │   └── 2025-10-20-models.md
│   ├── openai/
│   └── google/
│
├── drafts/                     # Work in progress
│   ├── anthropic.2025-10-20.draft.json
│   └── anthropic.2025-10-20.draft.diff.json
│
├── models/                     # Current production
│   ├── anthropic.json
│   ├── openai.json
│   └── google.json
│
└── pages/                      # Published with versions
    └── {provider}/
        ├── models.json         # Current version
        └── v/{N}/
            ├── models.json     # Archived versions
            └── sources/        # Archived source docs
```

## Troubleshooting

### "No draft found"
```bash
# Check drafts directory
ls -la drafts/

# Create draft manually or use Claude Code
```

### "Promote validation fails"
```bash
# Check the error message
# Common issues:
# - Missing required fields (model_name, pricing)
# - Invalid JSON syntax
# - Negative pricing values

# Edit draft and retry
vim drafts/openai.2025-10-20.draft.json
uv run llmring-registry promote --provider openai
```

### "Changes not detected"
```bash
# Check if draft is actually different
uv run llmring-registry review-draft --provider openai

# If no changes in diff, that's expected
```

## Getting Help

```bash
# Command help
uv run llmring-registry --help
uv run llmring-registry promote --help

# Verbose output
uv run llmring-registry -v promote --provider openai
```

## See Also

- [README.md](README.md) - Full documentation
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contributing guidelines
- [.claude/skills/update-registry/SKILL.md](.claude/skills/update-registry/SKILL.md) - Extraction schema
