# Anthropic structured output with LLMRing: issue and fix

## Summary

When using LLMRing with Anthropic to extract structured data from PDFs, we hit an Anthropic API error:

Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': "tools.0.custom.input_schema.type: Input should be 'object'"}}

Root cause: Anthropic’s Messages API requires tool input_schema to be an object. Our request used a top‑level array JSON Schema via LLMRing’s json_schema adapter, which Anthropic rejects.

We fixed this by wrapping the array under an object property and adjusting parsing accordingly.

## What happened

- We send a PDF as document content (base64) and request structured output via:
  - LLMRequest.response_format = { type: "json_schema", json_schema: { schema: <JSON Schema> }, strict: true }
- For Anthropic and Google, LLMRing adapts this into a tool call (Anthropic) or function (Google) using the provided JSON Schema.
- Anthropic requires input_schema.type == "object" for tools. If we pass a top‑level array schema, the SDK returns 400.

## The error

- Anthropic SDK returned 400 with message:
  - tools.0.custom.input_schema.type: Input should be 'object'
- LLMRing rethrew as ProviderResponseError with the same payload.

## Fix applied in this repo

File: src/registry/extraction/pdf_parser.py

- Previous (problematic): top‑level array schema
  - Response expected: [...]
- New (correct): wrap array under an object property
  - Tool input schema:
    - { type: "object", properties: { models: { type: "array", items: <model_schema> } }, required: ["models"] }
  - Response expected: { "models": [ ... ] }
- Request always uses provider‑prefixed model anthropic:claude-opus-4-1-20250805.
- Parsing logic first reads response.parsed (structured output provided by LLMRing adapter). If missing, it falls back to parsing response.content, then extracts the models array.
- Removed broad try/except that hid real errors; timeouts and JSON issues now raise with clear messages and file paths.

### Code-level changes

- Configure LLMRequest.response_format as strict JSON Schema with an object schema:
  - response_format = { type: "json_schema", json_schema: { schema: tool_input_schema }, strict: true }
- Expect and extract { models: [...] } from response.parsed.
- Avoid calling deprecated/sync LLMRing getters in PDF flow; keep everything async via service.chat(...).

## Why this isn’t (strictly) an LLMRing bug

- LLMRing’s json_schema adapter expects callers to pass an object schema for tool/function inputs. Anthropic mandates input_schema.type == "object".
- Passing a top‑level array schema is invalid for Anthropic tools. LLMRing could improve DX by:
  - Detecting non‑object schemas for Anthropic and wrapping them automatically under a default property (e.g., data).
  - Or raising a clear error: “Anthropic tool input_schema must be an object; wrap your schema under an object property.”

## Operational notes

- Use an explicit provider‑prefixed model: anthropic:claude-opus-4-1-20250805.
- Ensure ANTHROPIC_API_KEY is set and your account has access to Opus 4.1.
- LLMRing validates models against the registry. If the local/served anthropic/models.json does not include claude-opus-4-1-20250805, you may see ModelNotFoundError. Point LLMRing to the correct registry or add the model entry.

## How to reproduce (before fix)

1) Request structured output with a top‑level array JSON Schema on Anthropic via LLMRing.
2) Anthropic SDK returns 400: tools.0.custom.input_schema.type: Input should be 'object'.

## How to verify (after fix)

1) Run: uv run llmring-registry fetch --provider anthropic --timeout 90 --no-cleanup
2) Confirm no “input_schema.type” errors. If the model is not in the registry, you may see ModelNotFoundError instead; that is a registry issue, not schema.
3) Inspect parsed output or errors:
   - Success: structured models are extracted from PDFs.
   - Failure: clear timeout or JSON error showing the file path and cause.

## Future work (optional upstream improvements)

- In LLMRing’s Anthropic adapter, detect non‑object schemas and either:
  - auto‑wrap: { type: "object", properties: { data: <original_schema> }, required: ["data"] }, or
  - raise a helpful error before calling the SDK.
