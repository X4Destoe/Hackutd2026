# Operation Storm on iPhone

The same site now has a phone layout and can launch from an iPhone Home Screen. It uses the same scenarios, records and API as the desktop. No App Store download or separate account is required.

## Open and install

1. Open the team's hosted **HTTPS** site in **Safari** on the iPhone.
2. Tap **Share → Add to Home Screen**. Turn on **Open as Web App** if offered, then tap **Add**.
3. Launch the **Storm** icon. The in-app download icon repeats these instructions.

The web manifest requests standalone display. iOS metadata, a 180px Apple touch icon, and 192/512px app icons are included. The layout respects the notch/Home indicator and supports portrait and landscape. Safari controls and installation labels vary by iOS version; there is no automatic iOS install prompt.

## Response views

The bottom bar has **Map**, **Fix-First**, **Work Orders** and **Help Sites**. Map retains the desktop basemap, hazards, timeline, building markers, zoom and layers. Tap **Key** to see the loss/hazard legend. Tap a building for its details; **Back to map** returns to it. The timeline scrolls horizontally on phones. Fix-First approves the same server plans; work-order status changes and blocker notes persist through the same API. Help Sites retains availability/capacity and directions/call links. Texts and the customer-message composer are hidden on phone screens. Desktop Texts remain available.

The mobile breakpoint is 900 CSS pixels, extended to 1024px on touch devices to cover larger iPhones in landscape. Simulation creation/reset and desktop report navigation remain desktop tools; scenario switching is available on the phone. Building-detail report links remain usable when needed.

## Connection and deployment

This is an online response viewer, not an offline emergency dataset. The phone shows an offline/service-unavailable warning; a lightweight health check runs every15seconds while visible. Offline mutations fail visibly rather than silently queueing for reconnection. No background sync is registered. A production service worker caches **only** `/offline.html`; it does not cache app bundles, API responses, map tiles, contacts or work orders. A fresh offline launch explains that a connection is required. A view already open may retain in-memory query data: the warning identifies it as potentially out of date. Client view-sync time is not a hazard observation timestamp; the live map still displays its source-quality information.

Serve `frontend/dist` on an HTTPS origin and proxy `/api` (including SSE `/api/events`) to the running backend on the same origin. Serve `/manifest.webmanifest`, `/app-icons/*`, `/offline.html` and `/sw.js` as static files, not the SPA fallback. Give `/sw.js` a revalidation-friendly Cache-Control policy. The root-relative manifest/start URL assumes hosting at `/`.

For a local phone preview, put phone and computer on the same Wi-Fi, keep both backend and Vite running, allow the Vite port through the computer firewall, then open Vite's **Network** URL (for example `http://192.168.1.20:5173`) on the phone. `localhost` on the phone points to the phone, not the computer. Plain LAN HTTP can preview responsive screens; it does not provide the secure-context service worker/offline behavior. Use the team's HTTPS deployment for installation testing. No secrets or backend management ports need exposing to the phone.

## Verification

Build: `cd frontend && npm run build`. Run backend with `MESSAGING_MODE=sim`, and use `npm run preview -- --host 127.0.0.1 --port 5173` for production asset/worker testing. Vite preview inherits the existing `/api` proxy to port 8000.

Run `node e2e/mobile-smoke.cjs` from frontend. It first verifies simulator mode, resets an isolated demo, then checks phone map selection/timeline, approval, work-order blocked/done updates, help directions, 320px and landscape fit, touch targets, hidden Texts, Home Screen assets, offline warning/failure/no deferred approval, cache contents, offline launch and desktop navigation. It restores the demo afterward. `STORM_URL`, `CHROMIUM_PATH`, and `STORM_TEST_OUTPUT` configure the browser gate. Screenshots go to a temporary directory by default.

The automated gate uses Chromium with iPhone touch/viewport emulation (including932px landscape); optional STORM_BROWSER=webkit selects WebKit when its Linux libraries are installed. WebKit launch in this cloud image is blocked by missing GTK4/Graphene/Harfbuzz-ICU/Manette/Hyphen/GLES libraries; installation on a physical iPhone still needs Safari's Share action and the hosted HTTPS URL.
