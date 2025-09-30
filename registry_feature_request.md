# Feature Request: Enhanced Model Capabilities in Registry

## Summary
Add comprehensive model capability flags to the registry to properly handle provider-specific constraints and features.

## Problem
Currently, providers need to hard-code knowledge about which models support which features. For example:
- OpenAI's o1 and gpt-5 models don't support temperature parameter (only accept default value of 1.0)
- Some models don't support streaming
- Some models don't support function calling/tools
- Some models have specific routing requirements (e.g., Responses API vs Chat Completions API)

This leads to brittle code with hard-coded model name patterns like:
```python
if model.startswith("o1") or model.startswith("gpt-5"):
    # Don't use temperature
```

## Proposed Solution

### 1. Add Capability Flags to Registry

Update the registry model schema to include:

```json
{
  "model_name": "gpt-5-2025-08-07",
  "model_aliases": ["gpt-5", "GPT-5"],
  "display_name": "GPT-5",

  // Existing capabilities
  "supports_vision": false,
  "supports_function_calling": false,
  "supports_json_mode": false,
  "supports_parallel_tool_calls": false,

  // New capability flags needed
  "supports_temperature": false,  // Can only use default temperature
  "supports_streaming": false,     // Whether streaming is supported
  "supports_system_message": true, // Some models don't support system role
  "supports_pdf_input": false,     // Whether PDFs can be processed directly

  // Routing hints
  "api_endpoint": "responses",      // "chat", "responses", "assistants"
  "requires_flat_input": true,     // Needs conversation flattened to single string

  // Parameter constraints
  "temperature_values": [1.0],      // Allowed temperature values (null = all)
  "max_temperature": null,          // Max temperature if supported
  "min_temperature": null,          // Min temperature if supported

  // Other constraints
  "max_tools": 0,                   // Maximum number of tools (0 = none)
  "supports_tool_choice": false,    // Whether tool_choice parameter works
}
```

### 2. Registry API Changes

The registry should:
1. Maintain these capability flags for each model
2. Update them as providers change their APIs
3. Provide a versioned registry so lockfiles can pin to specific capability versions

### 3. Provider Implementation

Providers can then use registry data instead of hard-coding:

```python
# Instead of:
if model.startswith("o1") or model.startswith("gpt-5"):
    # Special handling

# Use:
model_info = await self.get_model_from_registry(provider, model_name)
if not model_info.supports_temperature:
    # Don't pass temperature parameter
if model_info.api_endpoint == "responses":
    # Route to Responses API
if not model_info.supports_streaming:
    # Use non-streaming endpoint
```

## Benefits

1. **Single Source of Truth**: Model capabilities defined once in registry
2. **Maintainable**: Updates to model capabilities happen in registry, not code
3. **Provider Agnostic**: Each provider can have different capabilities per model
4. **Future Proof**: New capabilities can be added without code changes
5. **Better Error Messages**: Can inform users why certain features aren't available

## Implementation Priority

High priority flags (breaking issues):
- `supports_temperature`
- `api_endpoint` / routing hints
- `supports_function_calling`

Medium priority:
- `supports_streaming`
- `supports_system_message`
- `max_tools`

Low priority (nice to have):
- `supports_pdf_input`
- Other constraint fields

## Migration Path

1. Add fields to registry with sensible defaults
2. Update known problematic models (o1, gpt-5)
3. Gradually fill in data for all models
4. Update providers to check registry instead of hard-coding
5. Remove hard-coded model name checks

## Related Issues

- Temperature parameter errors with o1/gpt-5 models
- Tool calling failures with certain models
- Streaming not working with some models
- Need to maintain model-specific workarounds in provider code