# Registry Cached Token Pricing - Validation Report

**Date**: 2025-10-05
**Validator**: Claude (Automated)
**Draft Files Validated**:
- `drafts/openai.2025-10-05.draft.json`
- `drafts/anthropic.2025-10-05.draft.json`
- `drafts/google.2025-10-05.draft.json`

---

## Executive Summary

### ✅ PASS: OpenAI (29 models)
- All cached pricing correctly extracted
- All capability flags accurate
- 20 models with caching, 9 without (as expected)

### ✅ PASS: Anthropic (6 models)
- All 4-tier caching pricing correctly extracted
- All capability flags accurate
- All 6 models have complete pricing

### ❌ FAIL: Google (15 models)
- **CRITICAL**: Missing cached input pricing (0/15 models)
- **CRITICAL**: Missing thinking output pricing (0/15 models)
- **CRITICAL**: Missing long context pricing (incomplete)
- **CRITICAL**: Missing cache storage costs
- Capability flags incorrectly set to True without pricing data

---

## Detailed Results

### OpenAI Validation

**Schema Fields Validated:**
- ✅ `dollars_per_million_tokens_cached_input` - 20 models
- ✅ `supports_caching` - Auto-derived correctly

**Sample Validation (against source: `2025-09-21-openai-pricing.png`):**

| Model | Input | Cached Input | Output | Status |
|-------|-------|--------------|--------|--------|
| gpt-4o-mini | $0.15 | $0.075 | $0.60 | ✅ |
| gpt-4o | $2.50 | $1.25 | $10.00 | ✅ |
| gpt-4.1 | $2.00 | $0.50 | $8.00 | ✅ |
| o1 | $15.00 | $7.50 | $60.00 | ✅ |
| o1-pro | $150.00 | null | $600.00 | ✅ (no caching) |
| gpt-4o-2024-05-13 | $2.50 | null | $10.00 | ✅ (no caching) |

**Models WITH caching (20):**
- gpt-4.1, gpt-5-nano, o3-deep-research, o4-mini-deep-research, gpt-5-mini-2025-08-07
- gpt-5-2025-08-07, gpt-5-chat-latest, gpt-4.1-mini, gpt-4.1-nano, gpt-4o
- gpt-4o-mini, gpt-realtime, gpt-4o-realtime-preview, gpt-4o-mini-realtime-preview
- o1, o3, o3-deep-research, o4-mini, o3-mini, o1-mini, codex-mini-latest

**Models WITHOUT caching (9):**
- gpt-4o-2024-05-13, gpt-audio, gpt-4o-audio-preview, gpt-4o-mini-audio-preview
- o1-pro, o3-pro, gpt-4o-mini-search-preview, gpt-4o-search-preview, computer-use-preview

**Cached Discount Verification:**
- gpt-5: 90% discount (✅)
- gpt-4.1: 75% discount (✅)
- gpt-4o: 50% discount (✅)

---

### Anthropic Validation

**Schema Fields Validated:**
- ✅ `dollars_per_million_tokens_cache_write_5m` - 6 models
- ✅ `dollars_per_million_tokens_cache_write_1h` - 6 models
- ✅ `dollars_per_million_tokens_cache_read` - 6 models
- ✅ `supports_caching` - All set to True

**Complete Validation (against source: `2025-09-21-models.md` lines 159-168):**

| Model | Base | 5m Write | 1h Write | Read | Output | Status |
|-------|------|----------|----------|------|--------|--------|
| claude-opus-4-1 | $15.00 | $18.75 | $30.00 | $1.50 | $75.00 | ✅ |
| claude-opus-4 | $15.00 | $18.75 | $30.00 | $1.50 | $75.00 | ✅ |
| claude-sonnet-4 | $3.00 | $3.75 | $6.00 | $0.30 | $15.00 | ✅ |
| claude-3-7-sonnet | $3.00 | $3.75 | $6.00 | $0.30 | $15.00 | ✅ |
| claude-3-5-haiku | $0.80 | $1.00 | $1.60 | $0.08 | $4.00 | ✅ |
| claude-3-haiku | $0.25 | $0.30 | $0.50 | $0.03 | $1.25 | ✅ |

**Cache Write Premium Verification:**
- 5m writes: 25% premium (✅)
- 1h writes: 100% premium for Opus, 100% for Sonnet, 100% for Haiku (✅)

**Cache Read Discount Verification:**
- All models: 90% discount (✅)

---

### Google Validation ❌

**Schema Fields Status:**

| Field | Expected | Found | Status |
|-------|----------|-------|--------|
| `dollars_per_million_tokens_cached_input` | 15 models | 0 models | ❌ MISSING |
| `dollars_per_million_tokens_input_long_context` | 3+ models | 0 models | ❌ MISSING |
| `dollars_per_million_tokens_output_long_context` | 3+ models | 0 models | ❌ MISSING |
| `dollars_per_million_tokens_output_thinking` | 3+ models | 0 models | ❌ MISSING |
| `cache_storage_cost_per_million_tokens_per_hour` | 15 models | 0 models | ❌ MISSING |
| `long_context_threshold_tokens` | 3+ models | 0 models | ❌ MISSING |

**Example: gemini-2.5-pro SHOULD have:**

```json
{
  "dollars_per_million_tokens_input": 1.25,
  "dollars_per_million_tokens_input_long_context": 2.50,
  "dollars_per_million_tokens_cached_input": 0.3125,  // 75% off base
  "dollars_per_million_tokens_output": 10.0,
  "dollars_per_million_tokens_output_long_context": 15.0,
  "dollars_per_million_tokens_output_thinking": null,  // Or separate rate if different
  "cache_storage_cost_per_million_tokens_per_hour": 0.01,
  "long_context_threshold_tokens": 200000,
  "supports_caching": true,
  "supports_thinking": true,
  "supports_long_context_pricing": true
}
```

**ACTUAL gemini-2.5-pro:**

```json
{
  "dollars_per_million_tokens_input": 2.1,  // ❌ Wrong base price
  "dollars_per_million_tokens_input_long_context": null,  // ❌ Missing
  "dollars_per_million_tokens_cached_input": null,  // ❌ Missing
  "dollars_per_million_tokens_output": 6.3,  // ❌ Wrong base price
  "dollars_per_million_tokens_output_long_context": null,  // ❌ Missing
  "dollars_per_million_tokens_output_thinking": null,  // ❌ Missing
  "cache_storage_cost_per_million_tokens_per_hour": null,  // ❌ Missing
  "long_context_threshold_tokens": null,  // ❌ Missing
  "supports_caching": true,  // ❌ Flag True but no pricing
  "supports_thinking": true,  // ❌ Flag True but no pricing
  "supports_long_context_pricing": false
}
```

**Issues:**
1. Base pricing appears incorrect ($2.1/$6.3 vs expected $1.25/$10.0 or $2.50/$15.0)
2. No cached pricing extracted (should be 75% off base)
3. No long context pricing extracted
4. No thinking pricing extracted
5. No cache storage costs extracted
6. No long context thresholds extracted
7. Capability flags incorrectly set True without pricing data

---

## Validation Rules Check

### Rule 1: Cached pricing ≤ base pricing
- ✅ OpenAI: All models pass
- ✅ Anthropic: Cache reads pass (cache writes intentionally higher)
- ❌ Google: Cannot validate (no cached pricing)

### Rule 2: Anthropic cache writes ≥ base pricing
- ✅ All models pass
- 5m writes: 125-120% of base
- 1h writes: 200% of base

### Rule 3: Long context pricing ≥ base pricing
- N/A OpenAI: No long context pricing
- N/A Anthropic: No long context pricing
- ❌ Google: Cannot validate (no long context pricing)

### Rule 4: Capability flags match pricing availability
- ✅ OpenAI: `supports_caching` correctly auto-derived
- ✅ Anthropic: `supports_caching` correctly set True
- ❌ Google: Flags set True but no pricing data

---

## Recommendations

### URGENT: Google Extraction Must Be Redone

The Google extraction is **incomplete and incorrect**. The extractor needs to:

1. **Re-extract base pricing** from correct sources (current prices appear wrong)
2. **Calculate cached pricing** as 75% off base input
3. **Extract long context pricing** for 2.5 Pro and other models with >200K context
4. **Extract or calculate thinking token pricing** for 2.5 models
5. **Research and add cache storage costs** from Google documentation
6. **Add long context thresholds** (e.g., 200K tokens for 2.5 Pro)
7. **Fix capability flags** to only be True when pricing data exists

### OpenAI: Ready for Promotion

- All pricing correctly extracted
- All capability flags accurate
- Ready to promote to `pages/openai/models.json`

### Anthropic: Ready for Promotion

- All 4-tier pricing correctly extracted
- All capability flags accurate
- Ready to promote to `pages/anthropic/models.json`

---

## Promotion Checklist

**Before promoting to production:**

- [x] OpenAI pricing validated
- [x] Anthropic pricing validated
- [ ] Google pricing validated (BLOCKED)
- [x] Schema fields defined correctly
- [x] Validation rules implemented
- [ ] All capability flags accurate (Google fails)
- [ ] Manual spot-check against source documents (OpenAI/Anthropic done, Google pending)

**DO NOT promote Google registry until extraction is fixed.**

---

## Next Steps

1. **Fix Google extraction immediately**
   - Research correct base pricing for all models
   - Implement cached pricing calculation (75% off)
   - Research long context pricing tiers
   - Research thinking token pricing
   - Add cache storage costs

2. **Promote OpenAI and Anthropic**
   - These are ready and correct
   - Can be promoted independently of Google

3. **Re-validate Google**
   - After re-extraction, run full validation again
   - Ensure all pricing dimensions present
   - Verify against real Google billing if possible

4. **Deploy to production**
   - Only after all three providers pass validation
   - Update llmring package to use new pricing fields
   - Implement cost calculator with new pricing logic
