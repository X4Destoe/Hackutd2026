// Brace demo - model: hazard lookup, power cascade, money (PRD 03 §3), plans/Fix-First (§4), help-site routing (§5).
/* eslint-disable */
window.BRACE_MODEL = (function () {
  const D = window.BRACE_DATA;
  const MI = 69.0; // miles per degree latitude

  // ---------- geometry ----------
  function distMi(a, b) {
    const kx = Math.cos((a[1] + b[1]) / 2 * Math.PI / 180) * MI;
    return Math.hypot((a[0] - b[0]) * kx, (a[1] - b[1]) * MI);
  }
  function distToLineMi(p, line) {
    let best = Infinity;
    const kx = Math.cos(p[1] * Math.PI / 180) * MI;
    for (let i = 0; i < line.length - 1; i++) {
      const ax = line[i][0] * kx, ay = line[i][1] * MI, bx = line[i + 1][0] * kx, by = line[i + 1][1] * MI;
      const px = p[0] * kx, py = p[1] * MI, dx = bx - ax, dy = by - ay;
      const t = Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy || 1)));
      best = Math.min(best, Math.hypot(px - (ax + t * dx), py - (ay + t * dy)));
    }
    return best;
  }
  const lerp = (pts, x) => { // piecewise-linear interpolation over [[x,y],...]
    if (x <= pts[0][0]) return pts[0][1];
    for (let i = 1; i < pts.length; i++) if (x <= pts[i][0]) {
      const [x0, y0] = pts[i - 1], [x1, y1] = pts[i]; return y0 + (y1 - y0) * (x - x0) / (x1 - x0);
    }
    return pts[pts.length - 1][1];
  };

  // ---------- hazard ----------
  // damageFactor: share of peak hazard used for DAMAGE at this step (forecast = predicted peak; recovery = peak seen).
  const damageFactor = (h) => (h < 0 ? 1 : h === 0 ? 0.7 : 1);
  const presentFactor = (h) => D.PRESENT[String(h)];

  function hazardAt(s, p, hour, mode = "damage") {
    const f = mode === "damage" ? damageFactor(hour) : presentFactor(hour);
    const out = { flood: 0, surge: 0, wind: 0, temp: null, ice: 0 };
    for (const r of s.rivers || []) {
      const d = distToLineMi(p, r.coords);
      if (d < r.hw) {
        const depth = r.peak * (1 - d / r.hw) * f;
        if (s.kind === "surge") out.surge = Math.max(out.surge, depth); else out.flood = Math.max(out.flood, depth);
      }
    }
    for (const pool of s.pools || []) {
      const d = distMi(p, pool.center);
      if (d < pool.radius) out.flood = Math.max(out.flood, pool.peak * (1 - 0.6 * d / pool.radius) * f);
    }
    if (s.wind) {
      const d = distToLineMi(p, s.wind.track);
      out.wind = s.wind.peakMph * Math.max(0.35, 1 - Math.max(0, d - 8) / 80) * (mode === "damage" ? damageFactor(hour) : presentFactor(hour));
    }
    if (s.kind === "winter") {
      const a = s.area, inside = ((p[0] - a.center[0]) / a.rx) ** 2 + ((p[1] - a.center[1]) / a.ry) ** 2 <= 1;
      if (inside) {
        const minTemp = Math.min(...Object.entries(s.temps).filter(([h]) => mode !== "damage" ? +h === hour : (hour < 0 ? true : +h <= Math.max(hour, 12))).map(([, t]) => t));
        out.temp = mode === "damage" ? minTemp : s.temps[String(hour)];
        out.ice = mode === "damage" || hour >= 0 && hour <= 48 ? s.ice : 0;
      }
    }
    return out;
  }
  const hazardsPresent = (hz, unpowered) => {
    const k = [];
    if (hz.flood > 0) k.push("flood"); if (hz.surge > 0) k.push("surge"); if (hz.wind > 74) k.push("wind");
    if (hz.temp !== null && hz.temp <= 20) k.push("winter");
    return k;
  };

  // ---------- money (PRD 03 §3) ----------
  const FLOOD_CURVE = [[0, 0], [0.5, 0.05], [1, 0.10], [2, 0.18], [3, 0.24], [4, 0.28], [6, 0.35], [8, 0.42]];
  const rentPerDay = (b) => b.tenants.reduce((a, t) => a + t.rent_per_day_cents, 0);
  const slaPerHour = (b) => b.tenants.reduce((a, t) => a + t.sla_penalty_per_hour_cents, 0);

  function impact(s, b, hour, codes = []) {
    const acts = codes.map((c) => D.actions.find((a) => a.code === c)).filter(Boolean);
    if (b.city !== s.city) return { b, none: true, risk: "none", net: 0, gross: 0, drivers: ["Not in the hazard area"], money: zero(), hz: {}, chain: [] };
    const hz = hazardAt(s, b.c, hour, "damage");
    const sub = s.substations[b.util] || { out: 0, name: b.util };
    const outHours = sub.out;
    const genH = b.gen + acts.reduce((a, x) => a + (x.addGen && (b.gen > 0 ? x.needGen : x.needNoGen) ? x.addGen : 0), 0);
    const unpowered = Math.max(0, outHours - genH);
    const above = Math.max(hz.flood, hz.surge) - b.floorFt;
    const r = {}; // damage ratio per hazard
    if (above > 0) {
      let fr = lerp(FLOOD_CURVE, above) + (b.groundEquip ? 0.04 : 0);
      if (hz.surge > hz.flood) fr = Math.min(0.9, fr * 1.3);
      r[hz.surge > hz.flood ? "surge" : "flood"] = fr;
    }
    const excess = hz.wind - b.roofMph;
    if (hz.wind > 74) r.wind = excess <= 0 ? 0.01 : Math.min(0.5, 0.02 + 0.004 * excess);
    if (hz.temp !== null) {
      let w = 0;
      if (!b.freeze && hz.temp <= 20 && unpowered > 8) w += Math.min(0.10, 0.03 + 0.002 * (unpowered - 8));
      if (hz.ice >= 0.5) w += 0.01;
      if (w) r.winter = w;
    }
    // apply action effects
    let downMult = 1, slaMult = 1;
    for (const a of acts) {
      for (const k of Object.keys(r)) {
        if (a.damage && (a.hazards.length === 0 || a.hazards.includes(k))) {
          if (a.maxDepth !== undefined && (k === "flood" || k === "surge")) r[k] *= above <= a.maxDepth ? a.damage : a.damageAbove;
          else r[k] *= a.damage;
        }
      }
      if (a.downtime && (a.hazards.length === 0 || a.hazards.some((h) => r[h] !== undefined))) downMult *= a.downtime;
      if (a.sla) slaMult *= a.sla;
    }
    const ratio = 1 - Object.values(r).reduce((p, x) => p * (1 - x), 1);
    const property = b.value * ratio; // b.value is already in cents
    const downtimeDays = (ratio * 180 + unpowered / 24) * downMult;
    const rent = downtimeDays * rentPerDay(b);
    const sla = Math.min(unpowered + downtimeDays * 24, 720) * slaPerHour(b) * slaMult;
    const ops = downtimeDays * b.sqft * 5;
    const ded = b.value * b.ins.ded, limit = b.value;
    const insurance = Math.min(limit, Math.max(0, property - ded)) + Math.min(downtimeDays, b.ins.bi) * rentPerDay(b);
    const gross = property + rent + sla + ops;
    const net = Math.max(0, gross - insurance);
    const drivers = [];
    if (above > 0) drivers.push(`${above.toFixed(1)} ft of ${hz.surge > hz.flood ? "storm surge" : "water"} above the first floor`);
    else if (Math.max(hz.flood, hz.surge) > 0) drivers.push(`${Math.max(hz.flood, hz.surge).toFixed(1)} ft of water at the site, first floor is ${b.floorFt} ft up`);
    if (r.wind) drivers.push(`${Math.round(hz.wind)} mph wind vs roof rated ${b.roofMph} mph`);
    if (outHours > 0) drivers.push(`${sub.name} down ${outHours}h, ${genH > 0 ? `generator covers ${genH}h` : "no generator"}${unpowered > 0 ? ` → ${Math.round(unpowered)}h without power` : ""}`);
    if (r.winter) drivers.push(`${hz.temp}°F with no heat and no pipe freeze protection: burst pipes`);
    if (sla > 0) drivers.push(`${b.tenants.filter((t) => t.sla_penalty_per_hour_cents).length} critical tenants: SLA ${fmt(slaPerHour(b))}/h`);
    if (insurance > 0) drivers.push(`Insurance (${b.ins.carrier}) recovers ${fmt(insurance)} after a ${fmt(ded)} deductible`);
    const chain = [];
    if (outHours > 0) { chain.push(`${sub.name} down ${outHours}h`); chain.push(genH > 0 ? `generator ${genH}h` : "no backup power"); if (unpowered > 0) chain.push(`${Math.round(unpowered)}h dark`); if (b.type === "data_center" && unpowered > 0) chain.push("cooling lost → SLA breach"); if (r.winter) chain.push("pipes freeze"); }
    if (above > 0) chain.push(`${above.toFixed(1)} ft inside`, "tenants out " + Math.round(downtimeDays) + " days");
    const risk = net <= 0 ? "none" : net < 5e6 ? "low" : net < 25e6 ? "moderate" : net < 1e8 ? "high" : "severe";
    return { b, risk, ratio, hz, outHours, genH, unpowered, above, drivers: drivers.slice(0, 5), chain,
      money: { property, rent, sla, ops, insurance, gross, net, downtimeDays }, net, gross, hazards: hazardsPresent(hz, unpowered).concat(unpowered > 0 ? ["power"] : []) };
  }
  const zero = () => ({ property: 0, rent: 0, sla: 0, ops: 0, insurance: 0, gross: 0, net: 0, downtimeDays: 0 });

  // ---------- plans ----------
  function candidates(s, b, hour, base) {
    return D.actions.filter((a) => {
      if (a.community) return false;
      if (hour > a.actBy) return false;
      if (a.needGen && !(b.gen > 0 && base.unpowered > 0)) return false;
      if (a.needNoGen && !(b.gen === 0 && base.unpowered > 0)) return false;
      if (a.needSla && slaPerHour(b) === 0) return false;
      if (a.hazards.length && !a.hazards.some((h) => base.hazards.includes(h))) return false;
      if (!a.hazards.length && !a.addGen && !a.sla && base.net <= 0) return false;
      return true;
    });
  }
  function bestPlan(s, b, hour, fixed = []) {
    const base = impact(s, b, hour, fixed);
    let chosen = [], current = base, cost = 0;
    let pool = candidates(s, b, hour, base).filter((a) => !fixed.includes(a.code));
    while (pool.length) {
      let best = null;
      for (const a of pool) {
        const next = impact(s, b, hour, fixed.concat(chosen, [a.code]));
        const gain = current.net - next.net, roi = gain / a.cost;
        if (roi > 1 && (!best || roi > best.roi)) best = { a, next, roi };
      }
      if (!best) break;
      chosen.push(best.a.code); cost += best.a.cost; current = best.next;
      pool = pool.filter((x) => x !== best.a);
    }
    if (!chosen.length) return null;
    const acts = chosen.map((c) => D.actions.find((a) => a.code === c));
    const avoided = base.net - current.net;
    return { building: b, codes: chosen, actions: acts, cost, avoided, roi: avoided / cost,
      actBy: Math.min(...acts.map((a) => a.actBy)), before: base, after: current };
  }

  // ---------- help-site safety & routing ----------
  function siteStatus(s, site, hour) {
    if (site.city !== s.city) return "other";
    const hz = hazardAt(s, site.c, hour, "present");
    const pred = hazardAt(s, site.c, hour, "damage");
    const sub = s.substations[site.util] || { out: 0 };
    const powerOut = hour >= 0 && hour < sub.out;
    if (hour < 0 && (Math.max(pred.flood, pred.surge) > 0.5 || sub.out > 0 || pred.wind > 110)) return "at_risk";
    if (Math.max(hz.flood, hz.surge) > 0.5 || powerOut || hz.wind > 110) return "unsafe";
    if (site.used >= site.cap) return "full";
    return "open";
  }
  const NEED_TYPES = { shelter: ["shelter", "cbre_help_site", "hotel"], warmth: ["warming_center", "shelter", "cbre_help_site"],
    claim: ["claim_site"], food_water: ["shelter", "warming_center", "cbre_help_site"] };
  function classify(text) {
    const t = text.toLowerCase();
    const needs = [];
    if (/(oxygen|ox[ií]geno|injur|hurt|herid|dialysis|ambulance|bleeding)/.test(t)) needs.push("medical");
    if (/(flood|water inside|inundad|ngập|roof gone|destroyed|dry place|place to stay|somewhere|shelter|refugio|evacuat)/.test(t)) needs.push("shelter");
    if (/(cold|fr[ií]o|lạnh|no heat|freezing|sin calefacci|warm)/.test(t)) needs.push("warmth");
    if (/(claim|reclamo|adjuster|insurance|seguro|policy)/.test(t)) needs.push("claim");
    if (/(food|water to drink|agua|comida|hungry)/.test(t)) needs.push("food_water");
    if (!needs.length) needs.push("shelter");
    const m = t.match(/(\d+)\s*(kids|children|people|ni[ñn]os|personas|of us)/);
    const people = m ? +m[1] + (/(kids|children|ni)/.test(m[2]) ? 1 : 0) : 1;
    const lang = /[ñáéíóú¿¡]|(agua|casa|niños|necesito|frío|inundad)/.test(t) ? "es" : "en";
    return { needs, people, lang, urgent: needs.includes("medical") };
  }
  const PLACES = { meyerland: [-95.455, 29.685], downtown: null, "energy corridor": [-95.62, 29.78], galleria: [-95.46, 29.74],
    "white oak": [-95.42, 29.79], lakewood: [-96.75, 32.82], "farmers branch": [-96.89, 32.92], "oak lawn": [-96.81, 32.81],
    beach: [-81.95, 26.45], "fort myers beach": [-81.95, 26.45], cape: [-81.95, 26.6] };
  function residentLocation(s, text, n) {
    const t = text.toLowerCase();
    for (const [k, v] of Object.entries(PLACES)) if (t.includes(k)) return v || s.center;
    const r = (s.rivers && s.rivers[0]) ? s.rivers[n % s.rivers.length].coords : null;
    if (r) { const p = r[(n * 3 + 2) % r.length]; return [p[0] + 0.01, p[1] - 0.008]; }
    return [s.center[0] + ((n * 37) % 10 - 5) / 100, s.center[1] + ((n * 53) % 10 - 5) / 120];
  }
  function route(s, sites, hour, text, n, exclude = []) {
    const need = classify(text), from = residentLocation(s, text, n);
    if (need.urgent) return { need, from, urgent: true };
    const types = [...new Set(need.needs.flatMap((x) => NEED_TYPES[x] || []))];
    let best = null;
    for (const site of sites) {
      if (exclude.includes(site.id) || !types.includes(site.type)) continue;
      const st = siteStatus(s, site, hour);
      if (st !== "open" || site.cap - site.used < need.people) continue;
      const d = distMi(from, site.c);
      if (!best || d < best.d) best = { site, d };
    }
    return { need, from, site: best && best.site, dist: best && best.d };
  }

  function fmt(cents) {
    const d = Math.round(cents / 100), a = Math.abs(d);
    if (a >= 1e6) return `$${(d / 1e6).toFixed(a >= 1e7 ? 1 : 2)}M`;
    if (a >= 1e3) return `$${Math.round(d / 1e3)}k`;
    return `$${d}`;
  }

  return { distMi, hazardAt, impact, bestPlan, siteStatus, route, classify, fmt, presentFactor, damageFactor, rentPerDay, slaPerHour };
})();
