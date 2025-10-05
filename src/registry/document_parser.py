"""Document parser to extract model information using LLMRing's unified interface.

Supports multiple document types:
- Screenshots (.png) - processed as images
- PDFs (.pdf) - processed as documents
- Markdown (.md) - processed as text content
"""

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from copy import deepcopy
from typing import Any, Dict, List, Optional
import asyncio

import click
from llmring import LLMRing
from llmring.file_utils import create_file_content
from llmring.schemas import LLMRequest, Message
from PIL import Image

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    """Model information extracted from documentation."""

    model_id: str
    display_name: str
    description: str
    use_cases: List[str]
    max_input_tokens: int
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
    dollars_per_million_tokens_cached_input: Optional[float] = None
    dollars_per_million_tokens_cache_write_5m: Optional[float] = None
    dollars_per_million_tokens_cache_write_1h: Optional[float] = None
    dollars_per_million_tokens_cache_read: Optional[float] = None
    dollars_per_million_tokens_input_long_context: Optional[float] = None
    dollars_per_million_tokens_output_long_context: Optional[float] = None
    dollars_per_million_tokens_output_thinking: Optional[float] = None
    cache_storage_cost_per_million_tokens_per_hour: Optional[float] = None
    long_context_threshold_tokens: Optional[int] = None

    # Model name synonyms (e.g., ["gpt-5"] for "gpt-5-2025-08-07")
    model_aliases: Optional[List[str]] = None

    # Additional capabilities
    supports_streaming: bool = True
    supports_audio: bool = False
    supports_documents: bool = False
    supports_json_schema: bool = False
    supports_logprobs: bool = False
    supports_multiple_responses: bool = False
    supports_caching: bool = False
    supports_thinking: bool = False
    supports_long_context_pricing: bool = False
    is_reasoning_model: bool = False

    # New capability flags for enhanced model constraints
    supports_temperature: bool = True  # False = can only use default temperature (e.g., o1, gpt-5)
    supports_system_message: bool = True  # Some models don't support system role
    supports_pdf_input: bool = False  # Whether PDFs can be processed directly

    # Routing and API endpoint hints
    api_endpoint: Optional[str] = None  # "chat", "responses", "assistants"
    requires_flat_input: bool = False  # Needs conversation flattened to single string

    # Parameter constraints
    temperature_values: Optional[List[float]] = None  # Allowed temperature values (None = all)
    max_temperature: Optional[float] = None  # Max temperature if supported
    min_temperature: Optional[float] = None  # Min temperature if supported

    # Tool constraints
    max_tools: Optional[int] = None  # Maximum number of tools (0 = none, None = unlimited)
    supports_tool_choice: bool = True  # Whether tool_choice parameter works
    tool_call_format: Optional[str] = None  # Format for tool calls if non-standard

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


def _resize_image_if_needed(image_path: Path, max_dimension: int = 7500) -> Path:
    """
    Resize image if it exceeds max dimensions.

    Args:
        image_path: Path to the image file
        max_dimension: Maximum width or height (default 7500 to stay under 8000 limit)

    Returns:
        Path to the resized image (or original if no resize needed)
    """
    try:
        with Image.open(image_path) as img:
            width, height = img.size

            if width <= max_dimension and height <= max_dimension:
                return image_path

            # Calculate new dimensions maintaining aspect ratio
            scale = max_dimension / max(width, height)
            new_width = int(width * scale)
            new_height = int(height * scale)

            # Create temp file for resized image
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            temp_path = Path(temp_file.name)

            # Resize and save
            resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            resized.save(temp_path, "PNG")

            logger.info(f"Resized {image_path.name} from {width}x{height} to {new_width}x{new_height}")
            click.echo(f"       Resized from {width}x{height} to {new_width}x{new_height}")

            return temp_path
    except Exception as e:
        logger.warning(f"Could not resize image {image_path}: {e}")
        return image_path


class DocumentParser:
    """Parse various document types to extract model information using LLMs."""

    def __init__(self):
        """Initialize parser with LLMRing."""
        self.service = LLMRing()

    def _model_extraction_response_schema(self) -> dict:
        """Schema used for structured extraction response."""
        model_schema = {
            "type": "object",
            "properties": {
                "model_name": {"type": "string"},
                "display_name": {"type": "string"},
                "description": {"type": "string"},
                "model_aliases": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Alternative names for this model (e.g., gpt-5 for gpt-5-2025-08-07)"
                },
                "dollars_per_million_tokens_input": {"type": "number"},
                "dollars_per_million_tokens_output": {"type": "number"},
                "dollars_per_million_tokens_cached_input": {
                    "type": "number",
                    "description": "Cached input pricing (if available)"
                },
                "dollars_per_million_tokens_cache_write_5m": {
                    "type": "number",
                    "description": "Anthropic 5-minute cache write pricing"
                },
                "dollars_per_million_tokens_cache_write_1h": {
                    "type": "number",
                    "description": "Anthropic 1-hour cache write pricing"
                },
                "dollars_per_million_tokens_cache_read": {
                    "type": "number",
                    "description": "Cache read pricing"
                },
                "dollars_per_million_tokens_input_long_context": {
                    "type": "number",
                    "description": "Long-context input pricing"
                },
                "dollars_per_million_tokens_output_long_context": {
                    "type": "number",
                    "description": "Long-context output pricing"
                },
                "dollars_per_million_tokens_output_thinking": {
                    "type": "number",
                    "description": "Thinking token pricing"
                },
                "cache_storage_cost_per_million_tokens_per_hour": {
                    "type": "number",
                    "description": "Explicit cache storage cost"
                },
                "long_context_threshold_tokens": {
                    "type": "integer",
                    "description": "Token threshold for long-context pricing"
                },
                # Single types for cross-provider compatibility
                "max_input_tokens": {"type": "integer"},
                "max_output_tokens": {"type": "integer"},
                "supports_vision": {"type": "boolean"},
                "supports_function_calling": {"type": "boolean"},
                "supports_json_mode": {"type": "boolean"},
                "supports_parallel_tool_calls": {"type": "boolean"},
                "supports_streaming": {"type": "boolean"},
                "supports_documents": {"type": "boolean"},
                "supports_caching": {"type": "boolean"},
                "supports_thinking": {"type": "boolean"},
                "supports_long_context_pricing": {"type": "boolean"},
                "is_active": {"type": "boolean"},
            },
            "required": [
                "model_name",
                "display_name",
                "dollars_per_million_tokens_input",
                "dollars_per_million_tokens_output",
            ],
        }

        return {
            "type": "object",
            "properties": {
                "models": {
                    "type": "array",
                    "items": model_schema,
                }
            },
            "required": ["models"],
        }

    def _create_request(self, provider: str, file_path: Path, accumulated_models: list = None) -> LLMRequest:
        """Create a structured-output request for a given document."""
        if accumulated_models:
            # Progressive extraction with context of what we've found so far
            prompt = self._create_progressive_extraction_prompt(provider, accumulated_models)
        else:
            # Initial extraction
            prompt = self._create_extraction_prompt_text(provider)

        # Handle different file types
        if file_path.suffix.lower() == '.md':
            # For markdown files, read the content directly
            markdown_content = file_path.read_text()
            content = f"{prompt}\n\n--- DOCUMENT CONTENT ---\n{markdown_content}\n--- END DOCUMENT ---"
        else:
            # For images and PDFs, use create_file_content
            content = create_file_content(str(file_path), prompt)

        return LLMRequest(
            messages=[Message(role="user", content=content)],
            model=self._get_best_model(),
            temperature=0,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "model_extraction",
                    "schema": self._model_extraction_response_schema(),
                    "strict": True,
                },
            },
        )

    async def _chat_with_timeout(self, request: LLMRequest, timeout_seconds: int | None):
        """Call the unified chat API with a timeout and retry logic."""
        # Default to 180 seconds (3 minutes) if not specified
        timeout = timeout_seconds or 180

        # Try twice before giving up
        for attempt in range(2):
            try:
                logger.info(f"LLM call attempt {attempt + 1}/2 with timeout {timeout}s")
                response = await asyncio.wait_for(self.service.chat(request), timeout=timeout)
                return response
            except asyncio.TimeoutError:
                if attempt == 0:
                    logger.warning(f"First attempt timed out after {timeout}s, retrying...")
                    click.echo(f"    ⏱️  Timeout on attempt 1, retrying...")
                    await asyncio.sleep(2)  # Brief pause before retry
                else:
                    raise  # Re-raise on second attempt
            except Exception as e:
                if attempt == 0 and "rate" not in str(e).lower():
                    logger.warning(f"First attempt failed: {str(e)[:100]}, retrying...")
                    click.echo(f"    🔄 Retrying after error: {str(e)[:50]}...")
                    await asyncio.sleep(3)  # Brief pause before retry
                else:
                    raise  # Re-raise on second attempt or rate limit errors

        # Should not reach here, but just in case
        raise Exception("Failed after 2 attempts")

    def _strip_code_fences(self, content: str) -> str:
        """Remove Markdown code fences from a JSON string if present."""
        text = content.strip()
        if text.startswith("```json"):
            text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            return text.strip()
        if text.startswith("```"):
            text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            return text.strip()
        return text

    def _parse_models_from_response(self, response, doc_path: Path) -> list:
        """Parse and normalize model list from LLM response."""
        parsed_payload = getattr(response, "parsed", None)
        content = self._strip_code_fences(response.content)

        if parsed_payload is not None:
            if isinstance(parsed_payload, dict) and "models" in parsed_payload:
                return parsed_payload["models"]
            return parsed_payload

        try:
            models_data = json.loads(content)
            if isinstance(models_data, dict) and "models" in models_data:
                return models_data["models"]
            return models_data
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Document parse returned non-JSON content for {doc_path}: {content[:500]}"
            ) from e

    async def _process_single_document_progressive(
        self, provider: str, doc_path: Path, accumulated_models: list, timeout_seconds: int | None
    ) -> list:
        """Process a document with accumulated context and return updated complete model list."""
        if not doc_path.exists():
            logger.warning(f"Document not found: {doc_path}")
            return accumulated_models

        file_type = doc_path.suffix.lower()
        size_mb = doc_path.stat().st_size / (1024*1024)

        logger.info(
            f"Processing {doc_path.name} ({size_mb:.2f} MB, type: {file_type})"
        )
        click.echo(f"    Processing: {doc_path.name} ({file_type})")

        processed_path = doc_path
        temp_created = False

        try:
            try:
                request = self._create_request(provider, processed_path, accumulated_models)
                response = await self._chat_with_timeout(request, timeout_seconds)
            except asyncio.TimeoutError:
                # Note: This should rarely happen now with retry logic in _chat_with_timeout
                click.echo(
                    f"    ⚠️  Timeout processing {doc_path.name} after 2 attempts"
                )
                logger.warning(
                    f"Timeout processing {doc_path.name} after 2 attempts"
                )
                return accumulated_models  # Return what we have so far
            except Exception as e:
                error_msg = str(e) or "No error message provided"
                error_type = type(e).__name__

                logger.error(f"Error processing {doc_path.name}", exc_info=True)

                # Only try resizing for image files
                if file_type == '.png' and ("image dimensions exceed" in error_msg or "8000 pixels" in error_msg):
                    click.echo(
                        f"    ⚠️  Image too large: {doc_path.name}, attempting resize..."
                    )
                    logger.warning(
                        f"Image dimensions exceed limit for {doc_path.name}, attempting resize"
                    )

                    if not temp_created:
                        processed_path = _resize_image_if_needed(doc_path)
                        temp_created = processed_path != doc_path

                        if temp_created:
                            try:
                                request = self._create_request(provider, processed_path, accumulated_models)
                                response = await self._chat_with_timeout(
                                    request, timeout_seconds
                                )
                            except Exception as retry_e:
                                retry_error = (
                                    str(retry_e)
                                    or f"{type(retry_e).__name__}: No message"
                                )
                                click.echo(
                                    f"    ❌ Still failed after resize: {retry_error[:200]}"
                                )
                                logger.error(
                                    f"Failed even after resize for {doc_path.name}: {retry_error}",
                                    exc_info=True,
                                )
                                return accumulated_models
                        else:
                            click.echo("    ❌ Could not resize image")
                            return accumulated_models
                    else:
                        click.echo("    ❌ Already resized but still too large")
                        return accumulated_models
                else:
                    click.echo(f"    ❌ Error processing {doc_path.name}:")
                    click.echo(f"       Type: {error_type}")
                    if error_msg:
                        click.echo(f"       Message: {error_msg[:200]}")
                    click.echo(f"       (Use --debug flag for full traceback)")
                    return accumulated_models

            models_data = self._parse_models_from_response(response, doc_path) or []
            models_data = self._filter_paid_models(models_data)
            if models_data:
                self._write_doc_snapshot(doc_path, models_data)
                click.echo(
                    f"    ✅ Extracted {len(models_data)} models from {doc_path.name}"
                )

            if not accumulated_models:
                return models_data

            merged_models = self._merge_document_models(accumulated_models, models_data)
            return merged_models
        finally:
            if temp_created:
                try:
                    import os
                    os.unlink(processed_path)
                    logger.debug(f"Cleaned up temp file: {processed_path}")
                except Exception:
                    pass

    def _save_intermediate_results(self, provider: str, models: list, step: int):
        """Save intermediate extraction results for debugging and recovery."""
        import tempfile
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{provider}_intermediate_step{step}_{timestamp}.json"
        temp_dir = Path(tempfile.gettempdir()) / "registry_extraction"
        temp_dir.mkdir(exist_ok=True)

        filepath = temp_dir / filename
        with open(filepath, 'w') as f:
            json.dump(models, f, indent=2)

        logger.info(f"Saved intermediate results to {filepath}")
        click.echo(f"    💾 Intermediate results saved: {filepath}")

    def _write_doc_snapshot(self, doc_path: Path, models_data: list) -> None:
        """Persist extraction results for a single document next to the source."""
        try:
            snapshot_path = doc_path.with_suffix(f"{doc_path.suffix}.extracted.json")
            with open(snapshot_path, "w") as f:
                json.dump(models_data, f, indent=2)
            logger.debug(f"Saved document snapshot to {snapshot_path}")
        except Exception as exc:
            logger.warning(f"Failed to write snapshot for {doc_path}: {exc}")

    def _models_to_dict(self, models: list) -> Dict[str, Dict[str, Any]]:
        model_map: Dict[str, Dict[str, Any]] = {}
        for model in models:
            if isinstance(model, ModelInfo):
                data = asdict(model)
            elif isinstance(model, dict):
                data = model
            else:
                continue
            model_id = data.get("model_id") or data.get("model_name")
            if not model_id:
                continue
            model_map[model_id] = deepcopy(data)
        return model_map

    def _merge_document_models(self, accumulated: list, new_models: list) -> list:
        if not new_models:
            return accumulated

        accumulated_map = self._models_to_dict(accumulated)
        new_map = self._models_to_dict(new_models)

        for model_id, new_data in new_map.items():
            if model_id in accumulated_map:
                merged = self._merge_model_record(accumulated_map[model_id], new_data)
                accumulated_map[model_id] = merged
            else:
                accumulated_map[model_id] = new_data

        return list(accumulated_map.values())

    def _is_paid_model(self, model) -> bool:
        """Return True if the model has strictly positive paid pricing."""
        try:
            if isinstance(model, ModelInfo):
                input_price = float(model.dollars_per_million_tokens_input)
                output_price = float(model.dollars_per_million_tokens_output)
            else:
                input_price = float(model.get("dollars_per_million_tokens_input", 0))
                output_price = float(model.get("dollars_per_million_tokens_output", 0))
        except (TypeError, ValueError, AttributeError):
            return False
        return input_price > 0 and output_price > 0

    def _filter_paid_models(self, models: list) -> list:
        """Filter out models that do not have paid pricing."""
        return [model for model in models if self._is_paid_model(model)]

    def _validate_and_filter_models(self, models: list) -> list:
        """Validate models have required pricing information."""
        valid_models = []
        for model in models:
            # Check if model has valid pricing
            input_price = model.get("dollars_per_million_tokens_input")
            output_price = model.get("dollars_per_million_tokens_output")

            # Enforce presence of base pricing; allow 0 only if explicitly documented
            if input_price is None or output_price is None:
                model_name = model.get("model_name") or model.get("model_id") or "Unknown"
                logger.warning(
                    f"Skipping model {model_name} - missing required base pricing"
                )
                click.echo(
                    f"    ⚠️  Skipping {model_name} - missing required base pricing"
                )
                continue

            try:
                base_input = float(input_price)
                base_output = float(output_price)
            except (TypeError, ValueError):
                model_name = model.get("model_name") or model.get("model_id") or "Unknown"
                logger.warning(
                    f"Skipping model {model_name} - non-numeric pricing: input={input_price}, output={output_price}"
                )
                click.echo(
                    f"    ⚠️  Skipping {model_name} - non-numeric pricing values"
                )
                continue

            # Pricing should be non-negative; allow zero if explicitly stated (some cache tiers)
            if base_input < 0 or base_output < 0:
                model_name = model.get("model_name") or model.get("model_id") or "Unknown"
                logger.warning(
                    f"Skipping model {model_name} - negative pricing detected"
                )
                click.echo(
                    f"    ⚠️  Skipping {model_name} - negative pricing values"
                )
                continue

            valid_models.append(model)

        return valid_models

    def _map_models(self, all_models: list) -> List[ModelInfo]:
        """Convert list of dicts into strongly-typed ModelInfo objects."""
        # First validate pricing
        valid_models = self._validate_and_filter_models(all_models)

        if len(valid_models) < len(all_models):
            click.echo(
                f"    ⚠️  Filtered out {len(all_models) - len(valid_models)} models with invalid pricing"
            )

        models: List[ModelInfo] = []
        model_map: dict = {}

        def _maybe_float(value):
            if value is None:
                return None
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        def _maybe_int(value):
            if value is None:
                return None
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        def _coerce_optional_float(value, allow_zero: bool = False):
            val = _maybe_float(value)
            if val is None:
                return None
            if val < 0:
                return None
            if not allow_zero and val == 0:
                return None
            return val

        def _coerce_optional_int(value, allow_zero: bool = False):
            val = _maybe_int(value)
            if val is None:
                return None
            if val < 0:
                return None
            if not allow_zero and val == 0:
                return None
            return val

        for model_data in valid_models:
            try:
                model_id = model_data.get("model_id") or model_data.get("model_name")
                if not model_id:
                    continue
                if model_id in model_map:
                    merged = self._merge_model_record(model_map[model_id], model_data)
                    if merged:
                        model_map[model_id] = merged
                    continue

                display_name = model_data.get("display_name") or model_id
                description = model_data.get("description") or ""
                use_cases = (
                    model_data.get("use_cases")
                    or model_data.get("recommended_use_cases")
                    or []
                )
                max_input_tokens = _maybe_int(model_data.get("max_input_tokens")) or 0
                max_output_tokens = _maybe_int(model_data.get("max_output_tokens"))
                supports_vision = bool(model_data.get("supports_vision", False))
                supports_function_calling = bool(
                    model_data.get("supports_function_calling", False)
                )
                supports_json_mode = bool(model_data.get("supports_json_mode", False))
                supports_parallel_tool_calls = bool(
                    model_data.get("supports_parallel_tool_calls", False)
                )
                dollars_in = _maybe_float(model_data.get("dollars_per_million_tokens_input"))
                dollars_out = _maybe_float(model_data.get("dollars_per_million_tokens_output"))

                if dollars_in is None or dollars_out is None or dollars_in <= 0 or dollars_out <= 0:
                    model_name = model_data.get("model_name") or model_data.get("model_id") or "Unknown"
                    logger.warning(
                        f"Skipping model {model_name} - base pricing must be > 0 for paid tiers: input={dollars_in}, output={dollars_out}"
                    )
                    click.echo(
                        f"    ⚠️  Skipping {model_name} - missing or non-positive paid pricing"
                    )
                    continue

                cached_in = _coerce_optional_float(model_data.get("dollars_per_million_tokens_cached_input"))
                cache_write_5m = _coerce_optional_float(model_data.get("dollars_per_million_tokens_cache_write_5m"))
                cache_write_1h = _coerce_optional_float(model_data.get("dollars_per_million_tokens_cache_write_1h"))
                cache_read = _coerce_optional_float(model_data.get("dollars_per_million_tokens_cache_read"))
                long_input = _coerce_optional_float(model_data.get("dollars_per_million_tokens_input_long_context"))
                long_output = _coerce_optional_float(model_data.get("dollars_per_million_tokens_output_long_context"))
                thinking_output = _coerce_optional_float(model_data.get("dollars_per_million_tokens_output_thinking"))
                cache_storage = _coerce_optional_float(model_data.get("cache_storage_cost_per_million_tokens_per_hour"), allow_zero=True)
                long_threshold = _coerce_optional_int(model_data.get("long_context_threshold_tokens"))

                release_date = model_data.get("release_date")
                deprecation_date = model_data.get("deprecated_date") or model_data.get(
                    "deprecation_date"
                )
                notes = model_data.get("notes")

                # Extract model aliases
                model_aliases = model_data.get("model_aliases")
                if model_aliases and not isinstance(model_aliases, list):
                    model_aliases = [model_aliases] if model_aliases else None

                provider_name = model_data.get("provider")

                cache_pricing_values = [
                    cached_in,
                    cache_write_5m,
                    cache_write_1h,
                    cache_read,
                    cache_storage,
                ]
                supports_caching_flag = bool(model_data.get("supports_caching", False)) or any(
                    value is not None for value in cache_pricing_values
                )
                if provider_name == "anthropic":
                    supports_caching_flag = True

                supports_thinking_flag = bool(model_data.get("supports_thinking", False)) or (
                    thinking_output is not None
                )
                if provider_name == "anthropic":
                    supports_thinking_flag = True

                supports_long_context_flag = bool(
                    model_data.get("supports_long_context_pricing", False)
                ) or (
                    long_input is not None
                    or long_output is not None
                    or long_threshold is not None
                )

                mi = ModelInfo(
                    model_id=model_id,
                    display_name=display_name,
                    description=description,
                    use_cases=use_cases,
                    max_input_tokens=max_input_tokens,
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
                    dollars_per_million_tokens_cached_input=cached_in,
                    dollars_per_million_tokens_cache_write_5m=cache_write_5m,
                    dollars_per_million_tokens_cache_write_1h=cache_write_1h,
                    dollars_per_million_tokens_cache_read=cache_read,
                    dollars_per_million_tokens_input_long_context=long_input,
                    dollars_per_million_tokens_output_long_context=long_output,
                    dollars_per_million_tokens_output_thinking=thinking_output,
                    cache_storage_cost_per_million_tokens_per_hour=cache_storage,
                    long_context_threshold_tokens=long_threshold,
                    model_aliases=model_aliases,
                    supports_streaming=bool(model_data.get("supports_streaming", True)),
                    supports_audio=bool(model_data.get("supports_audio", False)),
                    supports_documents=bool(model_data.get("supports_documents", False)),
                    supports_json_schema=bool(model_data.get("supports_json_schema", False)),
                    supports_logprobs=bool(model_data.get("supports_logprobs", False)),
                    supports_multiple_responses=bool(
                        model_data.get("supports_multiple_responses", False)
                    ),
                    supports_caching=supports_caching_flag,
                    supports_thinking=supports_thinking_flag,
                    supports_long_context_pricing=supports_long_context_flag,
                    is_reasoning_model=bool(model_data.get("is_reasoning_model", False)),
                    speed_tier=model_data.get("speed_tier"),
                    intelligence_tier=model_data.get("intelligence_tier"),
                    requires_tier=_maybe_int(model_data.get("requires_tier")) or 0,
                    requires_waitlist=bool(model_data.get("requires_waitlist", False)),
                    model_family=model_data.get("model_family"),
                    recommended_use_cases=model_data.get("recommended_use_cases"),
                    is_active=bool(model_data.get("is_active", True)),
                    added_date=model_data.get("added_date"),
                )
                models.append(mi)
                model_map[model_id] = asdict(mi)  # Store as dict for merging
            except Exception:
                # Skip invalid items silently during validation flow
                continue
        return models

    def _merge_model_record(self, existing: dict, new: dict) -> dict:
        """
        Merge two model records using field-level voting.

        Only fields that are present with legal types count as votes.
        Missing fields or wrong types are ignored (not votes).
        """
        # Initialize vote tracking if not present
        if "_votes" not in existing:
            existing["_votes"] = {}
            # Seed with existing data as first vote
            for field, value in existing.items():
                if field.startswith("_"):
                    continue
                existing["_votes"][field] = [value]

        # Record votes from new data (only legal types)
        for field, value in new.items():
            if field.startswith("_"):
                continue

            # Determine expected type and validate
            is_legal = False

            # Pricing fields: float or int (will be converted to float)
            if "dollars_per_million" in field or "cache_storage_cost" in field:
                is_legal = isinstance(value, (int, float))
            # Token counts: int
            elif "_tokens" in field or field == "requires_tier":
                is_legal = isinstance(value, int)
            # Boolean fields
            elif field.startswith("supports_") or field.startswith("is_") or field.startswith("requires_"):
                is_legal = isinstance(value, bool)
            # String fields
            elif field in ["provider", "model_name", "model_id", "display_name", "description",
                          "release_date", "deprecation_date", "notes", "speed_tier",
                          "intelligence_tier", "model_family", "added_date", "api_endpoint",
                          "tool_call_format"]:
                is_legal = isinstance(value, str)
            # List fields
            elif field in ["model_aliases", "use_cases", "recommended_use_cases",
                          "temperature_values"]:
                is_legal = isinstance(value, list)
            # Numeric fields (float)
            elif field in ["max_temperature", "min_temperature"]:
                is_legal = isinstance(value, (int, float))
            else:
                # Unknown field - accept any non-None value as legal
                is_legal = value is not None

            if is_legal:
                if field not in existing["_votes"]:
                    existing["_votes"][field] = []
                existing["_votes"][field].append(value)

        return existing

    def _resolve_votes(self, models_with_votes: list) -> list:
        """
        Resolve voting for each model by picking the most common value for each field.

        For pricing fields: prefer most common positive value, ignore zeros unless unanimous.
        For other fields: pick most common value overall.
        """
        from collections import Counter

        resolved_models = []

        for model_data in models_with_votes:
            if "_votes" not in model_data:
                # No votes tracked, use as-is
                resolved_models.append(model_data)
                continue

            votes = model_data["_votes"]
            resolved = {}

            for field, value_list in votes.items():
                if not value_list:
                    continue

                # Pricing fields: prefer positive values
                if "dollars_per_million" in field or "cache_storage_cost" in field:
                    # Filter to positive values only
                    positive_values = [v for v in value_list if isinstance(v, (int, float)) and v > 0]

                    if positive_values:
                        # Pick most common positive value
                        counter = Counter(positive_values)
                        resolved[field] = counter.most_common(1)[0][0]
                    elif all(v == 0 or v is None for v in value_list):
                        # All votes are zero/null - keep None
                        resolved[field] = None
                    else:
                        # Mixed, prefer any positive value
                        for v in value_list:
                            if isinstance(v, (int, float)) and v > 0:
                                resolved[field] = v
                                break

                # Integer fields: prefer positive values, except requires_tier which can be 0
                elif "_tokens" in field or field == "requires_tier":
                    int_values = [v for v in value_list if isinstance(v, int)]
                    if field == "requires_tier":
                        # requires_tier can be 0
                        if int_values:
                            counter = Counter(int_values)
                            resolved[field] = counter.most_common(1)[0][0]
                    else:
                        # Token fields should prefer positive values
                        positive_values = [v for v in int_values if v > 0]
                        if positive_values:
                            counter = Counter(positive_values)
                            resolved[field] = counter.most_common(1)[0][0]
                        elif int_values:
                            # All zeros or mixed - take most common
                            counter = Counter(int_values)
                            resolved[field] = counter.most_common(1)[0][0]
                        else:
                            resolved[field] = None

                # Boolean fields: most common value
                elif field.startswith("supports_") or field.startswith("is_") or field.startswith("requires_"):
                    bool_values = [v for v in value_list if isinstance(v, bool)]
                    if bool_values:
                        counter = Counter(bool_values)
                        resolved[field] = counter.most_common(1)[0][0]

                # All other fields: most common non-None value
                else:
                    non_none_values = [v for v in value_list if v is not None]
                    if non_none_values:
                        counter = Counter(str(v) if isinstance(v, (list, dict)) else v for v in non_none_values)
                        # Reconstruct original value from most common
                        most_common_key = counter.most_common(1)[0][0]
                        for v in non_none_values:
                            if (str(v) if isinstance(v, (list, dict)) else v) == most_common_key:
                                resolved[field] = v
                                break

            # Don't include internal vote tracking in final output
            resolved_models.append(resolved)

        return resolved_models

    async def parse_provider_docs_async(
        self, provider: str, doc_paths: List[Path], timeout_seconds: int | None = 180,
        save_intermediate: bool = True
    ) -> List[ModelInfo]:
        """
        Parse documents for a provider to extract model information progressively.

        Args:
            provider: Provider name (anthropic, google, openai)
            doc_paths: List of document file paths to analyze (.png, .pdf, .md)
            save_intermediate: Whether to save intermediate results after each document

        Returns:
            List of extracted model information
        """
        # Count document types
        doc_types = {}
        for path in doc_paths:
            ext = path.suffix.lower()
            doc_types[ext] = doc_types.get(ext, 0) + 1

        logger.info(f"Parsing {len(doc_paths)} documents for {provider} progressively")
        logger.info(f"Document types: {doc_types}")

        # Log file sizes and paths
        for path in doc_paths:
            if path.exists():
                size_mb = path.stat().st_size / (1024 * 1024)
                logger.info(f"  - {path.name}: {size_mb:.2f} MB ({path.suffix})")

        accumulated_models: list = []

        for i, doc_path in enumerate(doc_paths):
            logger.info(f"Processing document {i+1}/{len(doc_paths)}: {doc_path.name}")

            # Process with accumulated context
            updated_models = await self._process_single_document_progressive(
                provider, doc_path, accumulated_models, timeout_seconds
            )

            if updated_models is not None:
                accumulated_models = updated_models
                click.echo(f"    Total models after {doc_path.name}: {len(accumulated_models)}")

                # Save intermediate results
                if save_intermediate and i < len(doc_paths) - 1:
                    self._save_intermediate_results(provider, accumulated_models, i+1)

        # Resolve votes to get final field values
        click.echo(f"\n    📊 Final extraction results for {provider}:")
        click.echo(f"    Total models found: {len(accumulated_models)}")
        click.echo(f"    Resolving votes from all documents...")

        resolved_models = self._resolve_votes(accumulated_models)
        click.echo(f"    Resolved {len(resolved_models)} models from voting")

        final_models = self._filter_paid_models(self._map_models(resolved_models))
        click.echo(f"    ✅ Models with valid pricing: {len(final_models)}")

        return final_models

    def parse_provider_docs(
        self, provider: str, doc_paths: List[Path], timeout_seconds: int | None = 180
    ) -> List[ModelInfo]:
        """Synchronous wrapper for environments without an event loop."""
        import asyncio as _asyncio
        return _asyncio.run(
            self.parse_provider_docs_async(provider, doc_paths, timeout_seconds)
        )

    def _get_best_model(self) -> str:
        """Return model alias for screenshot extraction from lockfile."""
        # Use extractor alias defined in lockfile
        return "extractor"

    def _supports_json_mode(self) -> bool:
        """Check if the selected model supports JSON response format."""
        # Most modern models support JSON mode
        # LLMRing will handle this appropriately per provider
        return True

    def _create_progressive_extraction_prompt(self, provider: str, accumulated_models: list) -> str:
        """Create prompt for progressive extraction with accumulated context."""
        models_summary = json.dumps(accumulated_models, indent=2)
        return f"""You are progressively extracting model information from {provider} documentation.

Here are the models we've extracted so far:
{models_summary}

Now analyze this new screenshot and:
1. Add any NEW models not in the list above
2. UPDATE existing models if this screenshot has more/better information (especially pricing!)
3. Add any model aliases (alternative names) you find
   - Prefer the most explicit name (e.g., "gpt-5-2025-08-07") as model_name
   - Add simpler names (e.g., "gpt-5") to model_aliases array
4. CRITICAL: Fix any max_input_tokens that incorrectly used the context window value
   - Remember: max_input_tokens = context_window - max_output_tokens
   - Context window is the TOTAL, not the input limit!
5. Update pricing for any models that have missing fields, but ONLY if you are 100% sure
   - Capture cached token pricing if shown (OpenAI, Anthropic, Google)
   - Anthropic cache writes: include BOTH 5-minute and 1-hour rates when present
   - Anthropic cache reads: include the discounted rate
   - Google long-context tiers: include separate input/output pricing and the threshold tokens
   - Thinking tokens: capture distinct pricing when different from base output
   - Cache storage costs: include explicit pricing per million tokens per hour when shown
   - ALWAYS use PAID tier pricing, never free tier
   - NEVER update prices if unsure - better to leave null than add incorrect numbers
6. Update capability flags:
   - supports_caching must align with cache pricing fields
   - supports_thinking only if thinking pricing or capability is documented
   - supports_long_context_pricing only if long-context pricing/threshold is present

PRICING RULES:
- If you see pricing information for a model we already have, UPDATE all relevant price fields
- If there are multiple tiers (free, standard, paid), use the PAID tier
- Convert to dollars per million tokens:
  - Price per 1K tokens → multiply by 1000
  - Price per 1M tokens → use as-is
  - Price per token → multiply by 1,000,000
- For fields the provider doesn’t publish, leave them null (do NOT guess)

Important:
- Return the COMPLETE updated list of ALL models (both existing and new)
- If a model has multiple names, use the most specific as model_name
- Preserve all information from previous extractions unless explicitly contradicted

Return the complete updated model list."""

    def _create_extraction_prompt_text(self, provider: str) -> str:
        """Create extraction prompt text."""
        return f"""Analyze the attached screenshot from {provider} and extract detailed model information.

Extract information for ALL models mentioned. For each model, include:

{{
    "model_name": "exact API model identifier (prefer explicit versions like gpt-4-0125-preview)",
    "display_name": "human-friendly name",
    "description": "comprehensive description of the model's capabilities and strengths",
    "model_aliases": ["list", "of", "alternative", "names"] or [],
    "dollars_per_million_tokens_input": base_input_cost,
    "dollars_per_million_tokens_output": base_output_cost,
    "dollars_per_million_tokens_cached_input": cached_input_cost_or_null,
    "dollars_per_million_tokens_cache_write_5m": cache_write_5m_cost_or_null,
    "dollars_per_million_tokens_cache_write_1h": cache_write_1h_cost_or_null,
    "dollars_per_million_tokens_cache_read": cache_read_cost_or_null,
    "dollars_per_million_tokens_input_long_context": long_context_input_cost_or_null,
    "dollars_per_million_tokens_output_long_context": long_context_output_cost_or_null,
    "dollars_per_million_tokens_output_thinking": thinking_output_cost_or_null,
    "cache_storage_cost_per_million_tokens_per_hour": cache_storage_cost_or_null,
    "long_context_threshold_tokens": threshold_tokens_or_null,
    "max_output_tokens": maximum_output_tokens,
    "max_input_tokens": maximum_input_tokens,  // NOT the context window! See note below
    "supports_vision": boolean,
    "supports_function_calling": boolean,
    "supports_json_mode": boolean,
    "supports_parallel_tool_calls": boolean,
    "supports_streaming": boolean,
    "supports_documents": boolean,
    "supports_caching": boolean,
    "supports_thinking": boolean,
    "supports_long_context_pricing": boolean,
    "is_active": boolean
}}

CRITICAL - CONTEXT WINDOW vs MAX INPUT TOKENS:
- "Context Window" = TOTAL tokens (input + output combined)
- "Max Input Tokens" = Maximum INPUT only
- If screenshot shows "Context Window: 128K" and "Max Output: 4K":
  → max_input_tokens = 124000 (128K - 4K)
  → max_output_tokens = 4000
- NEVER use the context window value directly as max_input_tokens!

PRICING RULES:
- Include cached token pricing if the provider publishes it (OpenAI, Anthropic, Google Gemini)
- If cached pricing appears, set "supports_caching": true; if a model explicitly lacks cached pricing, set it to false and ensure cached fields are null
- Anthropic cache writes: capture BOTH 5-minute and 1-hour rates if shown
- Anthropic cache reads: include the discounted rate
- Google long-context models: capture long context pricing and threshold tokens
- Whenever long-context pricing or threshold exists, set "supports_long_context_pricing": true; otherwise false
- Thinking tokens (Google, Anthropic) must use dedicated pricing if different from base output; if thinking pricing exists, set "supports_thinking": true
- Cache storage costs (Google explicit caching) should be captured when present
- Convert all pricing to USD per million tokens
- Omit fields entirely if the provider does not publish that pricing; do not guess or insert 0
- If a field is not applicable, leave it out so the parser can treat it as null

Return ONLY the JSON array, no other text."""
