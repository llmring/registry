# Contributing to LLMRing Registry

Thank you for your interest in contributing to the LLMRing Registry! This document provides guidelines for contributing to the project.

## Code of Conduct

Please be respectful and constructive in all interactions. We aim to maintain a welcoming environment for all contributors.

## How to Contribute

### Reporting Issues

- Check existing issues first
- Provide clear reproduction steps
- Include relevant logs and error messages
- Specify your environment (OS, Python version, etc.)

### Submitting Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Add tests if applicable
5. Run tests locally (`uv run pytest`)
6. Commit with descriptive messages
7. Push to your fork
8. Open a pull request

### Adding a New Provider

To add support for a new LLM provider:

1. **Add provider URLs** in `src/registry/fetch_html.py`:
```python
PROVIDER_URLS = {
    "newprovider": {
        "pricing": "https://...",
        "models": "https://..."
    }
}
```

2. **Create extraction function** in `src/registry/extract_from_html.py`:
```python
def extract_newprovider_models(html: str) -> List[Dict[str, Any]]:
    # Your extraction logic here
    pass
```

3. **Test the extraction**:
```bash
uv run registry fetch-html --provider newprovider
uv run registry extract-comprehensive --provider newprovider
```

4. **Submit a PR** with:
   - The new extraction code
   - Test data (sample HTML)
   - Updated documentation

### Improving Extraction Patterns

If you notice incorrect or missing data:

1. Identify the specific field/model affected
2. Locate the extraction pattern in `extract_from_html.py`
3. Update the regex pattern
4. Test against current HTML
5. Ensure no regressions for other models

### Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/registry.git
cd registry

# Install dependencies
uv sync

# Set up pre-commit hooks (optional)
pre-commit install
```

### Testing

```bash
# Run all tests
uv run pytest

# Test specific provider
uv run pytest -k "test_openai"

# Test extraction
uv run registry extract-comprehensive --provider openai --interactive
```

### Code Style

- Use Black for Python formatting
- Follow PEP 8 guidelines
- Add type hints where possible
- Document functions and classes
- Keep functions focused and small

### Commit Messages

Use clear, descriptive commit messages:
- `feat: Add support for Cohere models`
- `fix: Correct GPT-4 pricing extraction`
- `docs: Update README with new commands`
- `refactor: Simplify HTML parsing logic`

## Priority Areas

We especially welcome contributions in these areas:

- **New Providers**: Cohere, AI21, Replicate, etc.
- **Extraction Accuracy**: Improving regex patterns
- **Embedding Models**: Adding support for embedding model extraction
- **Testing**: Adding unit and integration tests
- **Documentation**: Improving guides and examples

## Questions?

Feel free to open an issue for discussion or reach out to the maintainers.

Thank you for contributing!