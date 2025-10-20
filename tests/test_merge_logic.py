# ABOUTME: Comprehensive tests for the merge logic in promote.py
# ABOUTME: Tests critical behaviors for preserving production data during registry updates

import pytest
from src.registry.promote import _merge_model, _merge_registry, UPDATE_FIELDS


class TestMergeModel:
    """Tests for _merge_model function."""

    def test_merge_model_preserves_non_update_fields(self):
        """Non-UPDATE_FIELDS should be preserved from current when draft has null or missing."""
        current = {
            "model_name": "gpt-4o",
            "provider": "openai",
            "display_name": "GPT-4o",
            "description": "A powerful multimodal model",
            "api_endpoint": "chat",
            "dollars_per_million_tokens_input": 5.0,
            "dollars_per_million_tokens_output": 15.0
        }
        draft = {
            "model_name": "gpt-4o",
            "provider": "openai",
            "display_name": None,  # Null in draft
            "description": None,   # Null in draft
            # api_endpoint not in draft at all
            "dollars_per_million_tokens_input": 2.5,
            "dollars_per_million_tokens_output": 10.0
        }

        merged = _merge_model(current, draft)

        # Non-UPDATE_FIELDS should be preserved from current
        assert merged["display_name"] == "GPT-4o"
        assert merged["description"] == "A powerful multimodal model"
        assert merged["api_endpoint"] == "chat"
        # UPDATE_FIELDS should be updated from draft
        assert merged["dollars_per_million_tokens_input"] == 2.5
        assert merged["dollars_per_million_tokens_output"] == 10.0

    def test_merge_model_only_updates_non_null_draft_values(self):
        """UPDATE_FIELDS with null values in draft should be preserved from current."""
        current = {
            "model_name": "claude-3-5-sonnet-20241022",
            "provider": "anthropic",
            "dollars_per_million_tokens_input": 3.0,
            "dollars_per_million_tokens_output": 15.0,
            "dollars_per_million_tokens_cache_read": 0.30,
            "dollars_per_million_tokens_cache_write_5m": 3.75,
            "dollars_per_million_tokens_cache_write_1h": 3.00,
            "supports_vision": True,
            "supports_function_calling": True
        }
        draft = {
            "model_name": "claude-3-5-sonnet-20241022",
            "provider": "anthropic",
            "dollars_per_million_tokens_input": 3.0,
            "dollars_per_million_tokens_output": 15.0,
            # Cache pricing null in draft
            "dollars_per_million_tokens_cache_read": None,
            "dollars_per_million_tokens_cache_write_5m": None,
            "dollars_per_million_tokens_cache_write_1h": None,
            # Capabilities null in draft
            "supports_vision": None,
            "supports_function_calling": None
        }

        merged = _merge_model(current, draft)

        # Null values in draft should not overwrite current
        assert merged["dollars_per_million_tokens_cache_read"] == 0.30
        assert merged["dollars_per_million_tokens_cache_write_5m"] == 3.75
        assert merged["dollars_per_million_tokens_cache_write_1h"] == 3.00
        assert merged["supports_vision"] is True
        assert merged["supports_function_calling"] is True

    def test_merge_model_updates_pricing_fields(self):
        """Pricing fields should be updated when draft has non-null values."""
        current = {
            "model_name": "gpt-4o",
            "provider": "openai",
            "dollars_per_million_tokens_input": 5.0,
            "dollars_per_million_tokens_output": 15.0,
            "dollars_per_million_tokens_cached_input": 2.5
        }
        draft = {
            "model_name": "gpt-4o",
            "provider": "openai",
            "dollars_per_million_tokens_input": 2.5,
            "dollars_per_million_tokens_output": 10.0,
            "dollars_per_million_tokens_cached_input": 1.25
        }

        merged = _merge_model(current, draft)

        assert merged["dollars_per_million_tokens_input"] == 2.5
        assert merged["dollars_per_million_tokens_output"] == 10.0
        assert merged["dollars_per_million_tokens_cached_input"] == 1.25

    def test_merge_model_updates_capability_fields(self):
        """Capability fields should be updated when draft has non-null values."""
        current = {
            "model_name": "gpt-4o",
            "provider": "openai",
            "supports_vision": False,
            "supports_function_calling": True,
            "supports_json_mode": False,
            "max_input_tokens": 100000,
            "max_output_tokens": 4096
        }
        draft = {
            "model_name": "gpt-4o",
            "provider": "openai",
            "supports_vision": True,
            "supports_function_calling": True,
            "supports_json_mode": True,
            "max_input_tokens": 128000,
            "max_output_tokens": 16384
        }

        merged = _merge_model(current, draft)

        assert merged["supports_vision"] is True
        assert merged["supports_function_calling"] is True
        assert merged["supports_json_mode"] is True
        assert merged["max_input_tokens"] == 128000
        assert merged["max_output_tokens"] == 16384

    def test_merge_model_adds_new_update_fields(self):
        """New UPDATE_FIELDS in draft should be added to merged result."""
        current = {
            "model_name": "claude-3-5-sonnet-20241022",
            "provider": "anthropic",
            "dollars_per_million_tokens_input": 3.0,
            "dollars_per_million_tokens_output": 15.0
        }
        draft = {
            "model_name": "claude-3-5-sonnet-20241022",
            "provider": "anthropic",
            "dollars_per_million_tokens_input": 3.0,
            "dollars_per_million_tokens_output": 15.0,
            # New fields not in current
            "dollars_per_million_tokens_cache_read": 0.30,
            "supports_thinking": True,
            "max_output_tokens": 8192
        }

        merged = _merge_model(current, draft)

        assert merged["dollars_per_million_tokens_cache_read"] == 0.30
        assert merged["supports_thinking"] is True
        assert merged["max_output_tokens"] == 8192

    def test_merge_model_preserves_all_current_fields(self):
        """All fields from current should be in merged result."""
        current = {
            "model_name": "gpt-4o",
            "provider": "openai",
            "display_name": "GPT-4o",
            "description": "Test model",
            "api_endpoint": "chat",
            "custom_field": "custom_value",
            "dollars_per_million_tokens_input": 5.0
        }
        draft = {
            "model_name": "gpt-4o",
            "provider": "openai",
            "dollars_per_million_tokens_input": 2.5
        }

        merged = _merge_model(current, draft)

        # All current fields should be present
        assert merged["model_name"] == "gpt-4o"
        assert merged["provider"] == "openai"
        assert merged["display_name"] == "GPT-4o"
        assert merged["description"] == "Test model"
        assert merged["api_endpoint"] == "chat"
        assert merged["custom_field"] == "custom_value"
        # Updated field
        assert merged["dollars_per_million_tokens_input"] == 2.5

    def test_merge_model_handles_missing_fields_in_draft(self):
        """Fields missing entirely from draft should be preserved from current."""
        current = {
            "model_name": "gpt-4o",
            "provider": "openai",
            "dollars_per_million_tokens_input": 5.0,
            "dollars_per_million_tokens_output": 15.0,
            "dollars_per_million_tokens_cached_input": 2.5,
            "supports_vision": True,
            "supports_function_calling": True,
            "max_input_tokens": 100000
        }
        draft = {
            "model_name": "gpt-4o",
            "provider": "openai",
            "dollars_per_million_tokens_input": 2.5
            # All other fields missing from draft
        }

        merged = _merge_model(current, draft)

        # Missing fields should be preserved from current
        assert merged["dollars_per_million_tokens_output"] == 15.0
        assert merged["dollars_per_million_tokens_cached_input"] == 2.5
        assert merged["supports_vision"] is True
        assert merged["supports_function_calling"] is True
        assert merged["max_input_tokens"] == 100000
        # Updated field
        assert merged["dollars_per_million_tokens_input"] == 2.5

    def test_merge_model_with_zero_values(self):
        """Zero values in draft should update (not treated as falsy)."""
        current = {
            "model_name": "test-model",
            "provider": "test",
            "dollars_per_million_tokens_input": 5.0,
            "dollars_per_million_tokens_output": 15.0,
            "max_temperature": 1.0
        }
        draft = {
            "model_name": "test-model",
            "provider": "test",
            "dollars_per_million_tokens_input": 0.0,  # Zero price
            "dollars_per_million_tokens_output": 0.0,  # Zero price
            "max_temperature": 0.0  # Zero temperature
        }

        merged = _merge_model(current, draft)

        # Zero values should be preserved (not treated as null)
        assert merged["dollars_per_million_tokens_input"] == 0.0
        assert merged["dollars_per_million_tokens_output"] == 0.0
        assert merged["max_temperature"] == 0.0

    def test_merge_model_with_false_values(self):
        """False boolean values in draft should update (not treated as falsy)."""
        current = {
            "model_name": "test-model",
            "provider": "test",
            "supports_vision": True,
            "supports_function_calling": True,
            "supports_json_mode": True
        }
        draft = {
            "model_name": "test-model",
            "provider": "test",
            "supports_vision": False,
            "supports_function_calling": False,
            "supports_json_mode": False
        }

        merged = _merge_model(current, draft)

        # False values should be preserved (not treated as null)
        assert merged["supports_vision"] is False
        assert merged["supports_function_calling"] is False
        assert merged["supports_json_mode"] is False


class TestMergeRegistry:
    """Tests for _merge_registry function."""

    def test_merge_registry_preserves_models_not_in_draft(self):
        """Models in current but not in draft should be preserved unchanged."""
        current = {
            "provider": "openai",
            "version": 5,
            "models": {
                "openai:gpt-4o": {
                    "model_name": "gpt-4o",
                    "provider": "openai",
                    "dollars_per_million_tokens_input": 5.0
                },
                "openai:gpt-4o-mini": {
                    "model_name": "gpt-4o-mini",
                    "provider": "openai",
                    "dollars_per_million_tokens_input": 0.15
                },
                "openai:gpt-4-turbo": {
                    "model_name": "gpt-4-turbo",
                    "provider": "openai",
                    "dollars_per_million_tokens_input": 10.0
                }
            }
        }
        draft = {
            "provider": "openai",
            "models": {
                "openai:gpt-4o": {
                    "model_name": "gpt-4o",
                    "provider": "openai",
                    "dollars_per_million_tokens_input": 2.5
                }
            }
        }

        merged = _merge_registry(current, draft)

        # All three models should be in merged result
        assert len(merged["models"]) == 3
        assert "openai:gpt-4o" in merged["models"]
        assert "openai:gpt-4o-mini" in merged["models"]
        assert "openai:gpt-4-turbo" in merged["models"]

        # Models not in draft should be unchanged
        assert merged["models"]["openai:gpt-4o-mini"]["dollars_per_million_tokens_input"] == 0.15
        assert merged["models"]["openai:gpt-4-turbo"]["dollars_per_million_tokens_input"] == 10.0

        # Model in draft should be updated
        assert merged["models"]["openai:gpt-4o"]["dollars_per_million_tokens_input"] == 2.5

    def test_merge_registry_adds_new_models(self):
        """Models in draft but not in current should be added."""
        current = {
            "provider": "openai",
            "version": 5,
            "models": {
                "openai:gpt-4o": {
                    "model_name": "gpt-4o",
                    "provider": "openai",
                    "dollars_per_million_tokens_input": 5.0
                }
            }
        }
        draft = {
            "provider": "openai",
            "models": {
                "openai:gpt-4o": {
                    "model_name": "gpt-4o",
                    "provider": "openai",
                    "dollars_per_million_tokens_input": 2.5
                },
                "openai:gpt-5": {
                    "model_name": "gpt-5",
                    "provider": "openai",
                    "dollars_per_million_tokens_input": 10.0,
                    "supports_vision": True
                }
            }
        }

        merged = _merge_registry(current, draft)

        # Should have both models
        assert len(merged["models"]) == 2
        assert "openai:gpt-4o" in merged["models"]
        assert "openai:gpt-5" in merged["models"]

        # New model should be added as-is
        assert merged["models"]["openai:gpt-5"]["model_name"] == "gpt-5"
        assert merged["models"]["openai:gpt-5"]["dollars_per_million_tokens_input"] == 10.0
        assert merged["models"]["openai:gpt-5"]["supports_vision"] is True

    def test_merge_registry_merges_existing_models(self):
        """Models in both current and draft should be merged."""
        current = {
            "provider": "anthropic",
            "version": 3,
            "models": {
                "anthropic:claude-3-5-sonnet-20241022": {
                    "model_name": "claude-3-5-sonnet-20241022",
                    "provider": "anthropic",
                    "display_name": "Claude 3.5 Sonnet",
                    "description": "Most intelligent model",
                    "dollars_per_million_tokens_input": 3.0,
                    "dollars_per_million_tokens_output": 15.0,
                    "supports_vision": True
                }
            }
        }
        draft = {
            "provider": "anthropic",
            "models": {
                "anthropic:claude-3-5-sonnet-20241022": {
                    "model_name": "claude-3-5-sonnet-20241022",
                    "provider": "anthropic",
                    "dollars_per_million_tokens_input": 3.0,
                    "dollars_per_million_tokens_output": 15.0,
                    "dollars_per_million_tokens_cache_read": 0.30,
                    "supports_function_calling": True
                }
            }
        }

        merged = _merge_registry(current, draft)

        model = merged["models"]["anthropic:claude-3-5-sonnet-20241022"]

        # Non-UPDATE_FIELDS should be preserved from current
        assert model["display_name"] == "Claude 3.5 Sonnet"
        assert model["description"] == "Most intelligent model"

        # UPDATE_FIELDS from current should be preserved
        assert model["supports_vision"] is True

        # UPDATE_FIELDS from draft should be added
        assert model["dollars_per_million_tokens_cache_read"] == 0.30
        assert model["supports_function_calling"] is True

    def test_merge_registry_updates_metadata_fields(self):
        """extraction_date and sources should be updated from draft."""
        current = {
            "provider": "openai",
            "version": 5,
            "extraction_date": "2025-10-15",
            "sources": ["https://openai.com/pricing"],
            "models": {}
        }
        draft = {
            "provider": "openai",
            "extraction_date": "2025-10-20",
            "sources": ["https://openai.com/pricing", "https://platform.openai.com/docs"],
            "models": {}
        }

        merged = _merge_registry(current, draft)

        assert merged["extraction_date"] == "2025-10-20"
        assert merged["sources"] == ["https://openai.com/pricing", "https://platform.openai.com/docs"]

    def test_merge_registry_preserves_other_top_level_fields(self):
        """Other top-level fields from current should be preserved."""
        current = {
            "provider": "openai",
            "version": 5,
            "updated_at": "2025-10-15T10:00:00Z",
            "custom_field": "custom_value",
            "models": {}
        }
        draft = {
            "provider": "openai",
            "models": {}
        }

        merged = _merge_registry(current, draft)

        assert merged["version"] == 5
        assert merged["updated_at"] == "2025-10-15T10:00:00Z"
        assert merged["custom_field"] == "custom_value"

    def test_merge_registry_handles_empty_current(self):
        """Merging into empty current should work correctly."""
        current = {
            "provider": "openai",
            "version": 0,
            "models": {}
        }
        draft = {
            "provider": "openai",
            "extraction_date": "2025-10-20",
            "sources": ["https://openai.com/pricing"],
            "models": {
                "openai:gpt-4o": {
                    "model_name": "gpt-4o",
                    "provider": "openai",
                    "dollars_per_million_tokens_input": 2.5
                }
            }
        }

        merged = _merge_registry(current, draft)

        assert len(merged["models"]) == 1
        assert "openai:gpt-4o" in merged["models"]
        assert merged["extraction_date"] == "2025-10-20"
        assert merged["sources"] == ["https://openai.com/pricing"]

    def test_merge_registry_handles_missing_models_key(self):
        """Handles case where current has no 'models' key."""
        current = {
            "provider": "openai",
            "version": 1
        }
        draft = {
            "provider": "openai",
            "models": {
                "openai:gpt-4o": {
                    "model_name": "gpt-4o",
                    "provider": "openai",
                    "dollars_per_million_tokens_input": 2.5
                }
            }
        }

        merged = _merge_registry(current, draft)

        assert len(merged["models"]) == 1
        assert "openai:gpt-4o" in merged["models"]

    def test_merge_registry_complex_scenario(self):
        """Complex scenario with adds, updates, and preserves."""
        current = {
            "provider": "openai",
            "version": 10,
            "updated_at": "2025-10-15T10:00:00Z",
            "extraction_date": "2025-10-15",
            "sources": ["https://openai.com/pricing"],
            "models": {
                "openai:gpt-4o": {
                    "model_name": "gpt-4o",
                    "provider": "openai",
                    "display_name": "GPT-4o",
                    "description": "Flagship multimodal model",
                    "api_endpoint": "chat",
                    "dollars_per_million_tokens_input": 5.0,
                    "dollars_per_million_tokens_output": 15.0,
                    "supports_vision": True,
                    "supports_function_calling": True,
                    "max_input_tokens": 100000
                },
                "openai:gpt-4o-mini": {
                    "model_name": "gpt-4o-mini",
                    "provider": "openai",
                    "display_name": "GPT-4o Mini",
                    "dollars_per_million_tokens_input": 0.15,
                    "dollars_per_million_tokens_output": 0.60
                },
                "openai:gpt-4-turbo": {
                    "model_name": "gpt-4-turbo",
                    "provider": "openai",
                    "display_name": "GPT-4 Turbo",
                    "dollars_per_million_tokens_input": 10.0,
                    "dollars_per_million_tokens_output": 30.0,
                    "is_active": False
                }
            }
        }
        draft = {
            "provider": "openai",
            "extraction_date": "2025-10-20",
            "sources": ["https://openai.com/pricing", "https://platform.openai.com/docs"],
            "models": {
                # Update gpt-4o pricing
                "openai:gpt-4o": {
                    "model_name": "gpt-4o",
                    "provider": "openai",
                    "dollars_per_million_tokens_input": 2.5,
                    "dollars_per_million_tokens_output": 10.0,
                    "dollars_per_million_tokens_cached_input": 1.25,
                    "max_input_tokens": 128000
                },
                # Add new model
                "openai:gpt-5": {
                    "model_name": "gpt-5",
                    "provider": "openai",
                    "dollars_per_million_tokens_input": 20.0,
                    "dollars_per_million_tokens_output": 60.0,
                    "supports_vision": True,
                    "supports_function_calling": True,
                    "is_reasoning_model": True
                }
                # Note: gpt-4o-mini and gpt-4-turbo not in draft
            }
        }

        merged = _merge_registry(current, draft)

        # All four models should be present
        assert len(merged["models"]) == 4
        assert "openai:gpt-4o" in merged["models"]
        assert "openai:gpt-4o-mini" in merged["models"]
        assert "openai:gpt-4-turbo" in merged["models"]
        assert "openai:gpt-5" in merged["models"]

        # gpt-4o: updated pricing, preserved metadata
        gpt4o = merged["models"]["openai:gpt-4o"]
        assert gpt4o["dollars_per_million_tokens_input"] == 2.5
        assert gpt4o["dollars_per_million_tokens_output"] == 10.0
        assert gpt4o["dollars_per_million_tokens_cached_input"] == 1.25
        assert gpt4o["max_input_tokens"] == 128000
        assert gpt4o["display_name"] == "GPT-4o"
        assert gpt4o["description"] == "Flagship multimodal model"
        assert gpt4o["api_endpoint"] == "chat"
        assert gpt4o["supports_vision"] is True
        assert gpt4o["supports_function_calling"] is True

        # gpt-4o-mini: unchanged
        mini = merged["models"]["openai:gpt-4o-mini"]
        assert mini["display_name"] == "GPT-4o Mini"
        assert mini["dollars_per_million_tokens_input"] == 0.15
        assert mini["dollars_per_million_tokens_output"] == 0.60

        # gpt-4-turbo: unchanged
        turbo = merged["models"]["openai:gpt-4-turbo"]
        assert turbo["display_name"] == "GPT-4 Turbo"
        assert turbo["dollars_per_million_tokens_input"] == 10.0
        assert turbo["dollars_per_million_tokens_output"] == 30.0
        assert turbo["is_active"] is False

        # gpt-5: new model added
        gpt5 = merged["models"]["openai:gpt-5"]
        assert gpt5["model_name"] == "gpt-5"
        assert gpt5["dollars_per_million_tokens_input"] == 20.0
        assert gpt5["dollars_per_million_tokens_output"] == 60.0
        assert gpt5["supports_vision"] is True
        assert gpt5["supports_function_calling"] is True
        assert gpt5["is_reasoning_model"] is True

        # Metadata should be updated
        assert merged["extraction_date"] == "2025-10-20"
        assert merged["sources"] == ["https://openai.com/pricing", "https://platform.openai.com/docs"]

        # Other top-level fields should be preserved
        assert merged["version"] == 10
        assert merged["updated_at"] == "2025-10-15T10:00:00Z"
