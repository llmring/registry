#!/usr/bin/env python3
"""
Update existing registry JSON files with new capability fields.
This script adds the new capability flags from the enhanced model capabilities feature request.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List

def get_default_capabilities() -> Dict[str, Any]:
    """Return default values for new capability fields."""
    return {
        "supports_temperature": True,
        "supports_system_message": True,
        "supports_pdf_input": False,
        "api_endpoint": "chat",
        "requires_flat_input": False,
        "temperature_values": None,
        "max_temperature": None,
        "min_temperature": None,
        "max_tools": None,
        "supports_tool_choice": True,
        "tool_call_format": None,
    }

def update_openai_model(model_key: str, model_data: Dict[str, Any]) -> Dict[str, Any]:
    """Apply OpenAI-specific capability updates."""
    model_name = model_data.get("model_name", "")

    # Add default capabilities first
    defaults = get_default_capabilities()
    for key, value in defaults.items():
        if key not in model_data:
            model_data[key] = value

    # Special handling for o1 models (reasoning models)
    if model_name.startswith("o1-") or model_name == "o1":
        model_data["supports_temperature"] = False
        model_data["temperature_values"] = [1.0]
        model_data["supports_streaming"] = False
        model_data["supports_function_calling"] = False
        model_data["supports_tool_choice"] = False
        model_data["max_tools"] = 0
        model_data["api_endpoint"] = "chat"
        model_data["is_reasoning_model"] = True

    # Special handling for GPT-5 models
    if model_name.startswith("gpt-5") or "gpt-5" in model_name.lower():
        model_data["supports_temperature"] = False
        model_data["temperature_values"] = [1.0]
        model_data["api_endpoint"] = "responses"  # Uses Responses API
        model_data["supports_function_calling"] = False
        model_data["max_tools"] = 0

    # GPT-4 models support everything
    if model_name.startswith("gpt-4"):
        model_data["supports_temperature"] = True
        model_data["temperature_values"] = None  # All values allowed
        model_data["min_temperature"] = 0.0
        model_data["max_temperature"] = 2.0

    # GPT-3.5 models
    if model_name.startswith("gpt-3.5"):
        model_data["supports_temperature"] = True
        model_data["min_temperature"] = 0.0
        model_data["max_temperature"] = 2.0

    return model_data

def update_anthropic_model(model_key: str, model_data: Dict[str, Any]) -> Dict[str, Any]:
    """Apply Anthropic-specific capability updates."""
    model_name = model_data.get("model_name", "")

    # Add default capabilities
    defaults = get_default_capabilities()
    for key, value in defaults.items():
        if key not in model_data:
            model_data[key] = value

    # All Anthropic models support temperature
    model_data["supports_temperature"] = True
    model_data["min_temperature"] = 0.0
    model_data["max_temperature"] = 1.0

    # Anthropic uses different tool format
    model_data["tool_call_format"] = "anthropic"

    # Claude 3 models support vision
    if "claude-3" in model_name:
        model_data["supports_pdf_input"] = True  # Can process PDFs via vision

    return model_data

def update_google_model(model_key: str, model_data: Dict[str, Any]) -> Dict[str, Any]:
    """Apply Google-specific capability updates."""
    model_name = model_data.get("model_name", "")

    # Add default capabilities
    defaults = get_default_capabilities()
    for key, value in defaults.items():
        if key not in model_data:
            model_data[key] = value

    # Google models support temperature
    model_data["supports_temperature"] = True
    model_data["min_temperature"] = 0.0
    model_data["max_temperature"] = 2.0

    # Gemini models use different endpoint
    if "gemini" in model_name.lower():
        model_data["api_endpoint"] = "generateContent"
        model_data["tool_call_format"] = "google"

    # Gemini 1.5+ and 2.0+ models support PDFs
    if ("gemini-pro" in model_name.lower() or
        "gemini-1.5" in model_name.lower() or
        "gemini-2" in model_name.lower()):
        model_data["supports_pdf_input"] = True

    return model_data

def update_registry_file(file_path: Path) -> None:
    """Update a registry JSON file with new capability fields."""
    print(f"Updating {file_path}...")

    # Load existing data
    with open(file_path, 'r') as f:
        data = json.load(f)

    provider = data.get("provider", "")
    models = data.get("models", {})

    # Track changes
    updated_count = 0

    # Update each model based on provider
    for model_key, model_data in models.items():
        original = model_data.copy()

        if provider == "openai":
            model_data = update_openai_model(model_key, model_data)
        elif provider == "anthropic":
            model_data = update_anthropic_model(model_key, model_data)
        elif provider == "google":
            model_data = update_google_model(model_key, model_data)
        else:
            # Add defaults for unknown providers
            defaults = get_default_capabilities()
            for key, value in defaults.items():
                if key not in model_data:
                    model_data[key] = value

        # Update the model in the dictionary
        models[model_key] = model_data

        # Check if anything changed
        if original != model_data:
            updated_count += 1
            print(f"  Updated {model_key}")

    # Write back the updated data
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"  Total models updated: {updated_count}/{len(models)}")

def main():
    """Main function to update all registry files."""
    models_dir = Path("models")

    if not models_dir.exists():
        print(f"Error: {models_dir} directory not found")
        return

    # Find all JSON files in the models directory
    json_files = list(models_dir.glob("*.json"))

    if not json_files:
        print(f"No JSON files found in {models_dir}")
        return

    print(f"Found {len(json_files)} registry files to update")
    print("-" * 50)

    for file_path in sorted(json_files):
        update_registry_file(file_path)
        print()

    print("-" * 50)
    print("Registry update complete!")
    print("\nImportant models with special handling:")
    print("- OpenAI o1 models: no temperature support, no tools")
    print("- OpenAI GPT-5 models: no temperature support, uses Responses API")
    print("- Anthropic Claude 3: supports PDF input via vision")
    print("- Google Gemini Pro: supports PDF input directly")

if __name__ == "__main__":
    main()