# AI gateway
Optional provider assistance with deterministic English, Spanish and Vietnamese fallbacks. Import only the public package described in INTERFACE.md.

From backend: `LLM_PROVIDER=none python -m pytest app/modules/ai -q`.
No key or SDK required for tests. Provider failures, invalid responses and stalls use injected fakes; paid APIs are not tested. Configure keys through secure environment settings. Override model availability using LLM_MODEL.
