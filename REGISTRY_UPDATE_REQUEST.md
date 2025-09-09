# Registry Update Request

## Overview

This document outlines additional fields needed in the registry to support production use cases and enable better model selection for LLMRing users.

## Current State

The registry currently tracks these fields per model:
- Basic info: `provider`, `model_name`, `display_name`, `description`
- Limits: `max_input_tokens`, `max_output_tokens`
- Pricing: `dollars_per_million_tokens_input`, `dollars_per_million_tokens_output`
- Capabilities: `supports_vision`, `supports_function_calling`, `supports_json_mode`, `supports_parallel_tool_calls`
- Status: `is_active`, `added_date`, `deprecated_date`

## Requested Additional Fields

### 1. Critical Missing Capabilities

These capabilities are essential for users to make informed decisions about model selection:

#### **supports_streaming** (boolean)
- **Why needed**: Streaming is critical for user experience in chat applications
- **Default**: `true` (all major providers support it)
- **Example**: All OpenAI, Anthropic, Google models support streaming

#### **supports_audio** (boolean)
- **Why needed**: Audio input/output is becoming common (GPT-4o, Gemini, etc.)
- **Default**: `false`
- **Models that support it**:
  - OpenAI: `gpt-4o`, `gpt-4o-mini`, `whisper-*`
  - Google: `gemini-1.5-pro`, `gemini-1.5-flash`

#### **supports_documents** (boolean)
- **Why needed**: PDF/document processing is a common use case
- **Default**: `false`
- **Models that support it**:
  - OpenAI: All models via Assistants API or Responses API
  - Anthropic: All Claude 3+ models
  - Google: All Gemini 1.5+ models

#### **context_window_tokens** (integer)
- **Why needed**: Total context size (input + output) for planning conversations
- **Calculation**: Usually `max_input_tokens + max_output_tokens`
- **Example**: GPT-4o has 128K input + 16K output = 144K total

### 2. Advanced Capabilities

These help users leverage provider-specific features:

#### **supports_json_schema** (boolean)
- **Why needed**: Structured output with schema validation (beyond basic JSON mode)
- **Default**: `false`
- **Models that support it**:
  - OpenAI: GPT-4o and newer
  - Google: Gemini models with response_mime_type

#### **supports_logprobs** (boolean)
- **Why needed**: Important for confidence scoring and analysis
- **Default**: `false`
- **Models that support it**:
  - OpenAI: All GPT models
  - Others: Generally not supported

#### **supports_multiple_responses** (boolean)
- **Why needed**: Getting multiple completions in one request (OpenAI's `n` parameter)
- **Default**: `false`
- **Models that support it**:
  - OpenAI: All GPT models
  - Others: Generally not supported

#### **supports_caching** (boolean)
- **Why needed**: Cost optimization through prompt caching
- **Default**: `false`
- **Models that support it**:
  - Anthropic: All Claude models (beta)
  - OpenAI: Via Responses API with `store: true`

### 3. Model Characteristics

These help users choose the right model for their use case:

#### **is_reasoning_model** (boolean)
- **Why needed**: Identifies models optimized for complex reasoning (o1, o3, GPT-5)
- **Default**: `false`
- **Examples**: `o1`, `o1-mini`, `o3`, `o3-mini`, `gpt-5`

#### **speed_tier** (string: "fast" | "standard" | "slow")
- **Why needed**: Help users balance speed vs capability
- **Examples**:
  - "fast": `gpt-4o-mini`, `claude-3-haiku`, `gemini-1.5-flash`
  - "standard": `gpt-4o`, `claude-3-sonnet`, `gemini-1.5-pro`
  - "slow": `o1`, `o3`, `claude-3-opus`

#### **intelligence_tier** (string: "basic" | "standard" | "advanced")
- **Why needed**: Help users choose based on task complexity
- **Examples**:
  - "basic": `gpt-3.5-turbo`, mini/nano variants
  - "standard": `gpt-4`, `claude-3-sonnet`, `gemini-pro`
  - "advanced": `o1`, `gpt-5`, `claude-3-opus`

### 4. Access Requirements

#### **requires_tier** (integer, optional)
- **Why needed**: OpenAI has tier requirements for certain models
- **Default**: `null`
- **Examples**:
  - `o1`: Requires tier 5
  - `gpt-4`: Requires tier 1
  - `gpt-3.5-turbo`: No requirement

#### **requires_waitlist** (boolean)
- **Why needed**: Some models require special access
- **Default**: `false`
- **Examples**: New models often start with waitlist access

### 5. Additional Metadata

#### **release_date** (date string, optional)
- **Why needed**: Track model age and updates
- **Format**: "YYYY-MM-DD"
- **Example**: "2024-11-06" for GPT-4o

#### **model_family** (string)
- **Why needed**: Group related models
- **Examples**: "gpt-4", "claude-3", "gemini-1.5", "o-series"

#### **recommended_use_cases** (array of strings, optional)
- **Why needed**: Guide users to appropriate models
- **Examples**: ["chat", "code", "vision", "reasoning", "translation"]

## Proposed Registry Schema Update

```json
{
  "openai:gpt-4o": {
    // Existing fields
    "model_name": "gpt-4o",
    "display_name": "GPT-4o",
    "description": "Optimized for chat with vision capabilities",
    "max_input_tokens": 128000,
    "max_output_tokens": 16384,
    "dollars_per_million_tokens_input": 5.0,
    "dollars_per_million_tokens_output": 15.0,
    "supports_vision": true,
    "supports_function_calling": true,
    "supports_json_mode": true,
    "supports_parallel_tool_calls": true,
    "is_active": true,
    
    // New critical fields
    "supports_streaming": true,
    "supports_audio": true,
    "supports_documents": true,
    "context_window_tokens": 144384,
    
    // New advanced capabilities
    "supports_json_schema": true,
    "supports_logprobs": true,
    "supports_multiple_responses": true,
    "supports_caching": false,
    
    // New characteristics
    "is_reasoning_model": false,
    "speed_tier": "standard",
    "intelligence_tier": "standard",
    
    // New access requirements
    "requires_tier": null,
    "requires_waitlist": false,
    
    // New metadata
    "release_date": "2024-11-06",
    "model_family": "gpt-4",
    "recommended_use_cases": ["chat", "code", "vision", "function-calling"]
  }
}
```

## Implementation Priority

### Phase 1: Critical Fields (High Priority)
Add these fields immediately as they affect basic functionality:
- `supports_streaming`
- `supports_audio`
- `supports_documents`
- `context_window_tokens`

### Phase 2: Advanced Capabilities (Medium Priority)
Add these to enable advanced features:
- `supports_json_schema`
- `supports_logprobs`
- `supports_multiple_responses`
- `supports_caching`
- `is_reasoning_model`

### Phase 3: Characteristics & Metadata (Low Priority)
Add these for better UX:
- `speed_tier`
- `intelligence_tier`
- `requires_tier`
- `requires_waitlist`
- `release_date`
- `model_family`
- `recommended_use_cases`

## Migration Strategy

1. **Add fields with defaults** - New fields are optional with sensible defaults
2. **Gradual population** - Update models incrementally, starting with popular ones
3. **Provider validation** - Have provider experts review their model capabilities
4. **Automated checks** - Build scripts to validate against provider documentation

## Data Sources for Population

### OpenAI
- Models documentation: https://platform.openai.com/docs/models
- Pricing page: https://openai.com/pricing
- API reference for capabilities

### Anthropic
- Model documentation: https://docs.anthropic.com/en/docs/models
- Pricing: https://anthropic.com/pricing
- API reference for capabilities

### Google
- Model documentation: https://cloud.google.com/vertex-ai/docs/generative-ai/model-reference
- Gemini models: https://ai.google.dev/models/gemini
- Pricing and limits documentation

## Validation Rules

To ensure data quality, these validation rules should be applied:

1. **If `supports_vision=true`**, model should handle image inputs
2. **If `is_reasoning_model=true`**, typically `speed_tier="slow"`
3. **`context_window_tokens`** should approximately equal `max_input_tokens + max_output_tokens`
4. **`supports_streaming`** should be `true` for all modern models (GPT-3.5+, Claude 2+, Gemini 1+)
5. **Price validation**: Newer models shouldn't be drastically cheaper than older ones without reason

## Questions for Registry Maintainers

1. Should we track **rate limits** per model? (e.g., requests per minute)
2. Should we add **regional availability**? (some models are US-only)
3. Should we track **training data cutoff dates**?
4. Should we add **moderation flags** for models with built-in content filtering?
5. Should we version the schema itself for backward compatibility?

## Benefits of These Additions

1. **Better Model Selection**: Users can programmatically find models that meet their requirements
2. **Accurate Cost Estimation**: With all capabilities visible, cost planning improves
3. **Reduced Errors**: Users won't try to use features that aren't supported
4. **Improved Documentation**: The registry becomes the single source of truth
5. **Future-Proofing**: New capabilities can be added as fields as providers innovate

## Example Usage with Enhanced Registry

```python
# Find a fast model with vision support
models = registry.filter(
    supports_vision=True,
    speed_tier="fast"
)
# Returns: gpt-4o-mini, claude-3-haiku, gemini-1.5-flash

# Find models for complex reasoning
models = registry.filter(
    is_reasoning_model=True,
    is_active=True
)
# Returns: o1, o3, gpt-5

# Check if a model can handle a specific workflow
model = registry.get("gpt-4o")
if model.supports_documents and model.supports_json_schema:
    # Can process PDFs and return structured data
    process_invoice_with_schema(model)
```

## Next Steps

1. **Review and approve** the proposed fields
2. **Create a migration script** to add fields with defaults
3. **Update the most popular models** first (GPT-4o, Claude 3.5, Gemini 1.5)
4. **Document the new schema** in the registry README
5. **Build validation tooling** to ensure data quality

---

*This document prepared for the LLMRing Registry maintainers to enhance model capability tracking and improve user experience.*