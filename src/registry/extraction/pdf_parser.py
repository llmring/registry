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

            # Use LLMRing with its default configuration
            # It will automatically handle PDFs appropriately for each provider
            self.service = LLMRing(enable_db_logging=False)
            self.initialized = True
        except ImportError:
            logger.error("LLMRing not available. Install with: uv add llmring")
            self.service = None
            self.initialized = False
        except Exception as e:
            logger.error(f"Failed to initialize LLMRing: {e}")
            self.service = None
            self.initialized = False

    def parse_provider_docs(
        self, provider: str, pdf_paths: List[Path]
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

            try:
                # Use LLMRing's analyze_file to create proper content for any provider
                content = analyze_file(
                    str(pdf_path), self._create_extraction_prompt_text(provider)
                )

                # Create request using LLMRing's unified interface
                request = LLMRequest(
                    messages=[Message(role="user", content=content)],
                    model=self._get_best_model(),  # Auto-select best available model
                    max_tokens=4000,
                    temperature=0,
                    response_format=(
                        {"type": "json_object"} if self._supports_json_mode() else None
                    ),
                )

                # Run async request
                response = asyncio.run(self.service.chat(request))

                # Parse response
                try:
                    # First try direct JSON parsing
                    models_data = json.loads(response.content)
                    if isinstance(models_data, dict) and "models" in models_data:
                        models_data = models_data["models"]
                except json.JSONDecodeError:
                    # Try to find JSON array in response
                    import re

                    json_match = re.search(r"\[.*\]", response.content, re.DOTALL)
                    if json_match:
                        models_data = json.loads(json_match.group())
                    else:
                        logger.warning(
                            f"Could not parse JSON from response for {pdf_path}"
                        )
                        models_data = []

                # Add parsed models to results
                if models_data:
                    all_models.extend(models_data)

            except Exception as e:
                logger.error(f"Failed to process {pdf_path}: {e}")
                continue

        # Convert to ModelInfo objects
        models = []
        for model_data in all_models:
            try:
                models.append(ModelInfo(**model_data))
            except Exception as e:
                logger.error(f"Failed to parse model data: {e}")
                logger.error(f"Data: {model_data}")

        return models

    def _get_best_model(self) -> str:
        """Get the best available model for PDF extraction."""
        available_models = self.service.get_available_models()

        # Prefer models in this order for best PDF understanding
        preferred_models = [
            "claude-3-5-sonnet-20241022",  # Best for PDFs
            "gpt-4o",  # Good with Assistants API
            "gemini-1.5-flash",  # Fast and capable
            "claude-3-5-haiku-20241022",  # Fast Claude
            "gpt-4o-mini",  # Fallback
        ]

        for model in preferred_models:
            for provider_models in available_models.values():
                if model in provider_models:
                    logger.info(f"Using model: {model}")
                    return model

        # Fallback to first available model
        for provider_models in available_models.values():
            if provider_models:
                model = provider_models[0]
                logger.info(f"Using fallback model: {model}")
                return model

        raise ValueError("No models available")

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
