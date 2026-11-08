# Customer notices public interface

Auto-discovered `router` exposes `POST /api/customer-notices`. Request and response are documented in `docs/prd/customer-notices.md`. Imports messaging and scenarios through public module interfaces only. No alternate provider transport or inbound handler is installed.

Dispatch rechecks scenario/hour/mode and request-history identity before and after each recipient. A context change stops the remaining batch with409; an already-started provider attempt cannot be recalled and may have an unknown outcome. The browser smoke requires simulator mode before reset and accepts STORM_URL / STORM_ARTIFACT_DIR instead of workstation-specific paths.
