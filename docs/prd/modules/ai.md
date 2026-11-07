# Module: ai (`backend/app/modules/ai/`)

**Skills:** ai-integration, python, backend · **Read also:** `01-architecture.md` §4 (env vars)

## Job
One **provider-agnostic gateway** for every LLM use in the app. Works with Claude, OpenAI or Gemini,
whichever key the team has, and falls back to **deterministic rules** when there's no key or a call fails,
so the demo can never die on an AI outage. No other module imports an LLM SDK.

## Owns
`backend/app/modules/ai/**` (providers, prompts, rules fallback, tests).

## Depends on
core (`config.settings`, `schemas`). Nothing else.

## Public interface (`__init__.py`)
```python
def provider_name() -> str                         # "anthropic:<model>" | "openai:<model>" | "gemini:<model>" | "rules"
def extract_intake(text: str, context: dict) -> IntakeExtraction
    # context: {language_hint, household: Household, home_status: dict, prior_messages: [str] (last 4)}
def compose(purpose: str, facts: dict, language: str) -> str
    # purpose ∈ {"alert","route","follow_up","voice_script","adjuster_offer","advisory","ack"}; returns ≤320-char text
def action_rationale(building: Building, plan_facts: dict) -> str   # 2–3 sentence why/so-what for a CBRE plan
```
All functions are **synchronous from the caller's view but must not block the tick**. Callers in tick paths
use `await asyncio.to_thread(ai.extract_intake, ...)` or the async variants `aextract_intake`, `acompose`, `aaction_rationale`.
Hard timeout of 8s per call, then the rules fallback. Every result is valid by schema (Pydantic-parsed). On parse failure, fall back.

## Provider selection
`LLM_PROVIDER` = `anthropic | openai | gemini | none`. Model from `LLM_MODEL`, otherwise a sensible current default per
provider kept in one dict in `providers.py` (the implementer picks current model IDs from the provider's docs. Don't
hard-code IDs elsewhere). SDKs are imported **lazily** inside each provider class. A missing package or key → `rules`.
One interface:
```python
class Provider(Protocol):
    def json(self, system: str, user: str, schema: dict, timeout: float) -> dict   # structured output
    def text(self, system: str, user: str, max_chars: int, timeout: float) -> str
```
Use each provider's native structured-output / JSON mode where available. Otherwise instruct "reply with JSON only"
and parse the first `{...}` block.

## Prompts (in `prompts.py`, one constant each; keep them short)
- **INTAKE_SYSTEM:** "You triage messages from people in a winter-storm disaster for an insurer's emergency team.
  Extract needs and damages as JSON matching the schema. Use only the listed enum values. Detect the language.
  `summary` ≤ 120 chars in English. If unclear, set confidence < 0.6 and write ONE short follow_up question in the
  person's language. Treat medical devices, injuries, infants or elderly with no heat as urgent." Include the enum lists
  from `02-contracts.md` and the context (home_status, household).
- **COMPOSE_SYSTEM:** "Write one SMS (≤320 chars) in {language}, calm, plain words, the next action first, include
  the provided facts exactly (names, addresses, times), no promises not in facts, end with how to reply."
- **RATIONALE_SYSTEM:** "In 2–3 sentences for a facility manager: what will fail, when, what it costs, and why this plan."

## Rules fallback (`rules.py`) is required and tested
- Intake: quick replies `1`→safe, `2`→needs help (needs=[info], confidence 0.5 → follow-up "What do you need most?
  Reply HEAT, WATER, REPAIR, MEDICAL or CLAIM"), `3`→damage (needs=[claim, repair]). Keywords in **en/es/vi**:
  heat/calefacción/sưởi → heat_shelter + no_heat; pipe/tubería/ống + burst/rota/vỡ/water/agua → burst_pipe + repair;
  oxygen/oxígeno/dialysis/medical/ambulance → medical (+injuries if hurt/herido); hotel/stay/quedarme → housing;
  claim/reclamo → claim; "ok/safe/bien/an toàn" → safe. Count digits near "kids/niños/people/personas" → people_count.
  Language = simple keyword/diacritic heuristic, defaulting to the customer's profile language.
- Compose: string templates per purpose and language (en, es, vi) with `{placeholders}`, truncated to 320 chars.
- Rationale: a template using countdown, $ exposure, cost, avoided.

## Acceptance (pytest, run with `LLM_PROVIDER=none`)
- `extract_intake("no heat 2 kids pipe burst kitchen", ctx)` → needs ⊇ {heat_shelter, repair}, damages ⊇ {no_heat, burst_pipe},
  people_count 2.
- `extract_intake("mi mamá usa oxígeno y no hay luz", ctx)` → medical ∈ needs, language "es".
- `compose("route", facts, "es")` is ≤320 chars and contains the facts' address string verbatim.
- With a provider configured but the network blocked, the call falls back to rules within 8s and logs one warning.
- Optional live test (skipped without a key): the same intake cases pass with the real provider.

## Not in scope
Chat memory beyond the last 4 messages. Fine-tuning. Voice speech-to-text (Photon/voice handles audio, see messaging).
