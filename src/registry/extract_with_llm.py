#!/usr/bin/env python3
"""LLM-based extraction from HTML pricing pages.

This module uses LLMs to extract model information from HTML pages,
avoiding brittle regex patterns that break when providers update their sites.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Any
import click

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Try to find .env in current directory or parent directories
    for path in [Path.cwd(), Path.cwd().parent, Path("/Users/juanre/prj/llmring-all/llmring")]:
        env_file = path / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            break
except ImportError:
    pass

logger = logging.getLogger(__name__)


async def extract_models_from_html(provider: str, html_content: str) -> List[Dict[str, Any]]:
    """
    Extract model information from HTML using an LLM.
    
    Args:
        provider: Provider name (openai, anthropic, google)
        html_content: Raw HTML content from pricing page
    
    Returns:
        List of extracted model dictionaries
    """
    try:
        import os
        from llmring import LLMRing
        from llmring.schemas import LLMRequest, Message
        
        # Make sure we have API keys
        if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
            logger.error("No API keys found. Set OPENAI_API_KEY or ANTHROPIC_API_KEY")
            return []
        
        service = LLMRing()
        
        # Check available models
        available_models = service.get_available_models()
        if not available_models:
            logger.error("No models available in LLMRing")
            return []
        
        # Pick the best available model
        model = None
        for provider_models in available_models.values():
            if provider_models:
                model = provider_models[0]
                break
        
        if not model:
            logger.error("No suitable model found")
            return []
        
        # Create extraction prompt
        prompt = f"""Extract all AI model pricing information from this {provider} pricing page HTML.

For each model found, extract:
- model_name: The API identifier (e.g., "gpt-4o", "claude-opus-4.1", "gemini-1.5-flash")
- display_name: Human-friendly name (e.g., "GPT-4o", "Claude Opus 4.1")
- description: Brief description of the model's strengths
- dollars_per_million_tokens_input: Input price per million tokens (convert if needed)
- dollars_per_million_tokens_output: Output price per million tokens (convert if needed)
- max_input_tokens: Maximum input context length (if mentioned)
- max_output_tokens: Maximum output length (if mentioned)
- supports_vision: Whether it supports image inputs (true/false)
- supports_function_calling: Whether it supports function calling (true/false)
- supports_json_mode: Whether it supports JSON output mode (true/false)
- supports_parallel_tool_calls: Whether it supports parallel tool calls (true/false)

Important:
1. Extract ONLY actual models with pricing, not plans or subscriptions
2. Convert all prices to dollars per million tokens
3. If a capability is not mentioned, use reasonable defaults based on the model family
4. Return ONLY a JSON array of model objects, no other text

HTML content:
{html_content[:50000]}  # Limit to avoid token limits
"""
        
        request = LLMRequest(
            messages=[Message(role="user", content=prompt)],
            model=model,
            temperature=0,
            max_tokens=4000
        )
        
        response = await service.chat(request)
        
        # Parse response - handle markdown-wrapped JSON
        try:
            content = response.content.strip()
            
            # Remove markdown code block markers if present
            if content.startswith("```json"):
                content = content[7:]  # Remove ```json
                if content.endswith("```"):
                    content = content[:-3]  # Remove trailing ```
                content = content.strip()
            elif content.startswith("```"):
                content = content[3:]  # Remove ```
                if content.endswith("```"):
                    content = content[:-3]  # Remove trailing ```
                content = content.strip()
            
            result = json.loads(content)
            if isinstance(result, dict) and "models" in result:
                models = result["models"]
            else:
                models = result if isinstance(result, list) else []
        except json.JSONDecodeError:
            logger.error(f"Failed to parse LLM response as JSON: {response.content[:500]}")
            models = []
        
        # Add provider field to each model
        for model in models:
            if "provider" not in model:
                model["provider"] = provider
        
        return models
        
    except ImportError:
        logger.error("LLMRing not available. Install with: uv add llmring")
        return []
    except Exception as e:
        logger.error(f"LLM extraction failed: {e}")
        return []


async def validate_extracted_models(models: List[Dict[str, Any]], provider: str) -> List[Dict[str, Any]]:
    """
    Validate extracted models using a second LLM pass.
    
    This helps catch extraction errors and ensures consistency.
    """
    if not models:
        return models
    
    try:
        import os
        from llmring import LLMRing
        from llmring.schemas import LLMRequest, Message
        
        if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
            return models  # Skip validation if no API keys
        
        service = LLMRing()
        
        # Get best available model
        available_models = service.get_available_models()
        model = None
        for provider_models in available_models.values():
            if provider_models:
                model = provider_models[0]
                break
        
        if not model:
            return models
        
        # Create validation prompt
        prompt = f"""Validate and correct this extracted model data for {provider}.

Models to validate:
{json.dumps(models, indent=2)}

Please review each model and:
1. Fix any obvious pricing errors (e.g., prices that are off by 1000x)
2. Ensure model names match {provider}'s actual API identifiers
3. Add reasonable defaults for missing capability flags based on the model family
4. Remove any models that aren't actually API-accessible models
5. Ensure prices are in dollars per million tokens

Known patterns:
- OpenAI: gpt-4o, gpt-4o-mini, gpt-3.5-turbo, etc.
- Anthropic: claude-opus-4.1, claude-sonnet-4, claude-haiku-3.5, etc.
- Google: gemini-1.5-flash, gemini-1.5-pro, etc.

Return the corrected JSON array of models."""
        
        request = LLMRequest(
            messages=[Message(role="user", content=prompt)],
            model=model,
            temperature=0,
            max_tokens=4000
        )
        
        response = await service.chat(request)
        
        # Parse response - handle markdown-wrapped JSON
        try:
            content = response.content.strip()
            
            # Remove markdown code block markers if present
            if content.startswith("```json"):
                content = content[7:]  # Remove ```json
                if content.endswith("```"):
                    content = content[:-3]  # Remove trailing ```
                content = content.strip()
            elif content.startswith("```"):
                content = content[3:]  # Remove ```
                if content.endswith("```"):
                    content = content[:-3]  # Remove trailing ```
                content = content.strip()
            
            result = json.loads(content)
            if isinstance(result, dict) and "models" in result:
                validated = result["models"]
            else:
                validated = result if isinstance(result, list) else []
            
            return validated
        except json.JSONDecodeError:
            logger.error("Validation LLM response was not valid JSON")
            return models  # Return original if validation fails
            
    except Exception as e:
        logger.error(f"Model validation failed: {e}")
        return models  # Return original if validation fails


@click.command()
@click.option(
    "--provider",
    type=click.Choice(["openai", "anthropic", "google", "all"]),
    default="all",
    help="Provider to extract"
)
@click.option(
    "--html-dir",
    default="html_cache",
    type=click.Path(exists=True),
    help="Directory containing HTML files"
)
@click.option(
    "--models-dir", 
    default="models",
    type=click.Path(),
    help="Directory to save extracted models"
)
@click.option(
    "--validate/--no-validate",
    default=True,
    help="Run validation pass on extracted models"
)
def extract_with_llm(provider, html_dir, models_dir, validate):
    """
    Extract models from HTML using LLM-based extraction.
    
    This is more robust than regex patterns as it adapts to HTML structure changes.
    """
    import asyncio
    from datetime import datetime
    
    async def run_extraction():
        providers = [provider] if provider != "all" else ["openai", "anthropic", "google"]
        html_path = Path(html_dir)
        models_path = Path(models_dir)
        models_path.mkdir(exist_ok=True)
        
        for prov in providers:
            click.echo(f"\n🤖 Extracting {prov} models using LLM...")
            
            # Find HTML files for this provider
            html_files = list(html_path.glob(f"*{prov}*.html"))
            if not html_files:
                click.echo(f"  ⚠️  No HTML files found for {prov}")
                continue
            
            all_models = []
            
            for html_file in html_files:
                click.echo(f"  📄 Processing {html_file.name}")
                
                with open(html_file, "r", encoding="utf-8") as f:
                    html_content = f.read()
                
                # Extract models using LLM
                models = await extract_models_from_html(prov, html_content)
                
                if models:
                    all_models.extend(models)
                    click.echo(f"     Found {len(models)} models")
                else:
                    click.echo(f"     No models extracted")
            
            if all_models:
                # Remove duplicates based on model_name
                unique_models = {}
                for model in all_models:
                    model_name = model.get("model_name")
                    if model_name:
                        unique_models[model_name] = model
                
                final_models = list(unique_models.values())
                
                # Validate if requested
                if validate:
                    click.echo(f"  🔍 Validating {len(final_models)} models...")
                    final_models = await validate_extracted_models(final_models, prov)
                    click.echo(f"     Validation complete")
            
                # Convert to dictionary format for O(1) lookup
                models_dict = {}
                for model in final_models:
                    model_name = model.get("model_name")
                    if model_name:
                        model_key = f"{prov}:{model_name}"
                        model["provider"] = prov
                        models_dict[model_key] = model
                
                # Create output data
                output_data = {
                    "provider": prov,
                    "last_updated": datetime.now().strftime("%Y-%m-%d"),
                    "source": "llm_extraction",
                    "extraction_date": datetime.now().isoformat(),
                    "models": models_dict,
                }
                
                # Save to JSON
                output_file = models_path / f"{prov}.json"
                with open(output_file, "w") as f:
                    json.dump(output_data, f, indent=2)
                
                click.echo(f"  ✅ Saved {len(models_dict)} models to {output_file}")
            else:
                click.echo(f"  ⚠️  No models extracted for {prov}")
        
        click.echo("\n✨ LLM extraction complete")
        click.echo("   Use 'llmring-registry validate' to check the data")
        click.echo("   Use 'llmring-registry list' to view all models")
    
    # Run the async function
    asyncio.run(run_extraction())


if __name__ == "__main__":
    extract_with_llm()