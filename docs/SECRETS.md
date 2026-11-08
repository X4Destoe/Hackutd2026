# Private API credentials

Enter real values only in environment secret settings or the ignored `backend/.env` file. Do not send keys in chat, commit them, or add them to frontend settings. Any variable beginning with `VITE_` can be included in browser JavaScript; never use that prefix for a private key.

The private file is created with owner-only permissions (`600`). An existing file is preserved. On another machine, from the repository root:

```sh
cp .env.example backend/.env  # first setup only; do not overwrite an existing file
chmod 600 backend/.env
```

Edit the file in your editor. Keep `MESSAGING_MODE=sim` while configuring and checking the app.

## Photon

For the existing Spectrum bridge, fill in `SPECTRUM_PROJECT_ID`, `SPECTRUM_PROJECT_SECRET`, and `SPECTRUM_WEBHOOK_SECRET`. Provision a sending line in Photon; set `SPECTRUM_SENDER` if selecting among multiple lines. `DEMO_PHONES` maps authorized phone numbers to existing party IDs, such as a manager's number to `MGR-01`. Do not use the illustrative phone numbers as real recipients.

The Node bridge reads `backend/.env`, binds to loopback, and only sends to mapped recipients. Expose the application's `/api/webhooks/photon` route through the configured public HTTPS endpoint; do not expose the bridge's send port. Signed inbound webhooks are verified before message handling.

Restart the API and bridge after changing settings. Check configuration readiness without displaying values. Switch to `MESSAGING_MODE=photon` only for the configured real-phone rehearsal. Application-wide authentication is outside the current demo: do not publish the whole backend as a private management service without access control.

## Assistant

The AI-provider key also belongs on the backend. The existing operational AI supports `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, or `OPENAI_API_KEY` with `LLM_PROVIDER`. The corner assistant's separate provider configuration is being finalized in TASK-059; do not assume a new assistant key name until its interface is documented. Provider keys must never be returned in API responses, frontend code, or error messages.

Tell the agent only which variable names you configured; there is no need to reveal the values. Configuration-file protections reduce accidental exposure; they do not turn the unauthenticated hackathon demo into a production-secure service.

## Current Photon Project API keys

A current Photon Project API key belongs in `PHOTON_API_KEY`, not `SPECTRUM_PROJECT_SECRET`. The official `@photon-ai/api` client sends it as a Bearer credential to `https://api.photon.codes/v1/projects/{projectId}`. It requires `PHOTON_PROJECT_ID`; a project-scoped key cannot enumerate organization projects. A webhook destination ID is a different resource and cannot substitute for a project ID. The existing Spectrum bridge does not consume these HTTP API settings; that adapter requires separate integration and verification before real sending can be claimed.

This cloud environment must allow `api.photon.codes` before authenticated discovery or delivery checks can reach Photon. Saving an environment configuration draft does not apply it to the running machine.
