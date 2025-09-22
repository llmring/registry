"""Document parser to extract model information using LLMRing's unified interface.

Supports multiple document types:
- Screenshots (.png) - processed as images
- PDFs (.pdf) - processed as documents
- Markdown (.md) - processed as text content
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
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
                # Single types for cross-provider compatibility
                "max_input_tokens": {"type": "integer"},
                "max_output_tokens": {"type": "integer"},
                "supports_vision": {"type": "boolean"},
                "supports_function_calling": {"type": "boolean"},
                "supports_json_mode": {"type": "boolean"},
                "supports_parallel_tool_calls": {"type": "boolean"},
                "supports_streaming": {"type": "boolean"},
                "supports_documents": {"type": "boolean"},
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
                # Create request with accumulated context
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

            models_data = self._parse_models_from_response(response, doc_path)
            if models_data:
                click.echo(
                    f"    ✅ Extracted {len(models_data)} models from {doc_path.name}"
                )
            return models_data or []
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

    def _validate_and_filter_models(self, models: list) -> list:
        """Validate models have required pricing information."""
        valid_models = []
        for model in models:
            # Check if model has valid pricing
            input_price = model.get("dollars_per_million_tokens_input", 0) or 0
            output_price = model.get("dollars_per_million_tokens_output", 0) or 0

            if input_price <= 0 or output_price <= 0:
                model_name = model.get("model_name") or model.get("model_id") or "Unknown"
                logger.warning(
                    f"Skipping model {model_name} - invalid pricing: "
                    f"input=${input_price}, output=${output_price}"
                )
                click.echo(
                    f"    ⚠️  Skipping {model_name} - missing or zero pricing"
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
        for model_data in valid_models:
            try:
                model_id = model_data.get("model_id") or model_data.get("model_name")
                display_name = model_data.get("display_name") or model_id
                description = model_data.get("description") or ""
                use_cases = (
                    model_data.get("use_cases")
                    or model_data.get("recommended_use_cases")
                    or []
                )
                max_input_tokens = model_data.get("max_input_tokens", 0) or 0
                max_output_tokens = model_data.get("max_output_tokens")
                supports_vision = bool(model_data.get("supports_vision", False))
                supports_function_calling = bool(
                    model_data.get("supports_function_calling", False)
                )
                supports_json_mode = bool(model_data.get("supports_json_mode", False))
                supports_parallel_tool_calls = bool(
                    model_data.get("supports_parallel_tool_calls", False)
                )
                dollars_in = float(
                    model_data.get("dollars_per_million_tokens_input", 0) or 0
                )
                dollars_out = float(
                    model_data.get("dollars_per_million_tokens_output", 0) or 0
                )
                release_date = model_data.get("release_date")
                deprecation_date = model_data.get("deprecated_date") or model_data.get(
                    "deprecation_date"
                )
                notes = model_data.get("notes")

                # Extract model aliases
                model_aliases = model_data.get("model_aliases")
                if model_aliases and not isinstance(model_aliases, list):
                    model_aliases = [model_aliases] if model_aliases else None

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
                    model_aliases=model_aliases,
                    supports_streaming=bool(model_data.get("supports_streaming", True)),
                    supports_audio=bool(model_data.get("supports_audio", False)),
                    supports_documents=bool(model_data.get("supports_documents", False)),
                    supports_json_schema=bool(model_data.get("supports_json_schema", False)),
                    supports_logprobs=bool(model_data.get("supports_logprobs", False)),
                    supports_multiple_responses=bool(
                        model_data.get("supports_multiple_responses", False)
                    ),
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

            if updated_models:
                # Replace accumulated models with the updated complete list
                accumulated_models = updated_models
                click.echo(f"    Total models after {doc_path.name}: {len(accumulated_models)}")

                # Save intermediate results
                if save_intermediate and i < len(doc_paths) - 1:
                    self._save_intermediate_results(provider, accumulated_models, i+1)

        # Final validation and conversion
        click.echo(f"\n    📊 Final extraction results for {provider}:")
        click.echo(f"    Total models found: {len(accumulated_models)}")

        final_models = self._map_models(accumulated_models)
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
5. Update pricing for any models that have 0 or missing prices, but ONLY if you are 100% sure
   - Look for pricing tables, cost information, rate cards
   - ALWAYS use PAID tier pricing, never free tier
   - NEVER update prices if unsure - better to have no price than wrong price

PRICING RULES:
- If you see pricing information for a model we already have, UPDATE the prices
- If there are multiple tiers (free, standard, paid), use the PAID tier
- Convert to dollars per million tokens:
  - Price per 1K tokens → multiply by 1000
  - Price per 1M tokens → use as-is
  - Price per token → multiply by 1,000,000

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
    "dollars_per_million_tokens_input": input_cost,
    "dollars_per_million_tokens_output": output_cost,
    "max_output_tokens": maximum_output_tokens,
    "max_input_tokens": maximum_input_tokens,  // NOT the context window! See note below
    "supports_vision": boolean,
    "supports_function_calling": boolean,
    "supports_json_mode": boolean,
    "supports_parallel_tool_calls": boolean,
    "supports_streaming": boolean,
    "supports_documents": boolean,
    "is_active": boolean
}}

CRITICAL - CONTEXT WINDOW vs MAX INPUT TOKENS:
- "Context Window" = TOTAL tokens (input + output combined)
- "Max Input Tokens" = Maximum INPUT only
- If screenshot shows "Context Window: 128K" and "Max Output: 4K":
  → max_input_tokens = 124000 (128K - 4K)
  → max_output_tokens = 4000
- NEVER use the context window value directly as max_input_tokens!

Important notes:
1. Extract EXACT model IDs as used in API calls
2. If a model has multiple names (e.g., gpt-4 and gpt-4-0125-preview):
   - Use the most explicit/versioned name as model_name
   - Add simpler names to model_aliases
3. Convert all pricing to dollars per million tokens
4. If pricing has multiple tiers (free/paid), use the paid tier
5. Be comprehensive in descriptions

Return ONLY the JSON array, no other text."""
