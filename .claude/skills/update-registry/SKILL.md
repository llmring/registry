---
name: update-registry
description: Guide through the complete registry update workflow for a provider (manual fetch, Claude-guided extraction, review, promote). Use when updating model information for OpenAI, Anthropic, or Google.
---

# Registry Update Skill

This skill guides you through updating the LLMRing model registry for a provider using a simplified, Claude-guided extraction workflow.

## When to Use This Skill

Invoke this skill when:
- Juan asks to "update the registry" for a provider
- Juan mentions updating models for OpenAI, Anthropic, or Google
- Juan says he needs to add new models or update pricing
- Juan references provider documentation changes

## Workflow Overview

The simplified registry update process has 4 phases:

1. **Fetch**: Ask user to save latest documentation manually
2. **Extract**: Read source file and extract models using Claude's intelligence
3. **Review**: Compare draft against current production data
4. **Promote**: Move draft to production with versioning and commit

## Phase 1: Fetch Documentation

Ask Juan to manually save the documentation page:

1. Provide the correct URL for the provider:
   - Anthropic: https://docs.anthropic.com/en/docs/about-claude/models/overview
   - OpenAI: https://platform.openai.com/docs/models
   - Google: https://ai.google.dev/gemini-api/docs/models

2. Ask him to save it to: `sources/{provider}/{YYYY-MM-DD}-models.md`
   - Use today's date in the filename
   - Markdown format is preferred
   - If he saves as HTML/PDF, that's also fine

3. Confirm the file exists before proceeding:
   ```bash
   ls sources/{provider}/{date}-models.md
   ```

## Phase 2: Extract Models (Claude-Guided)

This is where the new simplified approach happens. YOU (Claude) will:

1. **Read the source file** using the Read tool
2. **Extract model information** using your intelligence
3. **Write the draft JSON** using the Write tool

### Extraction Schema

When extracting, create a JSON file with this structure:

```json
{
  "provider": "anthropic",
  "extraction_date": "2025-10-20T...",
  "sources": {
    "documents": 1,
    "models_extracted": 10
  },
  "models": {
    "anthropic:model-name": {
      "provider": "anthropic",
      "model_name": "exact-api-identifier",
      "display_name": "Human Friendly Name",
      "description": "Full description of capabilities",
      "model_aliases": ["alternative", "names"],

      // Pricing (required, dollars per million tokens)
      "dollars_per_million_tokens_input": 3.0,
      "dollars_per_million_tokens_output": 15.0,

      // Optional pricing fields (set to null if not provided)
      "dollars_per_million_tokens_cached_input": null,
      "dollars_per_million_tokens_cache_write_5m": 3.75,
      "dollars_per_million_tokens_cache_write_1h": 6.0,
      "dollars_per_million_tokens_cache_read": 0.3,
      "dollars_per_million_tokens_input_long_context": null,
      "dollars_per_million_tokens_output_long_context": null,
      "dollars_per_million_tokens_output_thinking": null,
      "cache_storage_cost_per_million_tokens_per_hour": null,
      "long_context_threshold_tokens": 200000,

      // Token limits (required)
      "max_input_tokens": 136000,
      "max_output_tokens": 64000,

      // Capabilities (boolean, default to reasonable values)
      "supports_vision": true,
      "supports_function_calling": true,
      "supports_json_mode": true,
      "supports_parallel_tool_calls": true,
      "supports_streaming": true,
      "supports_audio": false,
      "supports_documents": true,
      "supports_json_schema": true,
      "supports_logprobs": false,
      "supports_multiple_responses": false,
      "supports_caching": true,
      "supports_thinking": true,
      "supports_long_context_pricing": true,
      "is_reasoning_model": false,
      "supports_temperature": true,
      "supports_system_message": true,
      "supports_pdf_input": false,

      // Metadata (set to null if unknown)
      "api_endpoint": null,
      "requires_flat_input": false,
      "temperature_values": null,
      "max_temperature": null,
      "min_temperature": null,
      "max_tools": null,
      "supports_tool_choice": true,
      "tool_call_format": null,
      "speed_tier": null,
      "intelligence_tier": null,
      "requires_tier": 0,
      "requires_waitlist": false,
      "model_family": null,
      "recommended_use_cases": [],
      "is_active": true,
      "release_date": null,
      "deprecated_date": null,
      "added_date": null
    }
  }
}
```

### Extraction Guidelines

**CRITICAL RULES:**

1. **Context Window vs Max Input Tokens:**
   - If doc says "Context Window: 200K, Max Output: 64K"
   - Then: `max_input_tokens = 136000` (200K - 64K)
   - NEVER use context window directly as max_input_tokens!

2. **Pricing:**
   - Convert all pricing to dollars per million tokens
   - Only include pricing fields the provider publishes
   - Set unpublished fields to `null`, don't guess
   - For tiered pricing, use the PAID tier

3. **Model Names:**
   - Use the exact API identifier as `model_name`
   - Use simpler names in `model_aliases` array
   - Example: `model_name: "claude-sonnet-4-5-20250929"`, `model_aliases: ["claude-sonnet-4-5"]`

4. **Capabilities:**
   - Set based on what the documentation says
   - Use `true`/`false`, not `null` for boolean fields
   - If unsure, use conservative defaults (false for new features)

5. **Provider-Specific:**
   - **Anthropic:** Always supports function_calling, json_schema, json_mode, caching
   - **OpenAI:** Check for reasoning models (o1, o3, gpt-5 series)
   - **Google:** Watch for long-context pricing tiers

### Extraction Process

1. Read the source file
2. Identify all models mentioned
3. For each model, extract the information per the schema above
4. Validate as you go:
   - All required fields present?
   - Pricing makes sense? (input < output usually)
   - Token limits reasonable? (max_input + max_output <= context)
   - No obvious typos or errors?
5. Write the draft JSON to `drafts/{provider}.{date}.draft.json`
6. Tell Juan what you extracted:
   ```
   Extracted 10 models:
   - Model 1 name (key details)
   - Model 2 name (key details)
   ...
   ```

## Phase 3: Review Changes

Compare the draft against current production:

```bash
uv run llmring-registry review-draft --provider {provider}
```

This creates a diff file showing:
- Added models
- Removed models
- Changed fields

**Your job:**
1. Run the review command
2. Read the diff file at `drafts/{provider}.{date}.draft.diff.json`
3. Summarize changes for Juan in plain English:
   - "Added 2 new models: X, Y"
   - "Updated pricing for 6 models"
   - "Changed max_output_tokens for Model Z from A to B"
4. Highlight significant changes
5. Ask if he wants to proceed or make edits

If Juan wants to edit:
- Guide him to `drafts/{provider}.{date}.draft.json`
- Wait for confirmation that edits are complete
- Re-run review if needed

## Phase 4: Promote to Production

Once Juan approves:

```bash
uv run llmring-registry promote --provider {provider}
```

This will:
- Merge draft into current registry (preserving existing fields)
- Increment version number
- Create versioned snapshot at `pages/{provider}/v/{N}/`
- Archive source docs to `pages/{provider}/v/{N}/sources/`
- Delete the draft file

**After promotion:**
1. Verify files were updated
2. Show Juan what changed
3. Prepare git commit

## Phase 5: Commit Changes

```bash
git add sources/{provider}/ pages/{provider}/ models/{provider}.json manifest.json
git status
```

Suggest a commit message following this pattern:

```
Update {provider} models - {date}

Added new models:
- Model 1 (description)
- Model 2 (description)

Updated existing models:
- Model 3: New pricing ($X → $Y)
- Model 4: Added caching support

Deprecated:
- Model 5 (marked as inactive)
```

Create the commit but DO NOT push unless Juan explicitly asks.

## Error Handling

### Source file issues
- Check the file exists
- Verify it's readable markdown/text
- Ask Juan to re-save if corrupted

### Extraction issues
- If you're unsure about a field, ask Juan
- If pricing seems wrong, double-check the source
- If capabilities are unclear, check provider API docs

### Promotion issues
- If promote fails, check error message carefully
- Common issue: schema validation (check required fields)
- Verify the draft JSON is well-formed

## Provider-Specific Notes

**Anthropic:**
- Comprehensive documentation
- Always includes pricing for cache writes (5m and 1h)
- All models support function calling, JSON schema, caching
- Watch for extended thinking support

**OpenAI:**
- Frequent updates
- Reasoning models (o1, o3, gpt-5) have special constraints
- Check for "latest" aliases
- Cached pricing uses simpler structure

**Google:**
- Complex model families (Flash, Pro, Ultra)
- Long-context pricing tiers
- Experimental vs stable models
- Watch for token count variations

## Best Practices

1. **Read carefully** - Don't rush extraction
2. **Validate as you go** - Check each model makes sense
3. **Preserve data** - The promote merge logic keeps existing fields
4. **Ask questions** - If unsure, ask Juan rather than guessing
5. **Review thoroughly** - Pricing errors are costly
6. **Commit clearly** - Good commit messages help future updates

## Communication Style

- Be systematic and methodical
- Explain what you're doing at each step
- Show Juan what you extracted before proceeding
- Highlight important changes clearly
- Ask for confirmation before irreversible operations
- If something looks wrong, say so immediately

## Example Session

```
Juan: "Update the Anthropic registry"

Claude: "I'll help you update the Anthropic models registry.

Please save the latest Anthropic documentation to:
  sources/anthropic/2025-10-20-models.md

Visit: https://docs.anthropic.com/en/docs/about-claude/models/overview

Let me know when you've saved it."

Juan: "Done"

Claude: "Great! Let me read the file and extract the models..."

[Claude reads sources/anthropic/2025-10-20-models.md]
[Claude extracts model information]
[Claude writes to drafts/anthropic.2025-10-20.draft.json]

Claude: "Extraction complete! I found 10 models:

New models:
- Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)
- Claude Haiku 4.5 (claude-haiku-4-5-20251001)

Existing models (6 models with updated pricing/capabilities):
- All models now include cache pricing (5m and 1h writes)
- Added extended thinking support to eligible models
- Updated descriptions

Let me compare this against production..."

[Runs review-draft]

Claude: "Summary of changes:
- Added: 2 new models (Sonnet 4.5, Haiku 4.5)
- Updated: 6 models with cache pricing and capabilities
- Removed: 0 models
- Changed: Pricing and capability flags for all existing models

Should I proceed with promotion?"

Juan: "Yes"

Claude: "Promoting to production..."

[Runs promote]

Claude: "✅ Promotion complete!

Files updated:
- pages/anthropic/models.json (production)
- pages/anthropic/v/4/models.json (version snapshot)
- models/anthropic.json (local copy)
- manifest.json (updated version)

Ready to commit. Suggested message:

Update Anthropic models - 2025-10-20

Added new models:
- Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)
- Claude Haiku 4.5 (claude-haiku-4-5-20251001)

Updated all existing models with:
- Added caching support with 5m/1h cache write pricing
- Added extended thinking support (where applicable)
- Simplified descriptions

Should I create this commit?"
```

## Important Notes

- This skill is INTERACTIVE - you work with Juan step by step
- You do the extraction using your intelligence, not an LLM pipeline
- ALWAYS validate as you extract - you can see the source!
- NEVER skip the review phase - Juan needs to see changes
- DO explain your reasoning if something seems unusual
- TRACK progress using TodoWrite throughout the workflow
