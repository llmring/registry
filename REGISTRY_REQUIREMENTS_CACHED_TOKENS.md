# Registry Requirements: Cached Token Pricing

## Executive Summary

**CRITICAL ISSUE**: Our cost calculations are currently WRONG for all three major providers (OpenAI, Anthropic, Google) when advanced features (caching, thinking, long context) are used.

**OpenAI**: Overcharging by 50-90% on cached requests (treating $0.075/M as $0.15/M)

**Anthropic**: MASSIVELY incorrect - treating cache writes as base rate (should be MORE expensive) and cache reads as base rate (should be 90% cheaper)

**Google**: Missing multiple pricing dimensions - cached tokens (75% discount), thinking tokens (up to 5.8x premium), long context (2x premium)

**Root Cause**: Registry missing pricing fields for advanced features; cost calculator not tracking request parameters needed for accurate pricing.

**This is a customer-facing service**: We must be 100% accurate. Partial fixes are not acceptable.

**Required Actions**:
1. **Registry Team**: Complete schema redesign to support all pricing dimensions for all providers
2. **LLMRing Team**: Complete cost calculator rewrite to track all request parameters and apply correct pricing

---

## Provider Comparison Summary

| Provider | Caching Model | Thinking Tokens | Long Context | Complexity |
|----------|--------------|-----------------|--------------|------------|
| **OpenAI** | 2-tier: Regular + Cached (50-90% discount) | Reasoning tokens billed as output (same rate) | No separate pricing | **MEDIUM** |
| **Anthropic** | 4-tier: Base + 5m writes + 1h writes + reads | Extended thinking (separate feature) | No separate pricing | **HIGH** |
| **Google** | 2-tier: Regular + Cached (75% discount) + storage | Thinking tokens at 5.8x premium | 2x pricing for >200K tokens | **VERY HIGH** |

### Complexity Breakdown

**OpenAI** (2 dimensions):
- Input token type (regular vs cached)
- All models: 50-90% discount on cached

**Anthropic** (4 dimensions):
- Base input
- 5-minute cache writes (25-100% MORE expensive)
- 1-hour cache writes (100-200% MORE expensive)
- Cache reads (90% discount)

**Google** (7 dimensions):
- Short vs long context input
- Short vs long context output
- Cached input (75% discount)
- Thinking vs non-thinking output (5.8x difference)
- Explicit cache storage costs
- Implicit vs explicit caching modes
- Variable thinking budget settings

---

## Problem Statement

Both OpenAI and Anthropic charge different prices for cached vs non-cached input tokens, but our registry currently only stores regular input/output pricing. This causes **significant cost calculation errors** when users utilize prompt caching.

## Current Registry Schema (Incomplete)

```json
{
  "openai:gpt-4o-mini": {
    "dollars_per_million_tokens_input": 0.15,
    "dollars_per_million_tokens_output": 0.6,
    // Missing: cached input pricing
  }
}
```

## Required Registry Schema Changes

Add a new field for cached input token pricing:

```json
{
  "openai:gpt-4o-mini": {
    "dollars_per_million_tokens_input": 0.15,
    "dollars_per_million_tokens_cached_input": 0.075,  // NEW FIELD
    "dollars_per_million_tokens_output": 0.6,
  }
}
```

### Field Specification

**Field name**: `dollars_per_million_tokens_cached_input`

**Type**: `float | null`

**Description**: Price per million cached input tokens (USD). Cached tokens are portions of the input that have been previously computed and can be reused.

**Nullable**: Yes - some models may not support caching, or pricing may not be available

**Validation**:
- Must be >= 0 if present
- Should be <= `dollars_per_million_tokens_input` (cached is always cheaper or equal)
- Typically 10-50% of regular input pricing (50-90% discount)

## OpenAI Pricing Reference (2025-09-21)

From `/Users/juanre/prj/llmring-all/registry/sources/openai/2025-09-21-openai-pricing.png`:

| Model | Regular Input | Cached Input | Output | Discount |
|-------|--------------|--------------|--------|----------|
| gpt-5 | $1.25 | $0.125 | $10.00 | 90% |
| gpt-5-mini | $0.25 | $0.025 | $2.00 | 90% |
| gpt-5-nano | $0.05 | $0.005 | $0.40 | 90% |
| gpt-4.1 | $2.00 | $0.50 | $8.00 | 75% |
| gpt-4.1-mini | $0.40 | $0.10 | $1.60 | 75% |
| gpt-4.1-nano | $0.10 | $0.025 | $0.40 | 75% |
| gpt-4o | $2.50 | $1.25 | $10.00 | 50% |
| gpt-4o-mini | $0.15 | $0.075 | $0.60 | 50% |
| gpt-realtime | $4.00 | $0.40 | $16.00 | 90% |
| gpt-4o-realtime-preview | $5.00 | $2.50 | $20.00 | 50% |
| gpt-4o-mini-realtime-preview | $0.60 | $0.30 | $2.40 | 50% |
| o1 | $15.00 | $7.50 | $60.00 | 50% |
| o3 | $2.00 | $0.50 | $8.00 | 75% |
| o3-deep-research | $10.00 | $2.50 | $40.00 | 75% |
| o4-mini | $1.10 | $0.275 | $4.40 | 75% |
| o4-mini-deep-research | $2.00 | $0.50 | $8.00 | 75% |
| o3-mini | $1.10 | $0.55 | $4.40 | 50% |
| o1-mini | $1.10 | $0.55 | $4.40 | 50% |
| codex-mini-latest | $1.50 | $0.375 | $6.00 | 75% |
| gpt-image-1 | $5.00 | $1.25 | - | 75% |

**Models WITHOUT cached pricing** (marked with "-" in source):
- gpt-4o-2024-05-13
- gpt-audio
- gpt-4o-audio-preview
- gpt-4o-mini-audio-preview
- o1-pro
- o3-pro
- gpt-4o-mini-search-preview
- gpt-4o-search-preview
- computer-use-preview

For these models, `dollars_per_million_tokens_cached_input` should be `null`.

## How OpenAI Returns Token Counts

OpenAI API returns cached tokens separately in the usage object:

```json
{
  "usage": {
    "prompt_tokens": 1500,
    "completion_tokens": 300,
    "total_tokens": 1800,
    "prompt_tokens_details": {
      "cached_tokens": 1200  // Portion of prompt_tokens that were cached
    }
  }
}
```

**Key points**:
- `prompt_tokens` includes BOTH cached and non-cached tokens
- `cached_tokens` is a subset of `prompt_tokens`
- Non-cached input tokens = `prompt_tokens - cached_tokens`

## Cost Calculation Formula

```python
# Current (INCORRECT - overestimates):
input_cost = (prompt_tokens / 1_000_000) * dollars_per_million_tokens_input

# Required (CORRECT):
cached_tokens = usage.get("prompt_tokens_details", {}).get("cached_tokens", 0)
non_cached_tokens = prompt_tokens - cached_tokens

input_cost = (
    (non_cached_tokens / 1_000_000) * dollars_per_million_tokens_input +
    (cached_tokens / 1_000_000) * dollars_per_million_tokens_cached_input
)
```

## Example Cost Impact

### Scenario: gpt-4o-mini with 10,000 input tokens (8,000 cached)

**Current calculation (wrong)**:
```
input_cost = (10,000 / 1M) * $0.15 = $0.0015
```

**Correct calculation**:
```
non_cached = 2,000 tokens
cached = 8,000 tokens

input_cost = (2,000 / 1M) * $0.15 + (8,000 / 1M) * $0.075
           = $0.0003 + $0.0006
           = $0.0009
```

**Error**: $0.0006 overcharge (67% too high!)

## Registry Extraction Requirements

When extracting pricing from OpenAI sources:

1. **Extract three columns from pricing table**:
   - "INPUT" → `dollars_per_million_tokens_input`
   - "CACHED INPUT" → `dollars_per_million_tokens_cached_input`
   - "OUTPUT" → `dollars_per_million_tokens_output`

2. **Handle missing cached pricing**:
   - If "CACHED INPUT" column shows "-", set to `null`
   - Some older models may not support caching

3. **Validate relationships**:
   - `cached_input <= input` (cached is always cheaper or equal)
   - Typical discounts: 50%, 75%, or 90%

4. **Update schema documentation** in registry README:
   - Add field definition
   - Add validation rules
   - Add examples

## Migration Plan

### Phase 1: Registry Schema Update
- Add `dollars_per_million_tokens_cached_input` field to schema
- Update validation to check cached <= input
- Re-extract all OpenAI models with cached pricing

### Phase 2: Cost Calculator Update (llmring)
- Modify `CostCalculator.calculate_cost()` to use cached pricing
- Add breakdown: `non_cached_input_cost`, `cached_input_cost`, `output_cost`
- Update receipt schema if needed

### Phase 3: Testing
- Add test cases for cached token calculations
- Validate against known OpenAI pricing examples
- Ensure backward compatibility (null cached pricing = use regular input)

## Other Providers

### Anthropic (MORE COMPLEX - URGENT)

Anthropic has a **4-tier caching pricing model** that is MORE complex than OpenAI:

From `/Users/juanre/prj/llmring-all/registry/sources/anthropic/2025-09-21-models.md`:

| Model | Base Input | 5m Cache Writes | 1h Cache Writes | Cache Hits & Refreshes | Output |
|-------|-----------|----------------|----------------|----------------------|---------|
| Opus 4.1 | $15 | $18.75 | $30 | $1.50 | $75 |
| Opus 4 | $15 | $18.75 | $30 | $1.50 | $75 |
| Sonnet 4 | $3 | $3.75 | $6 | $0.30 | $15 |
| Sonnet 3.7 | $3 | $3.75 | $6 | $0.30 | $15 |
| Haiku 3.5 | $0.80 | $1 | $1.6 | $0.08 | $4 |
| Haiku 3 | $0.25 | $0.30 | $0.50 | $0.03 | $1.25 |

**Four input token types:**
1. **Base Input Tokens** - Regular input without caching
2. **5-minute Cache Writes** - Creating cache with 5min TTL (25-100% MORE expensive than base!)
3. **1-hour Cache Writes** - Creating cache with 1h TTL (100-200% MORE expensive!)
4. **Cache Hits & Refreshes** - Reading from cache (90% discount from base)

**API Response Format:**
```json
{
  "usage": {
    "input_tokens": 1000,
    "cache_creation_input_tokens": 500,  // Written to cache (but which TTL?)
    "cache_read_input_tokens": 300,      // Read from cache (90% discount)
    "output_tokens": 200
  }
}
```

**CRITICAL PROBLEM**: The API response does NOT tell us if `cache_creation_input_tokens` was 5min or 1hour cache! This is determined by the `cache_control` parameter in the request, which we need to track separately.

**Required Registry Fields:**
```json
{
  "dollars_per_million_tokens_input": 15.0,           // Base input
  "dollars_per_million_tokens_cache_write_5m": 18.75, // 5min cache writes
  "dollars_per_million_tokens_cache_write_1h": 30.0,  // 1hour cache writes
  "dollars_per_million_tokens_cache_read": 1.50,      // Cache reads/hits
  "dollars_per_million_tokens_output": 75.0
}
```

**Cost Calculation Requirements:**
1. Track `cache_control` parameter from request (user specifies 5m or 1h)
2. Extract `cache_creation_input_tokens` and `cache_read_input_tokens` from response
3. Calculate base input: `input_tokens - cache_creation_tokens - cache_read_tokens`
4. Apply correct cache write pricing based on user's cache_control setting

**Current Status:**
- ✅ Code captures `cache_creation_input_tokens` and `cache_read_input_tokens`
- ❌ Registry shows `"supports_caching": false` for all models (WRONG!)
- ❌ No cache pricing fields in registry
- ❌ Cost calculator doesn't use cache pricing
- ❌ Not tracking which cache TTL was used

**Impact**: Currently **MASSIVELY overcharging** for cache writes (treating $30/M as $15/M) and **overcharging** for cache reads (treating $1.50/M as $15/M).

### Google Gemini (COMPLEX - MULTIPLE DIMENSIONS)

Google has **THREE separate pricing dimensions** that can apply:

#### 1. Context Caching (75% discount)
- Cache reads: 75% discount on input tokens
- Storage costs: Charged based on TTL (time-to-live) duration
- Minimum tokens: 1,024 for Flash models, 2,048-4,096 for Pro models
- Two modes:
  - **Implicit caching** (automatic, no storage charge)
  - **Explicit caching** (user-controlled, has storage charges)

#### 2. Thinking Tokens (Part of output, variable pricing)
- Gemini 2.5 models have "thinking on by default"
- Thinking tokens are **counted as output tokens** and billed accordingly
- Example: Gemini 2.5 Flash:
  - Non-thinking output: $0.60 / MTok
  - Thinking output: $3.50 / MTok (5.8x more expensive!)
- User can configure "thinking budget" to control cost

#### 3. Long Context Pricing (>200K tokens)
- Different pricing for prompts exceeding 200K tokens
- Example Gemini 2.5 Pro:
  - Short context (≤200K): $1.25 input / $10 output per MTok
  - Long context (>200K): $2.50 input / $15 output per MTok

**Current Registry Issues:**
- ❌ All models show `"supports_caching": false` (WRONG!)
- ❌ No cached input pricing (75% discount missing)
- ❌ No thinking token pricing differentiation
- ❌ No long context pricing tiers
- ❌ No storage costs for explicit caching

**Required Registry Fields:**
```json
{
  "dollars_per_million_tokens_input": 1.25,              // Base input (≤200K)
  "dollars_per_million_tokens_input_long": 2.50,         // Long context (>200K)
  "dollars_per_million_tokens_cached_input": 0.3125,     // Cached input (75% off)
  "dollars_per_million_tokens_output": 10.0,             // Base output
  "dollars_per_million_tokens_output_long": 15.0,        // Long context output
  "dollars_per_million_tokens_thinking": 3.50,           // Thinking tokens (if different)
  "cache_storage_cost_per_million_tokens_per_hour": 0.01 // Storage cost for explicit caching
}
```

**API Response Format:**
```json
{
  "usageMetadata": {
    "promptTokenCount": 1000,
    "cachedContentTokenCount": 500,  // Tokens read from cache (75% discount)
    "candidatesTokenCount": 300,     // Total output tokens
    // Note: No separate thinking token count - included in candidatesTokenCount
  }
}
```

**Cost Calculation Challenges:**
1. Need to track context length to apply long-context pricing
2. Need to distinguish thinking vs non-thinking output (user configuration dependent)
3. Need to track cache storage duration for explicit caching
4. Implicit vs explicit caching has different billing models

**Impact**:
- Undercharging cached requests (missing 75% discount)
- Can't distinguish thinking vs non-thinking output costs (up to 5.8x difference!)
- Missing long-context premium (2x more expensive)

## Related: Reasoning Tokens (o1 Models)

OpenAI's o1/o3/o4 reasoning models also return `completion_tokens_details.reasoning_tokens`, but these are charged at the **same rate** as regular output tokens, so no separate pricing needed.

For visibility, we may want to capture this breakdown in usage data, but it doesn't affect cost calculations.

---

## Complete Registry Schema Requirements

### Required Schema Changes

All pricing fields must be **nullable** to support models that don't offer specific features.

#### Base Fields (Already Exist)
```json
{
  "dollars_per_million_tokens_input": float,
  "dollars_per_million_tokens_output": float
}
```

#### New Required Fields

```json
{
  // OpenAI-specific
  "dollars_per_million_tokens_cached_input": float | null,

  // Anthropic-specific
  "dollars_per_million_tokens_cache_write_5m": float | null,
  "dollars_per_million_tokens_cache_write_1h": float | null,
  "dollars_per_million_tokens_cache_read": float | null,

  // Google-specific
  "dollars_per_million_tokens_input_long_context": float | null,
  "dollars_per_million_tokens_output_long_context": float | null,
  "dollars_per_million_tokens_output_thinking": float | null,
  "cache_storage_cost_per_million_tokens_per_hour": float | null,
  "long_context_threshold_tokens": int | null,  // e.g., 200000 for Gemini 2.5 Pro

  // Capability flags (must be accurate!)
  "supports_caching": boolean,
  "supports_thinking": boolean,
  "supports_long_context_pricing": boolean
}
```

### Validation Rules

1. **Cached pricing must be ≤ base pricing**
   - `cached_input <= input` (or null)
   - `cache_read <= input` (or null)

2. **Anthropic cache writes can be > base pricing**
   - `cache_write_5m >= input` (allowed)
   - `cache_write_1h >= cache_write_5m` (allowed)

3. **Long context pricing must be ≥ base pricing**
   - `input_long_context >= input` (or null)
   - `output_long_context >= output` (or null)

4. **Capability flags must match pricing availability**
   - `supports_caching = true` IFF any cache pricing field is non-null
   - `supports_thinking = true` IFF `output_thinking` is non-null
   - `supports_long_context_pricing = true` IFF long context fields are non-null

### Per-Provider Extraction Requirements

#### OpenAI
**Source**: `/Users/juanre/prj/llmring-all/registry/sources/openai/2025-09-21-openai-pricing.png`

**Extract**:
- Column "INPUT" → `dollars_per_million_tokens_input`
- Column "CACHED INPUT" → `dollars_per_million_tokens_cached_input`
  - If shows "-", set to `null`
- Column "OUTPUT" → `dollars_per_million_tokens_output`

**Set flags**:
- `supports_caching = true` if cached pricing exists
- `supports_thinking = false` (OpenAI reasoning tokens billed at same rate as output)
- `supports_long_context_pricing = false`

**Models to extract**: All 26 active models in pricing table

#### Anthropic
**Source**: `/Users/juanre/prj/llmring-all/registry/sources/anthropic/2025-09-21-models.md`

**Extract** (from pricing table lines 159-168):
- Column "Base Input Tokens" → `dollars_per_million_tokens_input`
- Column "5m Cache Writes" → `dollars_per_million_tokens_cache_write_5m`
- Column "1h Cache Writes" → `dollars_per_million_tokens_cache_write_1h`
- Column "Cache Hits & Refreshes" → `dollars_per_million_tokens_cache_read`
- Column "Output Tokens" → `dollars_per_million_tokens_output`

**Set flags**:
- `supports_caching = true` (all models support caching)
- `supports_thinking = true` (extended thinking available)
- `supports_long_context_pricing = false`

**Models to extract**:
- Claude Opus 4.1
- Claude Opus 4
- Claude Sonnet 4
- Claude Sonnet 3.7
- Claude Haiku 3.5
- Claude Haiku 3

**Critical**: Fix existing `"supports_caching": false` to `true` for all models

#### Google
**Source**: Multiple screenshots + web documentation needed

**Extract**:
- Base pricing from model-specific screenshots
- Long context threshold from model documentation (e.g., 200K for 2.5 Pro)
- Thinking token pricing from API documentation
- Cache discount: 75% off base (calculate from base)
- Storage costs from caching documentation

**Example for Gemini 2.5 Pro**:
```json
{
  "dollars_per_million_tokens_input": 1.25,
  "dollars_per_million_tokens_input_long_context": 2.50,
  "dollars_per_million_tokens_cached_input": 0.3125,  // 75% off base
  "dollars_per_million_tokens_output": 10.0,
  "dollars_per_million_tokens_output_long_context": 15.0,
  "dollars_per_million_tokens_output_thinking": 3.50,  // If different from base
  "cache_storage_cost_per_million_tokens_per_hour": 0.01,  // From docs
  "long_context_threshold_tokens": 200000,
  "supports_caching": true,
  "supports_thinking": true,
  "supports_long_context_pricing": true
}
```

**Models to extract**:
- All Gemini 2.5 models (Pro, Flash, Flash-Lite)
- All Gemini 2.0 models
- All Gemini 1.5 models (even if deprecated)

### Schema Migration Plan

1. **Add new fields to schema** with all fields nullable
2. **Update validation logic** with new rules
3. **Re-extract all providers** with new fields
4. **Verify extraction** against source documents manually
5. **Test edge cases**: null values, models without caching, etc.
6. **Deploy new registry** with version bump

---

## Complete Cost Calculator Requirements

### Request Context Tracking

The cost calculator must track additional request parameters to apply correct pricing:

```python
@dataclass
class RequestContext:
    """Context needed for accurate cost calculation."""

    # Anthropic-specific
    cache_control_ttl: Optional[str] = None  # "5m" or "1h"

    # Google-specific
    total_input_tokens: int = 0  # For long-context threshold
    thinking_enabled: bool = False
    thinking_budget_tokens: Optional[int] = None
    cache_mode: Optional[str] = None  # "implicit" or "explicit"
    cache_ttl_hours: Optional[float] = None  # For storage costs
```

### Updated Cost Calculation Logic

#### OpenAI Cost Calculation

```python
def calculate_openai_cost(
    response: LLMResponse,
    registry_model: RegistryModel,
    context: RequestContext
) -> CostBreakdown:
    """Calculate cost for OpenAI with cached token support."""

    # Extract token counts
    prompt_tokens = response.usage.get("prompt_tokens", 0)
    completion_tokens = response.usage.get("completion_tokens", 0)
    cached_tokens = response.usage.get("prompt_tokens_details", {}).get("cached_tokens", 0)

    # Calculate non-cached input tokens
    non_cached_tokens = prompt_tokens - cached_tokens

    # Apply pricing
    if registry_model.dollars_per_million_tokens_cached_input is not None:
        input_cost = (
            (non_cached_tokens / 1_000_000) * registry_model.dollars_per_million_tokens_input +
            (cached_tokens / 1_000_000) * registry_model.dollars_per_million_tokens_cached_input
        )
    else:
        # Model doesn't support caching, use base rate for all
        input_cost = (prompt_tokens / 1_000_000) * registry_model.dollars_per_million_tokens_input

    output_cost = (completion_tokens / 1_000_000) * registry_model.dollars_per_million_tokens_output

    return CostBreakdown(
        input_tokens=non_cached_tokens,
        cached_input_tokens=cached_tokens,
        output_tokens=completion_tokens,
        input_cost=input_cost,
        output_cost=output_cost,
        total_cost=input_cost + output_cost,
        breakdown={
            "non_cached_input": (non_cached_tokens / 1_000_000) * registry_model.dollars_per_million_tokens_input,
            "cached_input": (cached_tokens / 1_000_000) * registry_model.dollars_per_million_tokens_cached_input if cached_tokens > 0 else 0,
            "output": output_cost
        }
    )
```

#### Anthropic Cost Calculation

```python
def calculate_anthropic_cost(
    response: LLMResponse,
    registry_model: RegistryModel,
    context: RequestContext
) -> CostBreakdown:
    """Calculate cost for Anthropic with 4-tier caching."""

    # Extract token counts
    input_tokens = response.usage.get("input_tokens", 0)
    cache_creation_tokens = response.usage.get("cache_creation_input_tokens", 0)
    cache_read_tokens = response.usage.get("cache_read_input_tokens", 0)
    output_tokens = response.usage.get("output_tokens", 0)

    # Calculate base input tokens (not cached)
    base_input_tokens = input_tokens - cache_creation_tokens - cache_read_tokens

    # Determine cache write pricing based on TTL
    if cache_creation_tokens > 0:
        if context.cache_control_ttl == "5m":
            cache_write_rate = registry_model.dollars_per_million_tokens_cache_write_5m
        elif context.cache_control_ttl == "1h":
            cache_write_rate = registry_model.dollars_per_million_tokens_cache_write_1h
        else:
            # Unknown TTL - this is an error condition
            raise ValueError(f"Unknown cache_control_ttl: {context.cache_control_ttl}")
    else:
        cache_write_rate = 0

    # Calculate input costs
    base_input_cost = (base_input_tokens / 1_000_000) * registry_model.dollars_per_million_tokens_input
    cache_write_cost = (cache_creation_tokens / 1_000_000) * cache_write_rate if cache_creation_tokens > 0 else 0
    cache_read_cost = (cache_read_tokens / 1_000_000) * registry_model.dollars_per_million_tokens_cache_read if cache_read_tokens > 0 else 0

    input_cost = base_input_cost + cache_write_cost + cache_read_cost
    output_cost = (output_tokens / 1_000_000) * registry_model.dollars_per_million_tokens_output

    return CostBreakdown(
        input_tokens=base_input_tokens,
        cache_creation_tokens=cache_creation_tokens,
        cache_read_tokens=cache_read_tokens,
        output_tokens=output_tokens,
        input_cost=input_cost,
        output_cost=output_cost,
        total_cost=input_cost + output_cost,
        breakdown={
            "base_input": base_input_cost,
            f"cache_write_{context.cache_control_ttl}": cache_write_cost,
            "cache_read": cache_read_cost,
            "output": output_cost
        }
    )
```

#### Google Cost Calculation

```python
def calculate_google_cost(
    response: LLMResponse,
    registry_model: RegistryModel,
    context: RequestContext
) -> CostBreakdown:
    """Calculate cost for Google with caching, thinking, and long context."""

    # Extract token counts
    prompt_tokens = response.usage.get("promptTokenCount", 0)
    cached_tokens = response.usage.get("cachedContentTokenCount", 0)
    output_tokens = response.usage.get("candidatesTokenCount", 0)

    # Calculate non-cached input
    non_cached_input = prompt_tokens - cached_tokens

    # Determine if long context pricing applies
    use_long_context = (
        registry_model.supports_long_context_pricing and
        context.total_input_tokens >= registry_model.long_context_threshold_tokens
    )

    # Select input pricing
    if use_long_context:
        input_rate = registry_model.dollars_per_million_tokens_input_long_context
    else:
        input_rate = registry_model.dollars_per_million_tokens_input

    # Calculate input costs
    non_cached_cost = (non_cached_input / 1_000_000) * input_rate

    if cached_tokens > 0 and registry_model.dollars_per_million_tokens_cached_input is not None:
        # Note: Cached tokens use base cached rate, not long-context rate
        cached_cost = (cached_tokens / 1_000_000) * registry_model.dollars_per_million_tokens_cached_input
    else:
        cached_cost = 0

    input_cost = non_cached_cost + cached_cost

    # Calculate output costs
    if context.thinking_enabled and registry_model.dollars_per_million_tokens_output_thinking is not None:
        output_rate = registry_model.dollars_per_million_tokens_output_thinking
    elif use_long_context:
        output_rate = registry_model.dollars_per_million_tokens_output_long_context
    else:
        output_rate = registry_model.dollars_per_million_tokens_output

    output_cost = (output_tokens / 1_000_000) * output_rate

    # Calculate storage costs for explicit caching
    storage_cost = 0
    if (context.cache_mode == "explicit" and
        context.cache_ttl_hours and
        cached_tokens > 0 and
        registry_model.cache_storage_cost_per_million_tokens_per_hour):
        storage_cost = (
            (cached_tokens / 1_000_000) *
            registry_model.cache_storage_cost_per_million_tokens_per_hour *
            context.cache_ttl_hours
        )

    total_cost = input_cost + output_cost + storage_cost

    return CostBreakdown(
        input_tokens=non_cached_input,
        cached_input_tokens=cached_tokens,
        output_tokens=output_tokens,
        input_cost=input_cost,
        output_cost=output_cost,
        storage_cost=storage_cost,
        total_cost=total_cost,
        breakdown={
            "non_cached_input": non_cached_cost,
            "cached_input": cached_cost,
            "output": output_cost,
            "storage": storage_cost
        },
        metadata={
            "long_context_applied": use_long_context,
            "thinking_rate_applied": context.thinking_enabled and registry_model.dollars_per_million_tokens_output_thinking is not None,
            "cache_mode": context.cache_mode
        }
    )
```

### Request Context Capture

Each provider adapter must capture request parameters:

```python
# In OpenAIProvider.chat()
context = RequestContext()
# OpenAI doesn't need additional context

# In AnthropicProvider.chat()
context = RequestContext()
# Extract cache_control from messages
for message in messages:
    if hasattr(message, 'cache_control'):
        context.cache_control_ttl = message.cache_control.get('type', 'ephemeral')
        break

# In GoogleProvider.chat()
context = RequestContext(
    total_input_tokens=len(prompt),  # Approximate, will be exact after response
    thinking_enabled=generation_config.get('thinking_enabled', False),
    cache_mode='explicit' if cached_content else 'implicit',
    cache_ttl_hours=cache_config.get('ttl_hours') if cached_content else None
)
```

### Updated CostBreakdown Schema

```python
@dataclass
class CostBreakdown:
    """Complete cost breakdown with all token types."""

    # Token counts
    input_tokens: int = 0
    cached_input_tokens: int = 0
    cache_creation_tokens: int = 0  # Anthropic only
    cache_read_tokens: int = 0      # Anthropic only
    output_tokens: int = 0

    # Costs
    input_cost: float = 0.0
    output_cost: float = 0.0
    storage_cost: float = 0.0  # Google only
    total_cost: float = 0.0

    # Detailed breakdown
    breakdown: Dict[str, float] = field(default_factory=dict)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### Testing Requirements

1. **Unit tests** for each provider with:
   - No caching (baseline)
   - With caching (all variants)
   - Edge cases (zero tokens, all cached, etc.)

2. **Integration tests** with real API calls:
   - Verify token counts match API response
   - Verify costs match provider's billing
   - Test all caching modes

3. **Regression tests**:
   - Ensure non-cached requests still work
   - Ensure models without caching support work

---

## Implementation Checklist

### Registry Team

- [ ] Add 12 new pricing fields to schema
- [ ] Add 3 new capability flags to schema
- [ ] Add validation rules for new fields
- [ ] Extract OpenAI pricing (26 models)
- [ ] Extract Anthropic pricing (6 models)
- [ ] Extract Google pricing (15+ models)
- [ ] Fix `supports_caching: false` → `true` for Anthropic
- [ ] Fix `supports_caching: false` → `true` for Google
- [ ] Manual verification of all extracted pricing
- [ ] Schema version bump
- [ ] Deploy new registry

### LLMRing Team

- [ ] Add `RequestContext` class
- [ ] Update OpenAI provider to capture context
- [ ] Update Anthropic provider to capture `cache_control` TTL
- [ ] Update Google provider to capture all context parameters
- [ ] Implement `calculate_openai_cost()` with caching
- [ ] Implement `calculate_anthropic_cost()` with 4-tier caching
- [ ] Implement `calculate_google_cost()` with all dimensions
- [ ] Update `CostBreakdown` schema
- [ ] Update receipts to include detailed breakdown
- [ ] Add unit tests for all providers (15+ test cases each)
- [ ] Add integration tests with real API calls
- [ ] Add regression tests
- [ ] Update documentation
- [ ] Deploy cost calculator update

### Validation Team

- [ ] Verify OpenAI costs against real billing
- [ ] Verify Anthropic costs against real billing
- [ ] Verify Google costs against real billing
- [ ] Test all edge cases
- [ ] Load testing with various token distributions

---

## Accuracy Requirement

**All cost calculations must be accurate to within ±$0.000001 (1 millionth of a dollar)** when compared to provider billing. Any deviation larger than rounding errors is unacceptable for a customer-facing service.

This requires:
1. Exact pricing data in registry
2. Correct formula implementation
3. Full request context capture
4. Comprehensive testing against real provider billing
