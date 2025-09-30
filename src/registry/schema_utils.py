"""Schema utilities for standardizing model data format.

This module provides functions to normalize and standardize the registry schema:
- Null vs empty array handling
- Consistent metadata format
- Required field validation
"""

from typing import Any, Dict, List, Optional


def normalize_model_data(model: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a single model's data to follow consistent schema rules.

    Rules:
    1. Empty arrays should be [] not null
    2. Optional strings should be null not ""
    3. Boolean defaults should be explicit
    4. Numbers should never be null (use 0 for unknown)
    """
    normalized = model.copy()

    # Array fields - should be [] not null
    array_fields = [
        "model_aliases",
        "recommended_use_cases",
        "temperature_values",  # New: List[float] for allowed temperature values
    ]
    for field in array_fields:
        value = normalized.get(field)
        if value is None:
            normalized[field] = [] if field != "temperature_values" else None  # temperature_values can be null (unrestricted)
        elif not isinstance(value, list):
            # Convert single value to list
            normalized[field] = [value] if value else []

    # Optional string fields - should be null not ""
    optional_string_fields = [
        "speed_tier",
        "intelligence_tier",
        "model_family",
        "release_date",
        "deprecated_date",
        "added_date",
        "description",
        "notes",
        "api_endpoint",  # New: "chat", "responses", "assistants", etc.
        "tool_call_format",  # New: format specification for tool calls
    ]
    for field in optional_string_fields:
        value = normalized.get(field)
        if value == "":
            normalized[field] = None
        elif field == "description" and value is None:
            # Description should at least be empty string, not null
            normalized[field] = ""

    # Boolean fields - ensure explicit values
    boolean_fields = [
        "supports_vision",
        "supports_function_calling",
        "supports_json_mode",
        "supports_parallel_tool_calls",
        "supports_streaming",
        "supports_audio",
        "supports_documents",
        "supports_json_schema",
        "supports_logprobs",
        "supports_multiple_responses",
        "supports_caching",
        "is_reasoning_model",
        "requires_waitlist",
        "is_active",
        "supports_temperature",  # New: False if model only uses default temperature
        "supports_system_message",  # New: Some models don't support system role
        "supports_pdf_input",  # New: Whether PDFs can be processed directly
        "requires_flat_input",  # New: Some models require flattened message structures
        "supports_tool_choice",  # New: Whether model supports tool_choice parameter
    ]
    for field in boolean_fields:
        if field not in normalized:
            # Set reasonable defaults
            if field == "supports_streaming":
                normalized[field] = True  # Most models support streaming
            elif field == "is_active":
                normalized[field] = True  # Assume active unless stated otherwise
            elif field in ["supports_temperature", "supports_system_message", "supports_tool_choice"]:
                normalized[field] = True  # Most models support these
            elif field in ["supports_pdf_input", "requires_flat_input"]:
                normalized[field] = False  # These are special capabilities
            else:
                normalized[field] = False
        else:
            # Ensure it's actually boolean
            normalized[field] = bool(normalized[field])

    # Numeric fields - ensure not null (except truly optional constraint fields)
    numeric_fields = [
        "max_input_tokens",
        "max_output_tokens",
        "dollars_per_million_tokens_input",
        "dollars_per_million_tokens_output",
        "requires_tier",
    ]
    for field in numeric_fields:
        if field in normalized and normalized[field] is None:
            if field.startswith("dollars_"):
                # Pricing should never be null - if unknown, validation should catch it
                normalized[field] = 0.0
            else:
                normalized[field] = 0

    # Optional numeric constraint fields - can be null (meaning no constraint/default behavior)
    optional_numeric_fields = [
        "max_temperature",  # New: Maximum allowed temperature value
        "min_temperature",  # New: Minimum allowed temperature value
        "max_tools",  # New: Maximum number of tools that can be provided
    ]
    # These fields should remain null if not specified - null means "no explicit constraint"
    # No normalization needed, just ensure they're numeric if present
    for field in optional_numeric_fields:
        if field in normalized and normalized[field] is not None:
            # Ensure it's numeric
            normalized[field] = float(normalized[field]) if "temperature" in field else int(normalized[field])

    return normalized


def normalize_extraction_metadata(draft_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize the extraction metadata at the top level of draft files.

    Standardizes the 'sources' field to always include:
    - documents: total count of all source documents
    - png_files: count of PNG screenshots
    - pdf_files: count of PDF documents
    - md_files: count of markdown files
    - models_extracted: count of models extracted
    """
    normalized = draft_data.copy()

    # Ensure sources field exists and has standard structure
    if "sources" not in normalized:
        normalized["sources"] = {}

    sources = normalized["sources"]

    # Normalize to standard structure
    standard_sources = {
        "documents": 0,
        "png_files": 0,
        "pdf_files": 0,
        "md_files": 0,
        "models_extracted": len(normalized.get("models", {}))
    }

    # Preserve existing counts if present
    for key in ["documents", "png_files", "pdf_files", "md_files", "models_extracted"]:
        if key in sources:
            standard_sources[key] = sources[key]

    # Handle legacy field names
    if "screenshot" in sources:
        standard_sources["png_files"] = sources["screenshot"]
    if "html" in sources:
        # HTML was deprecated in favor of PNG/PDF
        pass

    # Calculate total documents
    doc_count = (
        standard_sources["png_files"] +
        standard_sources["pdf_files"] +
        standard_sources["md_files"]
    )
    if doc_count > 0:
        standard_sources["documents"] = doc_count

    normalized["sources"] = standard_sources

    return normalized


def validate_required_fields(model: Dict[str, Any]) -> List[str]:
    """
    Validate that a model has all required fields.

    Returns:
        List of missing required fields (empty if valid)
    """
    required_fields = [
        "provider",
        "model_name",
        "display_name",
        "dollars_per_million_tokens_input",
        "dollars_per_million_tokens_output",
        "is_active",
    ]

    missing = []
    for field in required_fields:
        if field not in model:
            missing.append(field)
        elif model[field] is None and field in ["provider", "model_name", "display_name"]:
            # These string fields must not be null
            missing.append(f"{field} (is null)")

    return missing


def normalize_draft_file(draft_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize an entire draft file.

    This applies:
    1. Metadata normalization
    2. Per-model data normalization
    3. Field validation

    Returns:
        Normalized draft data
    """
    # Normalize top-level metadata
    normalized = normalize_extraction_metadata(draft_data)

    # Normalize each model
    if "models" in normalized and isinstance(normalized["models"], dict):
        normalized_models = {}
        for model_key, model_data in normalized["models"].items():
            normalized_models[model_key] = normalize_model_data(model_data)
        normalized["models"] = normalized_models

    return normalized


def generate_schema_report(draft_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a report on schema compliance for a draft file.

    Returns:
        Report dict with validation results
    """
    models = draft_data.get("models", {})
    total = len(models)

    issues = []
    models_with_issues = 0

    for model_key, model_data in models.items():
        model_issues = []

        # Check required fields
        missing = validate_required_fields(model_data)
        if missing:
            model_issues.append(f"Missing required: {', '.join(missing)}")

        # Check array fields
        for field in ["model_aliases", "recommended_use_cases"]:
            value = model_data.get(field)
            if value is not None and not isinstance(value, list):
                model_issues.append(f"{field} should be array, got {type(value).__name__}")

        # Check boolean fields
        boolean_fields = ["supports_vision", "supports_function_calling", "is_active"]
        for field in boolean_fields:
            value = model_data.get(field)
            if value is not None and not isinstance(value, bool):
                model_issues.append(f"{field} should be boolean, got {type(value).__name__}")

        # Check numeric fields
        for field in ["max_input_tokens", "max_output_tokens"]:
            value = model_data.get(field)
            if value is None:
                model_issues.append(f"{field} is null (should be 0 if unknown)")

        # Check pricing
        input_price = model_data.get("dollars_per_million_tokens_input")
        output_price = model_data.get("dollars_per_million_tokens_output")
        if input_price is not None and input_price <= 0:
            model_issues.append(f"Invalid input pricing: {input_price}")
        if output_price is not None and output_price <= 0:
            model_issues.append(f"Invalid output pricing: {output_price}")

        if model_issues:
            models_with_issues += 1
            issues.append({
                "model": model_key,
                "issues": model_issues
            })

    return {
        "total_models": total,
        "models_with_issues": models_with_issues,
        "compliance_rate": (total - models_with_issues) / total if total > 0 else 0,
        "issues": issues
    }