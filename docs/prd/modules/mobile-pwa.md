# Module: mobile-pwa (`frontend/src/modules/mobile-pwa/`)

**Skills:** frontend, typescript, mobile, ui-design · **Uses:** web-shell `shared/*` (PWA config lives in web-shell)

## Job
The phone-sized screens, installable with "Add to Home Screen":
1. **Help card** (`/h/:token`) for **customers**. Every Photon text links here. It answers "where do I go, what's
   happening, who's coming" on a cracked phone screen with bad signal.
2. **Field view** (`/field/:adjusterId`) for **claims adjusters**: their offers and accepted cases, with accept/pass buttons.
   It's the same human-in-the-loop decision as the SMS reply, just as a page.

## Owns
`frontend/src/modules/mobile-pwa/**` (exports `HelpCard`, `FieldView`).

## Help card (`useHelpCard(token)`, refresh via SSE + 30s poll fallback)
- Top: status in big words, in the customer's language (en/es/vi strings in a local dictionary):
  "Go to: Trinity Convention Center", "Help is on the way", "We're finding you a place", "You're marked safe".
- Place card: name, address, open hours, spots left, ETA, big **Directions** button (`directions_url`), call button if
  `phone`. Re-routed? Show a yellow "Changed: the previous site lost power".
- Adjuster: name + ETA when assigned.
- 2–3 safety tips for their needs.
- Footer: "Reply to our text anytime · Add this page to your Home Screen" (with a hint on how to do it on iPhone/Android).
- Under 50 KB of JS for this route (code-split). Readable at 360px wide. Large tap targets. Works with only cached data if
  offline, showing the "last updated" time.

## Field view (`useFieldView(adjusterId)`)
- Pending offers at the top: case summary, tier, damages, distance, **Accept** / **Pass** → `POST /api/field/offers/{id}`.
- Accepted cases: address with a maps link, household flags (oxygen, infants, elderly), needs, the last 3 customer messages, notes.
- Header shows the specialty badges ("Water specialist") to make the specialization story visible.

## Acceptance
- Opening a help-card link from a real Photon text on an iPhone renders correctly. "Add to Home Screen" gives a standalone app.
- The help card updates within ~2s when the case gets re-routed or an adjuster is assigned.
- Accept on the field view has the same effect as replying ACCEPT by text.

## Not in scope
Login (links are unguessable tokens; fine for a hackathon), push notifications (Photon texts do that job), a native
Swift app (stretch only: same endpoints).
