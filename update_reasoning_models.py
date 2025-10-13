#!/usr/bin/env python3
"""
Script to update reasoning model metadata in registry JSON files.
"""
import json
from pathlib import Path

# Define which models need updates
REASONING_MODELS_CONFIG = {
    # o1 series: already has is_reasoning_model=true, just add min_recommended_reasoning_tokens
    "o1": {"is_reasoning_model": True, "min_recommended_reasoning_tokens": 5000},
    "o1-2024-12-17": {"is_reasoning_model": True, "min_recommended_reasoning_tokens": 5000},
    "o1-mini": {"is_reasoning_model": True, "min_recommended_reasoning_tokens": 5000},
    "o1-pro": {"is_reasoning_model": True, "min_recommended_reasoning_tokens": 5000},
    "o1-pro-2025-03-19": {"is_reasoning_model": True, "min_recommended_reasoning_tokens": 5000},

    # o3 series: change is_reasoning_model to true and add min_recommended_reasoning_tokens
    "o3": {"is_reasoning_model": True, "min_recommended_reasoning_tokens": 5000},
    "o3-2025-04-16": {"is_reasoning_model": True, "min_recommended_reasoning_tokens": 5000},
    "o3-deep-research": {"is_reasoning_model": True, "min_recommended_reasoning_tokens": 5000},
    "o3-deep-research-2025-06-26": {"is_reasoning_model": True, "min_recommended_reasoning_tokens": 5000},
    "o3-mini": {"is_reasoning_model": True, "min_recommended_reasoning_tokens": 5000},
    "o3-mini-2025-01-31": {"is_reasoning_model": True, "min_recommended_reasoning_tokens": 5000},
    "o3-pro": {"is_reasoning_model": True, "min_recommended_reasoning_tokens": 5000},
    "o3-pro-2025-06-10": {"is_reasoning_model": True, "min_recommended_reasoning_tokens": 5000},

    # gpt-5 series: change is_reasoning_model to true and add min_recommended_reasoning_tokens
    "gpt-5": {"is_reasoning_model": True, "min_recommended_reasoning_tokens": 2000},
    "gpt-5-2025-08-07": {"is_reasoning_model": True, "min_recommended_reasoning_tokens": 2000},
    "gpt-5-chat-latest": {"is_reasoning_model": True, "min_recommended_reasoning_tokens": 2000},
    "gpt-5-codex": {"is_reasoning_model": True, "min_recommended_reasoning_tokens": 2000},
    "gpt-5-mini": {"is_reasoning_model": True, "min_recommended_reasoning_tokens": 2000},
    "gpt-5-mini-2025-08-07": {"is_reasoning_model": True, "min_recommended_reasoning_tokens": 2000},
    "gpt-5-nano": {"is_reasoning_model": True, "min_recommended_reasoning_tokens": 2000},
    "gpt-5-nano-2025-08-07": {"is_reasoning_model": True, "min_recommended_reasoning_tokens": 2000},
    "gpt-5-pro": {"is_reasoning_model": True, "min_recommended_reasoning_tokens": 2000},
    "gpt-5-pro-2025-10-06": {"is_reasoning_model": True, "min_recommended_reasoning_tokens": 2000},
}

def update_json_file(file_path: Path):
    """Update reasoning model metadata in a JSON file."""
    print(f"\nProcessing: {file_path}")

    with open(file_path, 'r') as f:
        data = json.load(f)

    if 'models' not in data:
        print(f"  ⚠️  No 'models' key in {file_path}")
        return

    updates_made = 0
    for model_key, model_data in data['models'].items():
        # Extract model name from key (format: "openai:model-name")
        if ':' in model_key:
            _, model_name = model_key.split(':', 1)
        else:
            model_name = model_data.get('model_name', '')

        if model_name in REASONING_MODELS_CONFIG:
            config = REASONING_MODELS_CONFIG[model_name]

            # Update is_reasoning_model
            old_value = model_data.get('is_reasoning_model')
            model_data['is_reasoning_model'] = config['is_reasoning_model']

            # Add min_recommended_reasoning_tokens
            model_data['min_recommended_reasoning_tokens'] = config['min_recommended_reasoning_tokens']

            if old_value != config['is_reasoning_model']:
                print(f"  ✓ {model_name}: is_reasoning_model {old_value} → {config['is_reasoning_model']}, added min_recommended_reasoning_tokens={config['min_recommended_reasoning_tokens']}")
            else:
                print(f"  ✓ {model_name}: added min_recommended_reasoning_tokens={config['min_recommended_reasoning_tokens']}")
            updates_made += 1

    # Write back with proper formatting
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
        f.write('\n')  # Add trailing newline

    print(f"  📝 Updated {updates_made} models in {file_path.name}")

def main():
    """Update all OpenAI JSON files."""
    registry_root = Path(__file__).parent

    # Files to update
    files_to_update = [
        registry_root / "models" / "openai.json",
        registry_root / "pages" / "openai" / "models.json",
    ]

    print("🔧 Updating reasoning model metadata...")
    print(f"Total models to update: {len(REASONING_MODELS_CONFIG)}")

    for file_path in files_to_update:
        if file_path.exists():
            update_json_file(file_path)
        else:
            print(f"  ⚠️  File not found: {file_path}")

    print("\n✅ Done!")

if __name__ == "__main__":
    main()
