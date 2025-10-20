
## 2025-10-20: Google Registry Update - In Progress

**Task:** Update Google model registry using update-registry skill

**Context:**
- Juan saved 13 screenshots of Google Gemini model documentation
- Screenshots located in: `sources/google/Screenshot 2025-10-20 at 19.*.png`
- Total size: ~3MB across 13 files
- Screenshots contain: model capabilities, token limits, pricing (including cache pricing, live API, audio pricing)

**Approach Decision:**
- Considered: Using extraction agent to save context
- Decided: Read screenshots directly
- Reason: Only ~22K tokens (2.2% of context) - very efficient, and I can verify accuracy directly
- Token estimate: 13 screenshots × 1,700 tokens/screenshot = ~22,000 tokens

**Models visible so far:**
- Gemini 2.5 Pro (gemini-2.5-pro) - 1M input, 65K output, has pricing
- Gemini 2.0 Flash (gemini-2.0-flash) - 1M context, has detailed pricing table

**Next steps:**
1. Read all 13 screenshots in parallel
2. Extract model information to draft JSON
3. Review against production
4. Promote and commit

**Key extraction notes to remember:**
- Google has tiered pricing (Free vs Paid tiers)
- Use PAID tier pricing for registry
- Watch for audio pricing (different from text/image/video)
- Cache storage pricing exists
- Live API has separate pricing
- Context window = max_input + max_output (calculate correctly!)


**CRITICAL GOOGLE-SPECIFIC RULE:**
- Google shows Free Tier and Paid Tier pricing side-by-side
- **ALWAYS use Paid Tier pricing for the registry** (ignore Free Tier)
- Paid Tier column says "Paid Tier, per 1M tokens in USD"
- Free Tier is for evaluation/testing only - not production usage


**Extraction Complete - 2025-10-20:**

Models extracted (5 total):
1. **google:gemini-2.5-pro** (NEW)
   - Input: 1,048,576 tokens, Output: 65,536 tokens
   - Pricing: $1.25/$10.00 (base), $2.50/$15.00 (>200k tokens)
   - Tiered pricing for prompts >200k tokens
   - Cache read: $0.125, Storage: $4.50/1M/hour
   - Supports: Vision, PDF, Function calling, Caching, Thinking, Structured outputs

2. **google:gemini-2.5-flash** (NEW)
   - Input: 1,048,576 tokens, Output: 65,536 tokens
   - Pricing: $0.30/$2.50 (includes thinking tokens in output)
   - "First hybrid reasoning model with 1M context and thinking budgets"
   - Cache read: $0.03, Storage: $1.00/1M/hour
   - Marked as is_reasoning_model: true
   - Supports: Vision, Audio, PDF, Function calling, Caching, Thinking

3. **google:gemini-2.5-flash-lite** (NEW)
   - Input: 1,048,576 tokens, Output: 65,536 tokens
   - Pricing: $0.10/$0.40
   - "Smallest and most cost effective model"
   - Cache read: $0.025, Storage: $1.00/1M/hour
   - Supports: Vision, Audio, PDF, Function calling, Caching, Thinking

4. **google:gemini-2.0-flash** (UPDATE)
   - Input: 1,048,576 tokens, Output: 8,192 tokens (smaller output than 2.5!)
   - Pricing: $0.10/$0.40
   - Cache read: $0.025, Storage: $1.00/1M/hour
   - Thinking: Experimental only (not full support) - set to false
   - Supports: Vision, Audio, PDF, Function calling, Caching

5. **google:gemini-2.0-flash-lite** (UPDATE)
   - Input: 1,048,576 tokens, Output: 8,192 tokens
   - Pricing: $0.075/$0.30
   - NO caching support at all
   - NO code execution, NO grounding, NO thinking, NO URL context
   - More limited than current registry shows

**Key decisions made:**
- Used PAID TIER pricing only (as documented in skill)
- Set Gemini 2.5 Flash as is_reasoning_model: true (first hybrid reasoning model)
- Gemini 2.0 Flash: Set thinking to false (only "Experimental" support, not production-ready)
- Gemini 2.5 Pro: Used long_context pricing fields for >200k token tier
- Audio pricing not captured (would need separate fields - out of scope for now)
- Live API pricing not captured (special feature, not standard input/output)

**Context usage:** ~60K tokens total (6% of budget) - very efficient!

