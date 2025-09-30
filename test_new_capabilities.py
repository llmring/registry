#!/usr/bin/env python3
"""
Test script to verify the new capability fields in the registry.
"""

import json
from pathlib import Path

def test_registry_capabilities():
    """Test that the new capability fields are properly set in the registry."""
    models_dir = Path("models")

    # Test cases for specific models with known constraints
    test_cases = {
        "openai": {
            "o1-mini": {
                "supports_temperature": False,
                "temperature_values": [1.0],
                "supports_streaming": False,
                "supports_function_calling": False,
                "max_tools": 0,
                "api_endpoint": "chat",
                "is_reasoning_model": True
            },
            "gpt-5-2025-08-07": {
                "supports_temperature": False,
                "temperature_values": [1.0],
                "api_endpoint": "responses",
                "supports_function_calling": False,
                "max_tools": 0
            },
            "gpt-4o": {
                "supports_temperature": True,
                "min_temperature": 0.0,
                "max_temperature": 2.0,
                "api_endpoint": "chat"
            }
        },
        "anthropic": {
            "claude-3-5-haiku-20241022": {
                "supports_temperature": True,
                "min_temperature": 0.0,
                "max_temperature": 1.0,
                "tool_call_format": "anthropic",
                "supports_pdf_input": True
            }
        },
        "google": {
            "gemini-2.0-flash": {
                "supports_temperature": True,
                "api_endpoint": "generateContent",
                "tool_call_format": "google",
                "supports_pdf_input": True
            }
        }
    }

    print("Testing new capability fields in registry...\n")
    print("-" * 60)

    all_passed = True

    for provider, models in test_cases.items():
        registry_file = models_dir / f"{provider}.json"

        if not registry_file.exists():
            print(f"❌ Registry file not found: {registry_file}")
            all_passed = False
            continue

        with open(registry_file) as f:
            data = json.load(f)

        registry_models = data.get("models", {})

        print(f"\nTesting {provider.upper()} models:")
        print("-" * 40)

        for model_name, expected_fields in models.items():
            model_key = f"{provider}:{model_name}"

            if model_key not in registry_models:
                print(f"❌ Model not found: {model_key}")
                all_passed = False
                continue

            model_data = registry_models[model_key]

            print(f"\n  Testing {model_name}:")

            for field, expected_value in expected_fields.items():
                actual_value = model_data.get(field)

                if actual_value == expected_value:
                    print(f"    ✅ {field}: {actual_value}")
                else:
                    print(f"    ❌ {field}: expected {expected_value}, got {actual_value}")
                    all_passed = False

    print("\n" + "=" * 60)

    # Check that all required new fields exist
    print("\nChecking for presence of all new fields:")
    print("-" * 40)

    required_new_fields = [
        "supports_temperature",
        "supports_system_message",
        "supports_pdf_input",
        "api_endpoint",
        "requires_flat_input",
        "temperature_values",
        "max_temperature",
        "min_temperature",
        "max_tools",
        "supports_tool_choice",
        "tool_call_format"
    ]

    for provider in ["openai", "anthropic", "google"]:
        registry_file = models_dir / f"{provider}.json"

        with open(registry_file) as f:
            data = json.load(f)

        registry_models = data.get("models", {})

        # Check first model for presence of fields
        if registry_models:
            first_model_key = next(iter(registry_models))
            first_model = registry_models[first_model_key]

            missing_fields = []
            for field in required_new_fields:
                if field not in first_model:
                    missing_fields.append(field)

            if missing_fields:
                print(f"❌ {provider}: Missing fields: {', '.join(missing_fields)}")
                all_passed = False
            else:
                print(f"✅ {provider}: All new fields present")

    print("\n" + "=" * 60)

    if all_passed:
        print("\n✅ All tests passed! New capability fields are properly implemented.")
    else:
        print("\n❌ Some tests failed. Please review the output above.")

    return all_passed

if __name__ == "__main__":
    success = test_registry_capabilities()
    exit(0 if success else 1)