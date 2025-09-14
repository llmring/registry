"""PDF parser to extract model information using LLMRing's unified interface.

LLMRing handles all the complexity of different providers:
- Anthropic Claude: Direct PDF support
- OpenAI: Assistants API for PDFs
- Google Gemini: Direct PDF support
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    """Model information extracted from documentation."""

    model_id: str
    display_name: str
    description: str
    use_cases: List[str]
    max_context: int
    max_output_tokens: Optional[int]
    supports_vision: bool
    supports_function_calling: bool
    supports_json_mode: bool
    supports_parallel_tool_calls: bool
    dollars_per_million_tokens_input: float
    dollars_per_million_tokens_output: float
    release_date: Optional[str]
    deprecation_date: Optional[str]
    notes: Optional[str]

    # Additional capabilities
    supports_streaming: bool = True
    supports_audio: bool = False
    supports_documents: bool = False
    context_window_tokens: Optional[int] = None
    supports_json_schema: bool = False
    supports_logprobs: bool = False
    supports_multiple_responses: bool = False
    supports_caching: bool = False
    is_reasoning_model: bool = False

    # Model characteristics & metadata
    speed_tier: Optional[str] = None  # "fast" | "standard" | "slow"
    intelligence_tier: Optional[str] = None  # "basic" | "standard" | "advanced"
    requires_tier: Optional[int] = None
    requires_waitlist: bool = False
    model_family: Optional[str] = None
    recommended_use_cases: Optional[List[str]] = None

    # Status fields
    is_active: bool = True
    added_date: Optional[str] = None


class PDFParser:
    """Parse PDF documents to extract model information using Claude."""

    def __init__(self):
        """Initialize parser with LLMRing."""
        try:
            from llmring import LLMRing

            # Use LLMRing with its default configuration; avoid optional args
            # for compatibility across versions
            self.service = LLMRing()
            self.initialized = True
        except ImportError:
            logger.error("LLMRing not available. Install with: uv add llmring")
            self.service = None
            self.initialized = False
        except Exception as e:
            logger.error(f"Failed to initialize LLMRing: {e}")
            self.service = None
            self.initialized = False

    async def parse_provider_docs_async(
        self, provider: str, pdf_paths: List[Path], timeout_seconds: int | None = 60
    ) -> List[ModelInfo]:
        """
        Parse PDF documents for a provider to extract model information.

        Args:
            provider: Provider name (anthropic, google, openai)
            pdf_paths: List of PDF file paths to analyze

        Returns:
            List of extracted model information
        """
        logger.info(f"Parsing {len(pdf_paths)} PDFs for {provider}")

        if not self.initialized:
            logger.error("LLMRing not initialized")
            return []

        # Use LLMRing's file handling capabilities
        import asyncio

        from llmring.file_utils import analyze_file
        from llmring.schemas import LLMRequest, Message

        all_models = []

        for pdf_path in pdf_paths:
            if not pdf_path.exists():
                logger.warning(f"PDF not found: {pdf_path}")
                continue

            logger.info(f"Processing {pdf_path}")

            # Use LLMRing's analyze_file to create proper content for any provider
            content = analyze_file(
                str(pdf_path), self._create_extraction_prompt_text(provider)
            )

            # Create request using LLMRing with JSON Schema so Anthropic adapter enforces structure
            # IMPORTANT: Anthropic tools require input_schema.type == "object". We wrap our array under an object.
            model_schema = {
                "type": "object",
                "properties": {
                    "model_name": {"type": "string"},
                    "display_name": {"type": "string"},
                    "description": {"type": "string"},
                    "dollars_per_million_tokens_input": {"type": "number"},
                    "dollars_per_million_tokens_output": {"type": "number"},
                    "max_input_tokens": {"type": ["integer", "null"]},
                    "max_output_tokens": {"type": ["integer", "null"]},
                    "supports_vision": {"type": ["boolean", "null"]},
                    "supports_function_calling": {"type": ["boolean", "null"]},
                    "supports_json_mode": {"type": ["boolean", "null"]},
                    "supports_parallel_tool_calls": {"type": ["boolean", "null"]},
                    "supports_streaming": {"type": ["boolean", "null"]},
                    "supports_documents": {"type": ["boolean", "null"]},
                    "is_active": {"type": ["boolean", "null"]}
                },
                "required": [
                    "model_name",
                    "display_name",
                    "dollars_per_million_tokens_input",
                    "dollars_per_million_tokens_output"
                ]
            }

            # Tool input schema must be an object; include an array property 'models'
            tool_input_schema = {
                "type": "object",
                "properties": {
                    "models": {
                        "type": "array",
                        "items": model_schema,
                    }
                },
                "required": ["models"],
            }

            request = LLMRequest(
                messages=[Message(role="user", content=content)],
                model=self._get_best_model(),
                max_tokens=4000,
                temperature=0,
                response_format={
                    "type": "json_schema",
                    "json_schema": {"schema": tool_input_schema},
                    "strict": True,
                },
            )

            # Run async request with timeout
            try:
                response = await asyncio.wait_for(
                    self.service.chat(request), timeout=timeout_seconds
                )
            except asyncio.TimeoutError as e:
                raise TimeoutError(f"Timed out processing {pdf_path}") from e

            # Parse response (prefer structured parsed payload if available)
            parsed_payload = getattr(response, "parsed", None)
            content = response.content.strip()
            # Strip code fences if present
            if content.startswith("```json"):
                content = content[7:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
            elif content.startswith("```"):
                content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()

            if parsed_payload is not None:
                # Expecting {"models": [...]} per tool_input_schema
                if isinstance(parsed_payload, dict) and "models" in parsed_payload:
                    models_data = parsed_payload["models"]
                else:
                    models_data = parsed_payload
            else:
                try:
                    models_data = json.loads(content)
                    if isinstance(models_data, dict) and "models" in models_data:
                        models_data = models_data["models"]
                except json.JSONDecodeError as e:
                    raise ValueError(
                        f"PDF parse returned non-JSON content for {pdf_path}: {content[:500]}"
                    ) from e

            # Add parsed models to results
            if models_data:
                all_models.extend(models_data)

        # Convert to ModelInfo objects mapping JSON keys to dataclass fields
        models: List[ModelInfo] = []
        for model_data in all_models:
            try:
                # Accept both "model_id" and "model_name"
                model_id = model_data.get("model_id") or model_data.get("model_name")
                display_name = model_data.get("display_name") or model_id
                description = model_data.get("description") or ""
                use_cases = model_data.get("use_cases") or model_data.get("recommended_use_cases") or []
                max_context = (
                    model_data.get("max_context")
                    or model_data.get("context_window_tokens")
                    or model_data.get("max_input_tokens")
                    or 0
                )
                max_output_tokens = model_data.get("max_output_tokens")
                supports_vision = bool(model_data.get("supports_vision", False))
                supports_function_calling = bool(model_data.get("supports_function_calling", False))
                supports_json_mode = bool(model_data.get("supports_json_mode", False))
                supports_parallel_tool_calls = bool(model_data.get("supports_parallel_tool_calls", False))
                dollars_in = float(model_data.get("dollars_per_million_tokens_input", 0) or 0)
                dollars_out = float(model_data.get("dollars_per_million_tokens_output", 0) or 0)
                release_date = model_data.get("release_date")
                deprecation_date = model_data.get("deprecated_date") or model_data.get("deprecation_date")
                notes = model_data.get("notes")

                mi = ModelInfo(
                    model_id=model_id,
                    display_name=display_name,
                    description=description,
                    use_cases=use_cases,
                    max_context=max_context,
                    max_output_tokens=max_output_tokens,
                    supports_vision=supports_vision,
                    supports_function_calling=supports_function_calling,
                    supports_json_mode=supports_json_mode,
                    supports_parallel_tool_calls=supports_parallel_tool_calls,
                    dollars_per_million_tokens_input=dollars_in,
                    dollars_per_million_tokens_output=dollars_out,
                    release_date=release_date,
                    deprecation_date=deprecation_date,
                    notes=notes,
                    supports_streaming=bool(model_data.get("supports_streaming", True)),
                    supports_audio=bool(model_data.get("supports_audio", False)),
                    supports_documents=bool(model_data.get("supports_documents", False)),
                    context_window_tokens=model_data.get("context_window_tokens"),
                    supports_json_schema=bool(model_data.get("supports_json_schema", False)),
                    supports_logprobs=bool(model_data.get("supports_logprobs", False)),
                    supports_multiple_responses=bool(model_data.get("supports_multiple_responses", False)),
                    supports_caching=bool(model_data.get("supports_caching", False)),
                    is_reasoning_model=bool(model_data.get("is_reasoning_model", False)),
                    speed_tier=model_data.get("speed_tier"),
                    intelligence_tier=model_data.get("intelligence_tier"),
                    requires_tier=model_data.get("requires_tier"),
                    requires_waitlist=bool(model_data.get("requires_waitlist", False)),
                    model_family=model_data.get("model_family"),
                    recommended_use_cases=model_data.get("recommended_use_cases"),
                    is_active=bool(model_data.get("is_active", True)),
                    added_date=model_data.get("added_date"),
                )
                models.append(mi)
            except Exception:
                # Skip invalid items silently during validation flow
                continue

        return models

    def parse_provider_docs(
        self, provider: str, pdf_paths: List[Path], timeout_seconds: int | None = 60
    ) -> List[ModelInfo]:
        """Synchronous wrapper for environments without an event loop."""
        import asyncio as _asyncio
        return _asyncio.run(
            self.parse_provider_docs_async(provider, pdf_paths, timeout_seconds)
        )

    def _get_best_model(self) -> str:
        """Return configured model for PDF extraction (no async calls)."""
        try:
            from ..config import DEFAULT_EXTRACTION_MODEL
            return DEFAULT_EXTRACTION_MODEL
        except Exception:
            return "anthropic:claude-opus-4-1-20250805"

    def _supports_json_mode(self) -> bool:
        """Check if the selected model supports JSON response format."""
        # Most modern models support JSON mode
        # LLMRing will handle this appropriately per provider
        return True

    def _create_extraction_prompt_text(self, provider: str) -> str:
        """Create extraction prompt text."""
        return f"""Analyze the attached PDF documents from {provider} and extract detailed model information.

Extract information for ALL models mentioned and return as a JSON array. For each model, include:

{{
    "model_id": "exact API model identifier",
    "display_name": "human-friendly name",
    "description": "comprehensive description of the model's capabilities and strengths",
    "use_cases": ["list", "of", "ideal", "use", "cases"],
    "max_context": context_window_tokens,
    "max_output_tokens": max_output_tokens_or_null,
    "supports_vision": boolean,
    "supports_function_calling": boolean,
    "supports_json_mode": boolean,
    "supports_parallel_tool_calls": boolean,
    "dollars_per_million_tokens_input": input_cost,
    "dollars_per_million_tokens_output": output_cost,
    "release_date": "YYYY-MM-DD or null",
    "deprecation_date": "YYYY-MM-DD or null",
    "notes": "any additional important notes or null"
}}

Important:
1. Extract EXACT model IDs as used in API calls
2. Convert all pricing to dollars per million tokens
3. Be comprehensive in descriptions - these help users choose models
4. Include specific use cases where each model excels
5. Note any deprecation dates or warnings

Return ONLY the JSON array, no other text."""
