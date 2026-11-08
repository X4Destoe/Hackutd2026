# Pitch

How each company track shows up in the live app. Dollars below are what `GET /api/portfolio/summary` and
`GET /api/fix-first` return after `POST /api/demo/reset` on Hurricane Harvey at −48h. They are synthetic.
Hazard footprints are hand-drawn and labeled illustrative. Do not quote the early overview draft ($6.8M, a $24k plan);
the screen does not show those.

## CBRE

| What they judge | Where it is on screen |
|---|---|
| One record per building | Click Bayou Plaza. The detail joins the hazard, the downtown substation, the generator, the tenants, and the State Farm policy. |
| Predict the cascade | Drivers: about 3.0 ft of water above the first floor, substation down 96h, generator covers 18h. |
| Quantify impact | Header net exposure **$8.05M** at forecast. Bayou Plaza is severe, about **$2.98M** net. The waterfall is damage + rent + operations − insurance, and it balances to the cent. |
| Decide and execute | Fix-First top card: pre-book restoration, move ground-floor equipment, flood barriers, fuel. **Cost $32.8k, saves $991.96k (30.2×), act by −24h.** Approve. Avoided becomes **$991.96k** and net falls to about **$7.06M**. Four work orders and the tenant notices go out on the simulator. |
| Beyond a dashboard | The same approval offers Galleria Medical Offices as a community help site ($2k). A resident who says they are flooded in the Galleria area can be sent there. |

## Photon

| What they judge | Where it is on screen |
|---|---|
| A person in the loop | Texts shows the phone simulator. Send as the Houston engineer: `DONE WO-001`. The work order closes. |
| Tasks and notices | Approving the Bayou plan texts the on-site engineer and the tenant contacts. The bodies are the task and the ground-floor notice. |
| Residents | A resident phone number can text in. The reply is a place to go, not a dead end. |
| Real Photon | The bridge and the signed webhook are described in `backend/spikes/photon/PHOTON_NOTES.md`. This environment has not sent a real iMessage. With the env blank, `messaging_mode` stays `sim` and the demo still runs. |

## State Farm

| What they judge | Where it is on screen |
|---|---|
| Classify the need | "our apartment flooded, 2 kids, need a dry place" is shelter for 3 people. "it is freezing and we have no heat, 2 kids" is warmth. "I need to file a claim" goes to the claims desk. |
| Only safe, open, with room | At Harvey impact, Bayou Community Center Shelter is unsafe (in the flood) and is never chosen. George R. Brown Convention Center is. The map pin for an unsafe site has a red ×. |
| Coordinate, including a claims adjuster | The same thread texts the nearest open State Farm claim site: name, address, desk phone, "bring your policy number", and a maps link. Houston's desk is the Galleria site, `+17135551004`. |
| Nobody dropped | A request that fits nowhere stays unrouted and says it is flagged for a coordinator. Ian at landfall does this on purpose: the wind is over 74 mph at every Fort Myers site. At +48h the beach shelter is still under surge and is still skipped. |

## Real-world facts used, and what is not

- Hurricane Harvey (2017, Houston), Winter Storm Uri (2021, Dallas), and Hurricane Ian (2022, Fort Myers) are the three scenarios. The shapes on the map are illustrative, not official flood maps.
- George R. Brown Convention Center, 1001 Avenida de las Americas, is the Houston mega-shelter in the data. It was a Harvey shelter. NRG Center and the Kay Bailey Hutchison Convention Center are the other named public venues. The rest of the help sites are generic and the addresses say so.
- Buildings, tenants, policies, and every dollar figure are synthetic. State Farm in the product is the insurer on those synthetic policies and the operator of the claim-site records, not a quote from a State Farm loss report.

## What is already on main

Impact, Fix-First, work orders, the message simulator, and the building map are on main. Resident routing (including the claims-adjuster text), printable reports, and the help-site pins are on their own branches until those pull requests merge. If a beat above 404s, that branch is not in the tree you are running.

## What to say if a judge asks

- No key is loaded. Copy is the template fallback. Turn a provider on with `LLM_PROVIDER` only if you want the optional paragraph in a report. The numbers never come from the model.
- The timeline changes the hazard drawing and which sites are safe. The dollar forecast is the predicted loss for the storm, so Harvey's header can read the same at −48h and at 0h. The approval is what moves Avoided.
- A live Photon handset is a rehearsal step, not a requirement for the three-minute path.
