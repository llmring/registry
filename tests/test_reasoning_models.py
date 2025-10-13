"""Test reasoning model metadata in registry JSON files."""
import json
from pathlib import Path

import pytest


def test_reasoning_models_in_openai_registry():
    """Test that all reasoning models have correct metadata in OpenAI registry."""
    registry_path = Path(__file__).parent.parent / "pages" / "openai" / "models.json"

    with open(registry_path, 'r') as f:
        data = json.load(f)

    models = data.get('models', {})

    # o1 series: should have is_reasoning_model=true and min_recommended_reasoning_tokens=5000
    o1_models = ['o1', 'o1-2024-12-17', 'o1-mini', 'o1-pro', 'o1-pro-2025-03-19']
    for model_name in o1_models:
        model_key = f"openai:{model_name}"
        assert model_key in models, f"Model {model_key} not found in registry"
        model_data = models[model_key]
        assert model_data['is_reasoning_model'] is True, f"{model_name} should have is_reasoning_model=true"
        assert model_data['min_recommended_reasoning_tokens'] == 5000, f"{model_name} should have min_recommended_reasoning_tokens=5000"

    # o3 series: should have is_reasoning_model=true and min_recommended_reasoning_tokens=5000
    o3_models = [
        'o3', 'o3-2025-04-16',
        'o3-deep-research', 'o3-deep-research-2025-06-26',
        'o3-mini', 'o3-mini-2025-01-31',
        'o3-pro', 'o3-pro-2025-06-10'
    ]
    for model_name in o3_models:
        model_key = f"openai:{model_name}"
        assert model_key in models, f"Model {model_key} not found in registry"
        model_data = models[model_key]
        assert model_data['is_reasoning_model'] is True, f"{model_name} should have is_reasoning_model=true"
        assert model_data['min_recommended_reasoning_tokens'] == 5000, f"{model_name} should have min_recommended_reasoning_tokens=5000"

    # gpt-5 series: should have is_reasoning_model=true and min_recommended_reasoning_tokens=2000
    gpt5_models = [
        'gpt-5', 'gpt-5-2025-08-07', 'gpt-5-chat-latest', 'gpt-5-codex',
        'gpt-5-mini', 'gpt-5-mini-2025-08-07',
        'gpt-5-nano', 'gpt-5-nano-2025-08-07',
        'gpt-5-pro', 'gpt-5-pro-2025-10-06'
    ]
    for model_name in gpt5_models:
        model_key = f"openai:{model_name}"
        assert model_key in models, f"Model {model_key} not found in registry"
        model_data = models[model_key]
        assert model_data['is_reasoning_model'] is True, f"{model_name} should have is_reasoning_model=true"
        assert model_data['min_recommended_reasoning_tokens'] == 2000, f"{model_name} should have min_recommended_reasoning_tokens=2000"


def test_non_reasoning_models_have_correct_defaults():
    """Test that non-reasoning models have is_reasoning_model=false."""
    registry_path = Path(__file__).parent.parent / "pages" / "openai" / "models.json"

    with open(registry_path, 'r') as f:
        data = json.load(f)

    models = data.get('models', {})

    # Test a few non-reasoning models
    non_reasoning_models = ['gpt-4.1', 'gpt-4o', 'gpt-4o-mini']
    for model_name in non_reasoning_models:
        model_key = f"openai:{model_name}"
        if model_key in models:
            model_data = models[model_key]
            # Non-reasoning models should either not have the field or have it set to false
            is_reasoning = model_data.get('is_reasoning_model', False)
            assert is_reasoning is False, f"{model_name} should have is_reasoning_model=false"


def test_reasoning_model_count():
    """Test that we have the expected number of reasoning models."""
    registry_path = Path(__file__).parent.parent / "pages" / "openai" / "models.json"

    with open(registry_path, 'r') as f:
        data = json.load(f)

    models = data.get('models', {})

    # Count reasoning models
    reasoning_count = sum(1 for m in models.values() if m.get('is_reasoning_model', False))

    # We expect 23 reasoning models (5 o1 + 8 o3 + 10 gpt-5)
    assert reasoning_count == 23, f"Expected 23 reasoning models, found {reasoning_count}"


def test_json_is_valid():
    """Test that all registry JSON files are valid."""
    registry_root = Path(__file__).parent.parent

    json_files = [
        registry_root / "pages" / "openai" / "models.json",
        registry_root / "models" / "openai.json",
    ]

    for json_file in json_files:
        assert json_file.exists(), f"JSON file not found: {json_file}"
        with open(json_file, 'r') as f:
            try:
                json.load(f)
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON in {json_file}: {e}")
