# Registry Deployment Plan

## Current State Analysis

### Working Components
✅ LLM-based PDF extraction via LLMRing
✅ HTML extraction for OpenAI (finding GPT-5 models)  
✅ Dual extraction with confidence scoring
✅ Manual curation workflow (`review-draft` → `promote`)
✅ Proper dictionary schema with `provider:model` keys
✅ GitHub Actions workflow (fixed command names)

### Critical Issues
❌ No curated models in `pages/` directory (deployment source)
❌ `extract-with-versioning` uses hardcoded data instead of actual extraction
❌ Anthropic HTML extraction broken (0 models extracted)
❌ GitHub Pages not enabled/configured
❌ No integration or end-to-end tests

## Pre-Deployment Checklist

### Phase 1: Create Initial Curated Models (REQUIRED)
```bash
# 1. Fetch latest HTML
uv run llmring-registry fetch-html --provider all

# 2. Extract using comprehensive method (if you have API keys)
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
uv run llmring-registry extract-comprehensive --provider all

# OR extract from HTML only
uv run llmring-registry extract-html --provider all

# 3. Review each provider's draft
uv run llmring-registry review-draft \
  --provider openai \
  --draft models/openai.json \
  --accept-all

# 4. Promote to pages directory
uv run llmring-registry promote \
  --provider openai \
  --reviewed models/openai.json
```

### Phase 2: Fix Extraction Issues
1. **Fix Anthropic HTML patterns** in `extract_from_html.py`:
   - Current patterns not matching their HTML structure
   - Need to update regex for Claude 3.5 Sonnet/Haiku

2. **Fix extract-with-versioning.py**:
   - Remove hardcoded models (lines 28-130)
   - Use actual PDF extraction from `extraction/pdf_parser.py`

3. **Add missing models**:
   - GPT-4o-mini not being extracted
   - Verify all current models from each provider

### Phase 3: Enable GitHub Pages
```yaml
# Repository Settings > Pages
Source: Deploy from a branch
Branch: main
Folder: /pages
```

Then verify:
```bash
curl https://llmring.github.io/registry/manifest.json
curl https://llmring.github.io/registry/openai/models.json
```

### Phase 4: Add Testing
```python
# tests/test_extraction.py
def test_openai_html_extraction():
    """Test OpenAI HTML extraction finds expected models."""
    html = load_fixture("openai_pricing.html")
    models = extract_openai_models(html)
    assert len(models) > 0
    assert any(m["model_id"] == "gpt-5" for m in models)

def test_comprehensive_extraction():
    """Test dual extraction and confidence scoring."""
    # Test that HTML and PDF agreement → certain
    # Test that single source → probable
    # Test that conflict → uncertain

def test_registry_schema():
    """Test output matches expected schema."""
    # Verify dictionary format
    # Verify required fields
    # Verify provider:model keys
```

### Phase 5: Documentation
Create `MANUAL_CURATION.md`:
```markdown
# Manual Curation Process

## Weekly Review Process
1. Check for provider pricing page updates
2. Run comprehensive extraction
3. Review diffs using `review-draft`
4. Validate against actual API responses
5. Promote reviewed files
6. Commit to pages/ directory

## Validation Checklist
- [ ] Model IDs match API exactly
- [ ] Prices in dollars per million tokens
- [ ] Context windows accurate
- [ ] Capabilities verified (vision, functions, etc.)
- [ ] No deprecated models included
```

## Deployment Steps

### 1. Bootstrap Initial Registry
```bash
# Create initial curated models for each provider
for provider in openai anthropic google; do
  # Create draft from current extraction
  uv run llmring-registry extract-html --provider $provider
  
  # Review and promote
  uv run llmring-registry review-draft \
    --provider $provider \
    --draft models/$provider.json \
    --current pages/$provider/models.json \
    --accept-all \
    --output reviewed/$provider.json
    
  uv run llmring-registry promote \
    --provider $provider \
    --reviewed reviewed/$provider.json
done
```

### 2. Create Manifest
```bash
python -c "
import json
from datetime import datetime
from pathlib import Path

manifest = {
    'version': '1.0',
    'updated_at': datetime.now().isoformat() + 'Z',
    'providers': ['openai', 'anthropic', 'google'],
    'schema_version': '3.5',
    'registry_url': 'https://llmring.github.io/registry/'
}

Path('pages/manifest.json').write_text(json.dumps(manifest, indent=2))
"
```

### 3. Commit and Deploy
```bash
git add pages/
git commit -m "Initial curated model registry

- OpenAI: GPT-5, GPT-5-mini, GPT-5-nano, GPT-4o
- Anthropic: Claude 3.5 Sonnet, Claude 3.5 Haiku
- Google: Gemini 1.5 Flash, Gemini 1.5 Flash-8B

Schema version 3.5 with dictionary format for O(1) lookup"
git push
```

### 4. Verify Deployment
```bash
# Wait 5 minutes for GitHub Pages to deploy
sleep 300

# Test registry access
curl -s https://llmring.github.io/registry/manifest.json | jq .
curl -s https://llmring.github.io/registry/openai/models.json | jq '.models | keys'

# Test with llmring
python -c "
from llmring import LLMRing
ring = LLMRing(registry_url='https://llmring.github.io/registry')
print(ring.get_available_models())
"
```

## Post-Deployment Monitoring

### Daily GitHub Actions
- Fetches HTML from providers
- Extracts models
- Creates draft if changes detected
- Requires manual review before publishing

### Weekly Manual Review
- Check extraction diffs
- Validate against provider docs
- Update patterns if HTML changed
- Promote validated models

### Metrics to Track
- Extraction success rate
- Number of models per provider
- Price changes over time
- New model additions
- Deprecation notices

## Success Criteria

- [ ] Registry accessible at https://llmring.github.io/registry/
- [ ] All three providers have curated models
- [ ] GitHub Actions runs daily without errors
- [ ] LLMRing can fetch and use registry
- [ ] Manual curation process documented
- [ ] Version history preserved in v/ directories