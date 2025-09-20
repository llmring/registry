"""Confidence scoring and consensus merging utilities for dual-source extraction."""

from __future__ import annotations

from typing import Any, Dict, Tuple


def _priority_value(html_value: Any, pdf_value: Any, field_name: str) -> Tuple[Any, bool, bool]:
    """
    Choose a value based on field-specific priority rules.

    Returns (value, one_is_null, both_non_null_but_different)
    """
    html_is_null = html_value is None
    pdf_is_null = pdf_value is None
    one_is_null = html_is_null ^ pdf_is_null
    both_non_null_but_different = (
        (not html_is_null) and (not pdf_is_null) and (html_value != pdf_value)
    )

    if field_name in [
        "dollars_per_million_tokens_input",
        "dollars_per_million_tokens_output",
    ]:
        # Prefer HTML for pricing (more current)
        value = html_value if not html_is_null else pdf_value
    elif field_name in [
        "max_input_tokens",
        "max_output_tokens",
        "supports_vision",
        "context_window_tokens",
    ]:
        # Prefer PDF for technical specs (more detailed)
        value = pdf_value if not pdf_is_null else html_value
    else:
        # Default: prefer non-null value
        value = html_value if not html_is_null else pdf_value

    return value, one_is_null, both_non_null_but_different


def calculate_field_confidence(
    html_value: Any, pdf_value: Any, field_name: str
) -> Dict[str, Any]:
    """
    Calculate confidence for a field based on source agreement.

    Returns a structure containing the chosen value, confidence label, and source details.
    """
    if html_value == pdf_value:
        return {
            "value": html_value,
            "confidence": "certain",
            "sources": {"html": html_value, "pdf": pdf_value},
            "conflict": False,
        }

    value, one_is_null, both_non_null_but_different = _priority_value(
        html_value, pdf_value, field_name
    )

    return {
        "value": value,
        "confidence": "probable" if one_is_null else "uncertain",
        "sources": {"html": html_value, "pdf": pdf_value},
        "conflict": both_non_null_but_different,
    }


def merge_model_records(html_model: Dict[str, Any], pdf_model: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two model dicts field-by-field using confidence scoring rules.

    Produces a flat model dict without confidence annotations for storage, but also
    returns a "_confidence" map inside the dict for optional inspection.
    """
    # Union of keys
    keys = set(html_model.keys()) | set(pdf_model.keys())

    merged: Dict[str, Any] = {}
    confidence_map: Dict[str, Dict[str, Any]] = {}

    for key in keys:
        if key.startswith("_"):
            # skip internal keys
            continue
        html_val = html_model.get(key)
        pdf_val = pdf_model.get(key)
        field_result = calculate_field_confidence(html_val, pdf_val, key)
        merged[key] = field_result["value"]
        confidence_map[key] = {
            "confidence": field_result["confidence"],
            "conflict": field_result["conflict"],
        }

    merged["_confidence"] = confidence_map
    return merged


def merge_with_consensus(
    html_models: Dict[str, Dict[str, Any]],
    pdf_models: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """
    Merge two keyed model maps {model_key: model_dict} into a single map with consensus.
    """
    merged: Dict[str, Dict[str, Any]] = {}
    all_keys = set(html_models.keys()) | set(pdf_models.keys())

    for key in all_keys:
        h = html_models.get(key)
        p = pdf_models.get(key)
        if h and p:
            merged[key] = merge_model_records(h, p)
        else:
            # If only present in one source, carry as-is and mark low confidence
            single = h or p or {}
            merged[key] = single.copy()
            conf = {k: {"confidence": "probable", "conflict": False} for k in single.keys()}
            merged[key]["_confidence"] = conf

    return merged


def calculate_confidence_summary(models: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
    """Summarize counts of certain/probable/uncertain across all model fields."""
    summary = {"certain": 0, "probable": 0, "uncertain": 0}
    for model in models.values():
        cmap = model.get("_confidence", {})
        for meta in cmap.values():
            label = meta.get("confidence")
            if label in summary:
                summary[label] += 1
    return summary


