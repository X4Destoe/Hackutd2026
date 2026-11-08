# 04 - UI spec (layout modeled on the UTD campus map)

Reference: the UTD interactive campus map. We copy its **structure**, not its colors: action buttons along the top,
a left panel with search, a hero card, tabs and toggleable category rows, and a large interactive map filling the right side,
with a vertical control on the map's left edge and map tools on its right edge.

## 1. Layout (desktop 1440×900; must look good on a projector)

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ▣ BRACE   [Scenario: Harvey · Houston ▾] [Fix-First] [Work Orders] [Help Sites] [Reports]  $ exposure │ ⟳ ⎙ │  TOP BAR (56px)
├──────────────────────────────┬───────────────────────────────────────────────────────────────────────────┤
│ 🔍 Search building, tenant…  │ ┌────┐                                                         ┌──┐     │
│ ┌──────────────────────────┐ │ │ −48│   MAP (MapLibre, ~70% width, full height)               │⌂ │     │
│ │ HERO CARD: scenario      │ │ │ −24│   · basemap (light, muted)                              │◫ │ layers
│ │ "Hurricane Harvey · 2017"│ │ │ −12│   · animated hazard overlay (blue water / snow / wind)  │⊕ │ zoom
│ │ phase badge · narrative  │ │ │  0 │   · buildings: circles sized by value, colored by $    │⊖ │
│ │ Net exposure  $6.8M      │ │ │ +12│     net exposure, label with name + $                   │? │ legend
│ │ Avoided       $0         │ │ │ +48│   · selected building: outlined + pulsing ring         └──┘     │
│ └──────────────────────────┘ │ │+7d │   · substations (⚡ red when down), dependency lines         │
│ [Overview] [Buildings] [Help]│ └────┘   · help sites (pins; ✕ when unsafe; capacity ring)              │
│  tabs (like Locations|Tours) │  TIMELINE   · work-order badges on buildings                              │
│ ─────────────────────────────│  (vertical,   ┌─────────────────────────────┐                             │
│  LAYER ROWS (toggle boxes)   │  like UTD's   │ hover tooltip: name, $ net, │                             │
│  🌊 Hazard overlay      [■] │  floor        │ risk, top driver            │                             │
│  🏢 Buildings by $ risk [■] │  selector)    └─────────────────────────────┘                             │
│  ⚡ Power grid          [■] │                                                                            │
│  🛠 Work orders         [■] │                                    legend chip bottom-right: $ color scale │
│  🏥 Help sites          [■] │                                    disclaimer chip bottom-left              │
│  ✉ Messages            [ ] │                                                                            │
│ ─────────────────────────────│                                                                            │
│  CONTENT AREA (scrolls):     │                                                                            │
│  Overview → Fix-First top 5  │                                                                            │
│  or Building detail          │                                                                            │
│ ─────────────────────────────│                                                                            │
│ footer: portfolio · 12 bldgs │                                                                            │
└──────────────────────────────┴───────────────────────────────────────────────────────────────────────────┘
```
- Left panel: fixed **400px**, scrollable content area. The map gets the rest.
- **Top bar buttons** open their view in the left panel's content area (they don't navigate away): Fix-First,
  Work Orders, Help Sites, Reports. The scenario dropdown sits leftmost. The right side shows live **net exposure** and **$ avoided**, plus refresh and print icons.
- **Timeline control** = a vertical segmented control floating on the map's left edge (like UTD's floor selector), with up/down arrows
  and the current step highlighted. Phase color bands: forecast = purple, impact = red, recovery = green. Keyboard ←/→ also steps.
- **Map tools** float on the right edge: home (re-center the scenario), layers popover, zoom ±, legend toggle.
- Under 1100px wide, the panel becomes a slide-over drawer. Mobile isn't a target, but nothing should break.

## 2. Left-panel views (content area)

| View | Opened by | Shows |
|---|---|---|
| **Overview** (default) | tab | Scenario narrative for this step, portfolio KPIs (at-risk count, gross, net, avoided, insurance recovery), **Fix-First top 5** (compact cards), "missed" plans in muted red |
| **Buildings** | tab | Sortable list (net $ desc / name / risk), filter "in this scenario". Each row: risk dot, name, city, net $, mini bar. Click → Building detail and the map flies to it |
| **Building detail** | clicking a building on the map or list | Header (name, type, city, risk badge). **"Fragmented data → one record"** chips (`data_sources`). Exposure readings. **Why** (cause chain + drivers). **Money waterfall** (damage + downtime + SLA + ops − insurance = net). **Plan card(s)** with Approve / Reject. Tenants table. Work orders. "Generate tenant notice" button |
| **Fix-First** | top button | Ranked cards: rank, building, action titles, cost, saves, ROI ×, act-by countdown ("act in 12h" / "MISSED"), Approve. Community actions (help site) in their own section |
| **Work Orders** | top button | List with status chips (sent/accepted/done/blocked), assignee, last update, photo thumbnails from Photon replies |
| **Help Sites** (State Farm) | top button / tab "Help" | Sites with status (open/full/unsafe ✕), capacity bar, type icon. Recent **referrals** (resident summary → site, distance, re-routed badge). Unrouted requests flagged in red |
| **Reports** | top button | Generate executive summary / tenant notice. List of generated reports with "Open printable" |
| **Messages** (optional) | layer row toggle | Live feed of Photon messages (in/out) with a phone-style simulator box to type as any party |

## 3. Map visuals (see `modules/map.md`)
- **Buildings:** circle radius ∝ √replacement value. Fill color by net exposure (none grey, low green, moderate yellow,
  high orange, severe red). Label shows name + "$1.65M". After approval: the ring turns green dashed and a ✓ appears.
- **Hazard overlays** (each style is visually distinct and animated):
  - `flood_water`: blue fills by depth band, opacity pulse, "rising" effect when stepping into impact (opacity/extent tween over 800ms).
  - `surge_water`: darker blue, moving wave-stripe pattern.
  - `snow_ice`: white/ice-blue tint plus a canvas **falling-snow particle** layer over the affected area.
  - `wind_swirl`: concentric translucent rings with a slow rotation, plus a hurricane track line.
  - `forecast_cone`: dashed purple outline cone (forecast steps).
  - `fire_smoke` (stretch): orange glow plus drifting ember particles.
- **Power:** substations as ⚡ markers (red and pulsing when down). Thin dependency lines substation → building appear on hover or selection.
- **Help sites:** pins by type. A red ✕ overlays unsafe ones. Referrals draw a brief animated line from the resident's approximate location to the site.

## 4. Visual style
Neutral, professional, not UTD colors: dark slate top bar, white panel, accent teal (CBRE-ish green-teal is fine)
for primary buttons. Dollar figures use tabular numerals. Risk colors as above. Font: Inter/system. shadcn components.
Every number has a unit. Every chart has a label. A judge must understand any screen in 10 seconds without narration.
