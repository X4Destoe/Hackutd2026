# Module: ai (`backend/app/modules/ai/`)

**Skills:** ai-integration, python · **Read also:** `01-architecture.md` §4

## Job
One provider-agnostic LLM gateway (Claude, OpenAI or Gemini, picked by `LLM_PROVIDER`) with **template fallbacks**,
so the demo never depends on a key or the network. No other module imports an LLM SDK.

## Owns
`backend/app/modules/ai/**`

## Interface (`__init__.py`)
```python
def provider_name() -> str                                  # "anthropic:<model>" | ... | "templates"
def classify_need(text: str, language_hint: str = "en") -> dict
    # {"needs": [NeedType], "people": int, "urgent": bool, "language": "en|es|vi", "summary": "<=100 chars English"}
def compose(purpose: str, facts: dict, language: str = "en") -> str
    # purpose: "task" | "tenant_notice" | "redirect" | "reroute" | "ack" | "exec_summary_intro"; SMS outputs <= 320 chars
def rationale(facts: dict) -> str                           # 1–2 sentences: why this plan, in dollars
def write_report(kind: str, facts: dict) -> str              # markdown body for reports (template fallback)
```
- Providers sit behind one `Provider` protocol (`json(system, user, schema, timeout)`, `text(system, user, max_chars, timeout)`).
  SDKs are lazy-imported. Model IDs live in one dict (the implementer picks current IDs from the provider docs). 6s timeout, then fallback.
- **Fallbacks are required and tested:**
  - Need classification uses en/es/vi keywords (flood/inundado/ngập → shelter; cold/frío/lạnh/no heat → warmth; claim/reclamo → claim;
    repair/roof/techo/pipe → repair; hurt/injured/herido/oxygen → medical + urgent; food/water/agua → food_water) and digits near
    "kids/people/niños/personas" for people count.
  - Compose and report use `str.format` templates per purpose (en/es/vi for resident messages, English for the rest).

## Acceptance (pytest with `LLM_PROVIDER=none`)
- `classify_need("our apartment flooded, 2 kids, need a dry place")` → needs ∋ shelter, people 3 (2 kids + sender), urgent False.
- `classify_need("mi papá usa oxígeno y no hay luz")` → medical, urgent True, language "es".
- `compose("redirect", facts, "es")` ≤ 320 chars and contains the site address verbatim.
- With a provider set but the network blocked, it falls back within 6s.
