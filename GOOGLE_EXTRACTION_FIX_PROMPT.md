# Prompt: Fix Google Gemini Registry Extraction

## Task

You need to fix the Google Gemini model extraction to include ALL required pricing dimensions: cached input pricing, long context pricing, thinking token pricing, cache storage costs, and thresholds. The current extraction is incomplete and has incorrect base pricing.

## Context

**Working Directory**: `/Users/juanre/prj/llmring-all/registry`

**Current Status**:
- OpenAI extraction: ✅ Complete and correct
- Anthropic extraction: ✅ Complete and correct
- Google extraction: ❌ Incomplete - missing most pricing fields

**Problem**: The Google draft at `drafts/google.2025-10-05.draft.json` is missing:
1. Cached input pricing (should be 75% discount)
2. Long context pricing tiers (2x premium for >200K tokens)
3. Thinking token pricing (up to 5.8x premium)
4. Cache storage costs
5. Long context thresholds

Additionally, some base pricing appears incorrect (e.g., gemini-2.5-pro shows $2.1/$6.3).

## Required Schema Fields

Each Google model must have these fields (set to `null` if not applicable):

```json
{
  // Base pricing
  "dollars_per_million_tokens_input": float,
  "dollars_per_million_tokens_output": float,

  // Cached pricing (75% discount from base)
  "dollars_per_million_tokens_cached_input": float | null,

  // Long context pricing (2x premium for >200K tokens)
  "dollars_per_million_tokens_input_long_context": float | null,
  "dollars_per_million_tokens_output_long_context": float | null,
  "long_context_threshold_tokens": int | null,  // e.g., 200000

  // Thinking token pricing (if different from base output)
  "dollars_per_million_tokens_output_thinking": float | null,

  // Cache storage costs
  "cache_storage_cost_per_million_tokens_per_hour": float | null,

  // Capability flags (auto-derived by schema but must have data)
  "supports_caching": boolean,
  "supports_thinking": boolean,
  "supports_long_context_pricing": boolean
}
```

## Source Files

### 1. Existing Google Source Documents

**Location**: `/Users/juanre/prj/llmring-all/registry/sources/google/`

**Files available**:
```
2025-09-21-google-gemini-1-5-flash-8b.png
2025-09-21-google-gemini-1-5-flash.png
2025-09-21-google-gemini-1-5-pro.png
2025-09-21-google-gemini-2-0-flash-lite.png
2025-09-21-google-gemini-2-0-flash-live.png
2025-09-21-google-gemini-2-0-flash.png
2025-09-21-google-gemini-2-5-flash-lite.png
2025-09-21-google-gemini-2-5-flash.png
2025-09-21-google-gemini-2-5-pro.png
2025-09-21-google-gemini-live-2-5-flash-preview.png
2025-09-21-google-model-variants.png
2025-09-21-google-pricing.png
2025-09-21-google-summary.png
```

**Note**: These screenshots show model capabilities (supports_caching, supports_thinking) but may not have complete pricing information.

### 2. Required Additional Research

You MUST research Google's official documentation for:

1. **Cached Input Pricing**:
   - Google uses 75% discount on cached input tokens
   - Formula: `cached_input = base_input * 0.25`
   - All models that support caching should have this

2. **Long Context Pricing**:
   - Gemini 2.5 Pro: Changes at 200K tokens threshold
   - Short context (≤200K): $1.25 input / $10.00 output per M tokens
   - Long context (>200K): $2.50 input / $15.00 output per M tokens
   - Research which other models have long context pricing

3. **Thinking Token Pricing**:
   - Gemini 2.5 Flash: $3.50/M for thinking tokens (vs $0.60/M base)
   - Gemini 2.5 Pro: Check if different from base output rate
   - Only 2.5 models with "thinking on by default" feature

4. **Cache Storage Costs**:
   - For explicit caching (not implicit)
   - Charged per million tokens per hour of storage
   - Research current rate from Google documentation

**Web search recommended**:
- "Google Gemini API pricing 2025"
- "Gemini context caching pricing"
- "Gemini thinking tokens pricing"
- "Gemini long context pricing"

### 3. Example Correct Extraction

Based on web research, Gemini 2.5 Pro should look like:

```json
{
  "provider": "google",
  "model_name": "gemini-2.5-pro",
  "display_name": "Gemini 2.5 Pro",
  "dollars_per_million_tokens_input": 1.25,
  "dollars_per_million_tokens_input_long_context": 2.50,
  "dollars_per_million_tokens_cached_input": 0.3125,  // 75% off base (1.25 * 0.25)
  "dollars_per_million_tokens_output": 10.0,
  "dollars_per_million_tokens_output_long_context": 15.0,
  "dollars_per_million_tokens_output_thinking": null,  // Research if different
  "cache_storage_cost_per_million_tokens_per_hour": 0.01,  // Research actual value
  "long_context_threshold_tokens": 200000,
  "supports_caching": true,
  "supports_thinking": true,
  "supports_long_context_pricing": true,
  // ... other fields
}
```

## Validation Reference

### Current (Incorrect) State

From `drafts/google.2025-10-05.draft.json`:

```json
{
  "model_name": "gemini-2.5-pro",
  "dollars_per_million_tokens_input": 2.1,  // ❌ Wrong
  "dollars_per_million_tokens_cached_input": null,  // ❌ Missing
  "dollars_per_million_tokens_input_long_context": null,  // ❌ Missing
  "dollars_per_million_tokens_output": 6.3,  // ❌ Wrong
  "dollars_per_million_tokens_output_long_context": null,  // ❌ Missing
  "dollars_per_million_tokens_output_thinking": null,  // ❌ Missing
  "cache_storage_cost_per_million_tokens_per_hour": null,  // ❌ Missing
  "long_context_threshold_tokens": null,  // ❌ Missing
  "supports_caching": true,  // ❌ Flag true but no pricing
  "supports_thinking": true,  // ❌ Flag true but no pricing
}
```

### Reference: Working Examples

**OpenAI (see `drafts/openai.2025-10-05.draft.json`):**
```json
{
  "model_name": "gpt-4o-mini",
  "dollars_per_million_tokens_input": 0.15,
  "dollars_per_million_tokens_cached_input": 0.075,  // ✅ 50% discount
  "dollars_per_million_tokens_output": 0.6,
  "supports_caching": true
}
```

**Anthropic (see `drafts/anthropic.2025-10-05.draft.json`):**
```json
{
  "model_name": "claude-sonnet-4-20250514",
  "dollars_per_million_tokens_input": 3.0,
  "dollars_per_million_tokens_cache_write_5m": 3.75,  // ✅ 25% premium
  "dollars_per_million_tokens_cache_write_1h": 6.0,   // ✅ 100% premium
  "dollars_per_million_tokens_cache_read": 0.3,       // ✅ 90% discount
  "dollars_per_million_tokens_output": 15.0,
  "supports_caching": true
}
```

## Step-by-Step Instructions

### Step 1: Research Google Pricing

1. **Search for official Google AI pricing documentation**
   - Look for "Google Gemini API pricing" + current date
   - Find official pricing page (ai.google.dev or cloud.google.com)

2. **Extract ALL pricing dimensions for each model**:
   - Base input/output rates
   - Cached input rates (or discount %)
   - Long context rates (if applicable)
   - Long context threshold (token count where pricing changes)
   - Thinking token rates (for 2.5 models)
   - Cache storage rates (per M tokens per hour)

3. **Document your sources**:
   - Save URLs in `sources/google/README.md`
   - Take screenshots if needed
   - Note extraction date

### Step 2: Fix Base Pricing

1. **Verify base pricing for each model** against official docs

2. **Update `drafts/google.2025-10-05.draft.json`**:
   - Correct `dollars_per_million_tokens_input`
   - Correct `dollars_per_million_tokens_output`

3. **Models to fix** (at minimum):
   - All Gemini 2.5 models (Pro, Flash, Flash-Lite)
   - All Gemini 2.0 models
   - All Gemini 1.5 models

### Step 3: Add Cached Pricing

1. **For each model that supports caching**:
   - Calculate: `cached_input = base_input * 0.25` (75% discount)
   - Add to `dollars_per_million_tokens_cached_input`

2. **Verify in source screenshots**:
   - Check `2025-09-21-google-gemini-*.png` files
   - Look for "Caching: Supported" in capabilities section

3. **If model doesn't support caching**:
   - Set `dollars_per_million_tokens_cached_input: null`

### Step 4: Add Long Context Pricing

1. **For Gemini 2.5 Pro**:
   - Research official long context pricing
   - Expected: 2x premium for >200K tokens
   - Add `dollars_per_million_tokens_input_long_context`
   - Add `dollars_per_million_tokens_output_long_context`
   - Add `long_context_threshold_tokens: 200000`

2. **For other models**:
   - Research if they have long context pricing tiers
   - If yes, add the fields
   - If no, set to `null`

### Step 5: Add Thinking Token Pricing

1. **For Gemini 2.5 models**:
   - Check if thinking tokens are priced differently
   - Known: Gemini 2.5 Flash has $3.50/M for thinking (vs $0.60/M base)
   - Add `dollars_per_million_tokens_output_thinking` if different
   - If same as base, set to `null`

2. **Reference web searches**:
   - "Gemini 2.5 Flash thinking tokens pricing"
   - "Gemini 2.5 Pro thinking budget cost"

### Step 6: Add Cache Storage Costs

1. **Research explicit caching storage costs**:
   - Different from cached token read costs
   - Charged per M tokens per hour of storage
   - Add `cache_storage_cost_per_million_tokens_per_hour`

2. **All models with caching should have this**

### Step 7: Validate Your Extraction

Run this validation script from `/Users/juanre/prj/llmring-all/registry`:

```bash
python3 << 'EOF'
import json

with open('drafts/google.2025-10-05.draft.json') as f:
    data = json.load(f)

print("Google Extraction Validation:")
print("=" * 80)

# Check gemini-2.5-pro as reference
for model_key in ["google:gemini-2.5-pro", "google:gemini-2-5-pro"]:
    if model_key in data["models"]:
        model = data["models"][model_key]

        print(f"\n{model['model_name']}:")

        # Required fields
        required = {
            "base_input": model.get("dollars_per_million_tokens_input"),
            "cached_input": model.get("dollars_per_million_tokens_cached_input"),
            "long_input": model.get("dollars_per_million_tokens_input_long_context"),
            "base_output": model.get("dollars_per_million_tokens_output"),
            "long_output": model.get("dollars_per_million_tokens_output_long_context"),
            "thinking_output": model.get("dollars_per_million_tokens_output_thinking"),
            "cache_storage": model.get("cache_storage_cost_per_million_tokens_per_hour"),
            "threshold": model.get("long_context_threshold_tokens"),
        }

        for field, value in required.items():
            status = "✅" if value is not None else "❌ MISSING"
            print(f"  {field}: {value} {status}")

        # Validate calculations
        if required["base_input"] and required["cached_input"]:
            expected = required["base_input"] * 0.25
            actual = required["cached_input"]
            if abs(actual - expected) < 0.01:
                print(f"  ✅ Cached discount correct (75% off)")
            else:
                print(f"  ❌ Cached discount wrong: expected ${expected}, got ${actual}")

        if required["long_input"] and required["base_input"]:
            ratio = required["long_input"] / required["base_input"]
            if abs(ratio - 2.0) < 0.1:
                print(f"  ✅ Long context premium correct (2x)")
            else:
                print(f"  ⚠️  Long context premium: {ratio}x (expected ~2x)")

        break

# Count completeness
models_with_cached = 0
models_with_long_context = 0
models_with_thinking = 0
total = len(data["models"])

for model in data["models"].values():
    if model.get("dollars_per_million_tokens_cached_input"):
        models_with_cached += 1
    if model.get("dollars_per_million_tokens_input_long_context"):
        models_with_long_context += 1
    if model.get("dollars_per_million_tokens_output_thinking"):
        models_with_thinking += 1

print(f"\n" + "=" * 80)
print(f"Total models: {total}")
print(f"Models with cached pricing: {models_with_cached}/{total}")
print(f"Models with long context pricing: {models_with_long_context}/{total}")
print(f"Models with thinking pricing: {models_with_thinking}/{total}")

if models_with_cached < total * 0.8:
    print("\n❌ FAIL: Too few models with cached pricing")
else:
    print("\n✅ PASS: Most models have cached pricing")
EOF
```

### Step 8: Update Validation Report

After fixing, run:

```bash
cd /Users/juanre/prj/llmring-all/registry
python3 -c "
import json

with open('drafts/google.2025-10-05.draft.json') as f:
    data = json.load(f)

print('Google extraction ready for validation')
print(f'Total models: {len(data[\"models\"])}')
"
```

Then ask the validator to re-run the full validation.

## Required Output

1. **Updated draft file**: `drafts/google.2025-10-05.draft.json` with ALL pricing fields
2. **Source documentation**: URLs and screenshots saved in `sources/google/`
3. **Validation output**: Run the validation script and include output

## Success Criteria

Your extraction is complete when:

- ✅ All base pricing is correct (verified against official Google docs)
- ✅ Cached input pricing present for all models with caching support (75% discount)
- ✅ Long context pricing present for applicable models (2x premium)
- ✅ Long context thresholds defined (e.g., 200K tokens)
- ✅ Thinking token pricing researched and added if different from base
- ✅ Cache storage costs added
- ✅ Capability flags accurate (only True when pricing data exists)
- ✅ Validation script shows all checks passing

## Reference Documents

1. **Requirements**: `/Users/juanre/prj/llmring-all/llmring-api/REGISTRY_REQUIREMENTS_CACHED_TOKENS.md`
   - Complete specification of what's needed
   - Examples from OpenAI and Anthropic
   - Pricing formulas and calculations

2. **Validation Report**: `/Users/juanre/prj/llmring-all/registry/VALIDATION_REPORT.md`
   - Shows what's wrong with current extraction
   - Has expected values for key models
   - Validation rules to follow

3. **Schema Utils**: `/Users/juanre/prj/llmring-all/registry/src/registry/schema_utils.py`
   - Shows how capability flags are auto-derived (lines 167-186)
   - Field definitions (lines 129-150)
   - Validation rules

4. **Working Examples**:
   - OpenAI: `drafts/openai.2025-10-05.draft.json`
   - Anthropic: `drafts/anthropic.2025-10-05.draft.json`

## Common Pitfalls to Avoid

1. ❌ **Don't** set capability flags to True without pricing data
   - Schema auto-derives flags from pricing fields
   - Only add pricing if you have verified data

2. ❌ **Don't** guess pricing values
   - Must be verified from official Google documentation
   - Include source URLs in your work

3. ❌ **Don't** use cached pricing from other providers
   - Google uses 75% discount (25% of base)
   - OpenAI varies (50-90% discount)
   - Anthropic has 90% discount for reads

4. ❌ **Don't** skip long context pricing
   - Critical for accurate cost calculations
   - 2x premium is significant for >200K token requests

5. ❌ **Don't** ignore thinking tokens
   - 5.8x difference in pricing is huge
   - Must distinguish for Gemini 2.5 models

## Questions?

If you're unsure about any pricing:

1. Search official Google AI documentation first
2. Check Google Cloud pricing pages
3. Look for 2025 pricing (not outdated 2024)
4. Document your source with URL and date
5. If truly unavailable, note it explicitly with `null` and explain why

---

**START HERE**: Begin by researching Google's official pricing documentation, then update the draft file systematically field by field.
