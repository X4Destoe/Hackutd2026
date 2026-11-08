# AI public interface
Import `from app.modules import ai`. No router or startup registration is required.

- `provider_name()`: configured provider/model when a key exists, otherwise `templates`; not a network health check.
- `classify_need(text, language_hint="en")`: contract need enum values, positive people count, urgency, en/es/vi language, English summary up to 100 characters. Children include sender; explicit people totals take precedence. Medical keywords always imply urgency.
- `compose(purpose, facts, language="en")`: at most 320 characters. Purposes: task, tenant_notice, redirect, reroute, ack, exec_summary_intro. Routing facts: site_name (resource_name/name aliases), address, details. Tasks: work_order_id, building_name, task_text. Tenant notices: building_name, notice (tenant_notice_text/text aliases). Intro: summary. Unknown purposes or required facts exceeding SMS limit raise ValueError. Address is never truncated.
- `rationale(facts)`: cost_cents and avoided_cents rendered as compact dollars ($24k / $980k).
- `write_report(kind, facts)`: executive_summary or tenant_notice Markdown; money keys ending _cents render as dollars. Consumers sanitize Markdown before rendering HTML.

LLM_PROVIDER selects none/anthropic/openai/gemini; LLM_MODEL overrides centralized defaults. Optional SDKs install via backend `[ai]`. Missing key, SDK, malformed response, network error or six-second deadline uses deterministic templates. One in-flight slot bounds abandoned workers; concurrent requests use templates immediately. Deadline does not cancel stuck SDK threads (daemonized). Classification merges deterministic needs and preserves medical urgency. Provider prose must retain supplied facts or uses templates. Logs exclude resident messages, secrets and exception bodies.

Report generation validates nested monetary fields and addresses, allowing prose to summarize other facts without repeating Python dict/list representations. Monetary checks accept exact full-dollar or compact representations; this is a consistency guard, not a factual verifier of new prose. The team-selected Anthropic default is claude-sonnet-5-5; live model availability was not verified in this environment, and LLM_MODEL remains the override.
