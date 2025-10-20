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

## Updating Model Data

The easiest way to contribute model updates is using the Claude-guided workflow:

### With Claude Code

```
In Claude Code:
> Update the {provider} registry

Follow Claude's guidance through the complete workflow.
```

### Manually

1. **Save source documentation**:
   - Visit provider's model documentation page
   - Save as markdown to `sources/{provider}/YYYY-MM-DD-models.md`

2. **Create draft JSON**:
   - Extract model information following the schema in `.claude/skills/update-registry/SKILL.md`
   - Save to `drafts/{provider}.YYYY-MM-DD.draft.json`

3. **Review and promote**:
   ```bash
   uv run llmring-registry review-draft --provider {provider}
   uv run llmring-registry promote --provider {provider}
   ```

4. **Submit PR** with:
   - Source documentation
   - Draft JSON
   - Updated production files
   - Clear commit message describing changes

### Adding a New Provider

To add support for a new LLM provider:

1. **Create directory structure**:
   ```bash
   mkdir -p sources/newprovider
   mkdir -p pages/newprovider
   ```

2. **Save documentation**:
   - Save provider's model docs to `sources/newprovider/YYYY-MM-DD-models.md`

3. **Extract models** (using Claude or manually):
   - Follow the registry schema
   - Create `drafts/newprovider.YYYY-MM-DD.draft.json`

4. **Promote and test**:
   ```bash
   uv run llmring-registry promote --provider newprovider
   uv run llmring-registry stats --provider newprovider
   ```

5. **Submit PR** with:
   - Source documentation
   - Extracted models
   - Example showing data quality
   - Updated documentation

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/registry.git
cd registry

# Install dependencies
uv sync

# Verify CLI works
uv run llmring-registry --help
```

## Testing

```bash
# Run all tests
uv run pytest

# Test specific functionality
uv run pytest -k "test_promote"

# Verbose output
uv run pytest -v
```

## Code Style

- Use Black for Python formatting
- Follow PEP 8 guidelines
- Add type hints where possible
- Document functions and classes
- Keep functions focused and small

## Commit Messages

Use clear, descriptive commit messages:

```
Update OpenAI models - 2025-10-20

Added new models:
- GPT-5 (gpt-5-2025-08-07)
- GPT-5 Mini (gpt-5-mini-2025-08-07)

Updated pricing:
- GPT-4o: $2.50 → $2.00 per MTok output
```

## Architecture Decisions

### Why Claude-Guided Extraction?

The registry uses an interactive Claude-guided workflow instead of automated extraction for several reasons:

1. **Accuracy**: Claude can reason about edge cases and ambiguities
2. **Simplicity**: No complex voting/merging pipeline
3. **Debuggability**: See extraction happen in real-time
4. **Flexibility**: Handle provider-specific quirks interactively

### Smart Merge Logic

When promoting drafts, the system preserves existing production data:
- Only updates fields where draft has non-null values
- Keeps existing metadata when draft doesn't provide it
- Prevents accidental data loss

## Priority Areas

We especially welcome contributions in these areas:

- **New Providers**: Cohere, AI21, Replicate, Together AI, etc.
- **Schema Enhancements**: New capability flags, pricing models
- **Testing**: Unit and integration tests
- **Documentation**: Guides, examples, troubleshooting tips

## Questions?

Feel free to open an issue for discussion or reach out to the maintainers.

Thank you for contributing!
