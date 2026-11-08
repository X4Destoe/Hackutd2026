# Community views

HelpSites accepts optional city and uses resource/referral queries. Medical referrals and unrouted requests are shown first; unsafe sites are explicitly marked. Capacity bars use supplied capacity/used values; availability is not inferred from a site's name.

Reports generates executive or building tenant reports, then links to the backend's printable HTML. It does not inject report Markdown/HTML into the app or send tenant notices automatically.

Messages uses the existing mutation/query invalidations and the application-level SSE connection. Known party IDs come from building technician/tenant contacts plus the demo manager. Residents enter an international phone number. Failed drafts remain editable; pending requests disable resubmission. Photo links allow HTTP(S) only. No new EventSource is opened here.

Validation: frontend production build; Chromium fixture checks for resident/technician payloads, under-two-second feed refresh, referral/unsafe/capacity displays, executive and tenant report generation, printable popup and failed-send retry. Resources/messaging/report backend modules must merge before the same flow can be verified against real services. No real phone message was sent during validation.
