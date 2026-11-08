// Operation Storm demo - UI. Plain JS, no build step. Everything runs in the browser (texts are simulated).
/* eslint-disable */
(function () {
  const D = window.BRACE_DATA, M = window.BRACE_MODEL, fmt = M.fmt;
  const $ = (s) => document.querySelector(s);
  const RISK = { none: "#9aa5ae", low: "#2e9d5b", moderate: "#e1b12c", high: "#ec7a1c", severe: "#d63b2f" };
  const PHASE = { forecast: "#7a5af8", impact: "#d63b2f", recovery: "#2e9d5b" };
  const SITE_ICON = { shelter: "S", warming_center: "W", claim_site: "C", hotel: "H", cbre_help_site: "+" };
  const SITE_NAME = { shelter: "Shelter", warming_center: "Warming center", claim_site: "State Farm claim site", hotel: "Hotel", cbre_help_site: "CBRE help site" };
  const TYPE_ICON = {};

  let st;
  function reset(sid) {
    st = { sid: sid || (st && st.sid) || "harvey_houston", hi: 0, approvals: {}, wo: [], msgs: [], refs: [], cbre: [], sel: null, view: "overview",
      layers: { hazard: true, buildings: true, power: true, help: true, wo: true }, sites: D.sites.map((x) => ({ ...x })), n: 0, initial: {} };
  }
  reset();
  const S = () => D.scenarios[st.sid];
  const step = () => D.STEPS[st.hi];
  const H = () => step().hour;
  const inCity = (b) => b.city === S().city;
  const allSites = () => st.sites.concat(st.cbre);

  // ---------- derived state ----------
  function impactOf(b) { return M.impact(S(), b, H(), (st.approvals[b.id] || {}).codes || []); }
  function baselineOf(b) { return M.impact(S(), b, H(), []); }
  function initialPlan(b) {
    const k = st.sid + b.id;
    if (!(k in st.initial)) st.initial[k] = M.bestPlan(S(), b, -48);
    return st.initial[k];
  }
  function plans() {
    const out = { live: [], missed: [] };
    for (const b of D.buildings.filter(inCity)) {
      if (st.approvals[b.id]) continue;
      const init = initialPlan(b);
      const cur = M.bestPlan(S(), b, H());
      if (init && H() > init.actBy) out.missed.push({ ...init, missed: true, late: cur });
      if (cur) out.live.push(cur);   // what can still be done now (post-event options after deadlines pass)
    }
    out.live.sort((a, b) => ((a.actBy - H() <= 12) === (b.actBy - H() <= 12) ? b.roi - a.roi : (a.actBy - H() <= 12 ? -1 : 1)));
    return out;
  }
  function totals() {
    let net = 0, gross = 0, ins = 0, avoided = 0, atRisk = 0;
    for (const b of D.buildings.filter(inCity)) {
      const i = impactOf(b);
      net += i.net; gross += i.money.gross; ins += i.money.insurance; if (i.net > 0) atRisk++;
      if (st.approvals[b.id]) avoided += Math.max(0, baselineOf(b).net - i.net);
    }
    return { net, gross, ins, avoided, atRisk };
  }

  // ---------- messaging (simulated Photon) ----------
  function text(party, body, dir = "out", kind = "", quiet = false) {
    st.msgs.push({ party, body, dir, kind, at: step().label });
    if (quiet) return;
    if (dir === "out") toast(`${icon("send", 14)}<b>Text to ${party}</b> · ${body.length > 110 ? body.slice(0, 110) + "…" : body}`);
    else toast(`${icon("message-square", 14)}<b>${party}</b> ${party.startsWith("Resident") ? "texted" : "replied"} · ${body}`);
  }
  function toast(html) {
    const el = document.createElement("div"); el.className = "toast"; el.innerHTML = html; $("#toast").appendChild(el);
    setTimeout(() => el.remove(), 4200);
  }

  // ---------- actions ----------
  function approve(bid) {
    const b = D.buildings.find((x) => x.id === bid);
    const p = M.bestPlan(S(), b, H());
    if (!p) return;
    st.approvals[bid] = { codes: p.codes, at: H(), plan: p };
    const tech = D.parties[b.tech].name;
    p.actions.forEach((a, i) => {
      const id = "WO-" + String(st.wo.length + 1).padStart(3, "0");
      st.wo.push({ id, bid, b: b.name, action: a.title, status: "sent", who: tech, updates: [] });
      text(tech, `OPERATION STORM TASK ${id} · ${b.name}: ${a.task}. ${a.actBy <= 0 ? "Deadline " + (a.actBy === 0 ? "landfall" : `${Math.abs(a.actBy)}h before landfall`) : "Start now"}. Reply DONE, BLOCKED or send a photo.`, "out", "task", true);
      if (a.notice) b.tenants.forEach((t) => text(t.name, `Notice from ${b.name} management: ${a.notice}`, "out", "notice", true));
    });
    const notices = p.actions.filter((a) => a.notice).length * b.tenants.length;
    toast(`${icon("send", 14)}<b>Plan approved for ${b.name}.</b> ${p.actions.length} tasks texted to ${tech}${notices ? `, ${notices} notices to ${b.tenants.length} tenants` : ""}.`);
    render();
    // simulated technician replies (Photon human-in-the-loop)
    setTimeout(() => { const w = st.wo.find((w) => w.bid === bid && w.status === "sent"); if (!w) return; w.status = "accepted"; w.updates.push("photo received: crew on site"); text(tech, `On it. Crew on site at ${b.name}. [photo attached]`, "in"); render(); }, 2500);
    setTimeout(() => { st.wo.filter((w) => w.bid === bid).forEach((w) => { w.status = "done"; w.updates.push("done"); }); text(tech, `DONE. ${b.name}: all tasks complete.`, "in"); render(); }, 6000);
  }
  function offerHelpSite(bid) {
    const b = D.buildings.find((x) => x.id === bid);
    if (st.cbre.some((s) => s.bid === bid)) return;
    st.cbre.push({ id: "CBRE-" + bid, bid, city: b.city, type: "cbre_help_site", name: `${b.name} (CBRE help site)`, address: b.name, c: b.c, cap: b.host_capacity, used: 0, util: b.util });
    toast(`<b>${b.name}</b> is now a community help site · ${b.host_capacity} spots`);
    render();
  }
  function residentText(body) {
    st.n++;
    const who = "Resident " + (st.n + 100);
    text(who, body, "in");
    const r = M.route(S(), allSites(), H(), body, st.n);
    if (r.urgent) {
      st.refs.push({ who, body, need: r.need, from: r.from, status: "urgent" });
      text(who, "If anyone is in danger or needs oxygen/medical help, call 911 now. A coordinator has been alerted to your message.");
    } else if (r.site) {
      r.site.used += r.need.people;
      st.refs.push({ who, body, need: r.need, from: r.from, site: r.site.id, dist: r.dist, status: "routed" });
      const es = r.need.lang === "es";
      text(who, es
        ? `Vaya a ${r.site.name}, ${r.site.address} (${r.dist.toFixed(1)} mi). Abierto, ${r.site.cap - r.site.used} lugares. Mapa: maps.google.com/?q=${r.site.c[1]},${r.site.c[0]}`
        : `Go to ${r.site.name}, ${r.site.address} (${r.dist.toFixed(1)} mi). Open now, ${r.site.cap - r.site.used} spots left.${r.site.type === "claim_site" ? " Bring your policy number if you have it." : ""} Map: maps.google.com/?q=${r.site.c[1]},${r.site.c[0]}`);
    } else {
      st.refs.push({ who, body, need: r.need, from: r.from, status: "unrouted" });
      text(who, "We're finding you a safe place. A coordinator will text you within 15 minutes.");
    }
    render();
  }
  function rerouteUnsafe() {
    for (const ref of st.refs.filter((r) => r.status === "routed" || r.status === "rerouted")) {
      const site = allSites().find((x) => x.id === ref.site);
      if (!site || M.siteStatus(S(), site, H()) === "open") continue;
      site.used = Math.max(0, site.used - ref.need.people);
      const r = M.route(S(), allSites(), H(), ref.body, 0, [site.id]);
      if (r.site) { r.site.used += ref.need.people; ref.site = r.site.id; ref.dist = M.distMi(ref.from, r.site.c); ref.status = "rerouted";
        text(ref.who, `Change of plan: ${site.name} is no longer safe. Go to ${r.site.name}, ${r.site.address} instead.`); }
    }
  }

  // ---------- map ----------
  // Offline backdrop (venue Wi-Fi down / tiles blocked): approximate highways + Gulf water, clearly not a real basemap.
  const FALLBACK_STYLE = { version: 8, sources: { ctx: { type: "geojson", data: window.BRACE_CONTEXT } }, layers: [
    { id: "bg", type: "background", paint: { "background-color": "#eef1ec" } },
    { id: "gulf", type: "fill", source: "ctx", filter: ["==", ["get", "k"], "water"], paint: { "fill-color": "#cfe3f2" } },
    { id: "roads", type: "line", source: "ctx", filter: ["==", ["get", "k"], "road"], paint: { "line-color": "#ffffff", "line-width": ["interpolate", ["linear"], ["zoom"], 8, 2, 13, 7] } },
    { id: "roads-edge", type: "line", source: "ctx", filter: ["==", ["get", "k"], "road"], paint: { "line-color": "#d4dbd2", "line-width": 1, "line-gap-width": ["interpolate", ["linear"], ["zoom"], 8, 2, 13, 7] } } ] };
  const map = new maplibregl.Map({ container: "map", style: "https://tiles.openfreemap.org/styles/liberty", center: S().center, zoom: S().zoom, attributionControl: { compact: true } });
  let styled = false;
  map.on("style.load", () => { styled = true; addLayers(); drawHazard(); });
  setTimeout(() => { if (!styled) { console.warn("Basemap unreachable, using plain background"); map.setStyle(FALLBACK_STYLE); } }, 4000);

  function mpp0(lat) { return 156543.03 * Math.cos(lat * Math.PI / 180); }
  function widthExpr(lat) {
    const k = 1 / mpp0(lat);
    return ["interpolate", ["exponential", 2], ["zoom"], 0, ["*", ["get", "w"], k], 22, ["*", ["get", "w"], k * 4194304]];
  }
  function circlePoly(c, rMi, n = 72) {
    const pts = []; const kx = Math.cos(c[1] * Math.PI / 180) * 69;
    for (let i = 0; i <= n; i++) { const a = (i / n) * 2 * Math.PI; pts.push([c[0] + Math.cos(a) * rMi / kx, c[1] + Math.sin(a) * rMi / 69]); }
    return { type: "Polygon", coordinates: [pts] };
  }
  function ellipsePoly(a, n = 90) {
    const pts = []; for (let i = 0; i <= n; i++) { const t = (i / n) * 2 * Math.PI; pts.push([a.center[0] + Math.cos(t) * a.rx, a.center[1] + Math.sin(t) * a.ry]); }
    return { type: "Polygon", coordinates: [pts] };
  }
  const fc = (features) => ({ type: "FeatureCollection", features });
  function addLayers() {
    const lat = S().center[1];
    for (const id of ["water", "pools", "area", "track", "waves", "refs"]) if (!map.getSource(id)) map.addSource(id, { type: "geojson", data: fc([]) });
    if (map.getLayer("water")) return;
    map.addLayer({ id: "area", type: "fill", source: "area", paint: { "fill-color": ["get", "col"], "fill-opacity": ["get", "op"] } });
    map.addLayer({ id: "area-edge", type: "line", source: "area", paint: { "line-color": ["get", "edge"], "line-width": 2, "line-dasharray": [3, 2] } });
    map.addLayer({ id: "pools", type: "fill", source: "pools", paint: { "fill-color": ["get", "col"], "fill-opacity": ["get", "op"] } });
    map.addLayer({ id: "water", type: "line", source: "water", layout: { "line-cap": "round", "line-join": "round" },
      paint: { "line-color": ["get", "col"], "line-width": widthExpr(lat), "line-opacity": ["get", "op"], "line-blur": 6 } });
    map.addLayer({ id: "waves", type: "line", source: "waves", paint: { "line-color": "#d9f1ff", "line-width": 3, "line-opacity": 0.9, "line-dasharray": [0, 4, 3] } });
    map.addLayer({ id: "track", type: "line", source: "track", paint: { "line-color": ["get", "col"], "line-width": 3, "line-dasharray": [2, 2] } });
    map.addLayer({ id: "refs", type: "line", source: "refs", paint: { "line-color": "#7a5af8", "line-width": 2.5, "line-dasharray": [1, 1.5] } });
  }
  function drawHazard() {
    if (!styled || !map.getSource("water")) return;
    const s = S(), h = H(), ph = step().phase, show = st.layers.hazard;
    const f = ph === "forecast" ? 1 : M.presentFactor(h);
    const water = [], pools = [], area = [], waves = [], track = [];
    const bands = [[1, 0.25], [0.66, 0.35], [0.33, 0.45]];
    if (show && s.rivers) for (const r of s.rivers) for (const [fr, op] of bands) {
      if (f <= 0) break;
      const col = ph === "forecast" ? "#8b7cf6" : s.kind === "surge" ? (fr < 0.5 ? "#0b3d66" : "#1565a8") : (fr < 0.5 ? "#0d4fa8" : "#2f80ed");
      water.push({ type: "Feature", properties: { w: 2 * r.hw * fr * f * 1609, col, op: ph === "forecast" ? op * 0.6 : op }, geometry: { type: "LineString", coordinates: r.coords } });
    }
    if (show && s.pools) for (const p of s.pools) for (const [fr, op] of bands) {
      if (f <= 0) break;
      pools.push({ type: "Feature", properties: { col: ph === "forecast" ? "#8b7cf6" : "#2f80ed", op: ph === "forecast" ? op * 0.6 : op }, geometry: circlePoly(p.center, p.radius * fr * Math.max(f, 0.4)) });
    }
    if (show && s.kind === "winter") {
      const t = s.temps[String(h)];
      const op = ph === "forecast" ? 0.18 : t <= 10 ? 0.42 : t <= 25 ? 0.3 : 0.08;
      area.push({ type: "Feature", properties: { col: "#f4f9ff", op, edge: ph === "forecast" ? "#7a5af8" : "#9ec5ea" }, geometry: ellipsePoly(s.area) });
    }
    if (show && s.kind === "surge" && ph !== "forecast" && f > 0.2) waves.push({ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: s.rivers[0].coords } });
    if (show && s.wind) track.push({ type: "Feature", properties: { col: ph === "forecast" ? "#7a5af8" : "#5b6b78" }, geometry: { type: "LineString", coordinates: s.wind.track } });
    map.getSource("water").setData(fc(water)); map.getSource("pools").setData(fc(pools)); map.getSource("area").setData(fc(area));
    map.getSource("waves").setData(fc(waves)); map.getSource("track").setData(fc(track));
    const refs = st.refs.filter((r) => r.site).map((r) => ({ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: [r.from, allSites().find((x) => x.id === r.site).c] } }));
    map.getSource("refs").setData(fc(st.layers.help ? refs : []));
  }

  // markers
  let markers = [];
  function clearMarkers() { markers.forEach((m) => m.remove()); markers = []; }
  function drawMarkers() {
    clearMarkers();
    const s = S(), h = H();
    if (st.layers.power) for (const [id, sub] of Object.entries(s.substations)) {
      const el = document.createElement("div");
      const down = h >= 0 && h < sub.out, pred = h < 0 && sub.out > 0;
      el.className = "smk" + (down ? " down" : pred ? " pred" : "");
      el.title = `${sub.name}: ${sub.out ? (h < 0 ? `predicted outage ${sub.out}h` : down ? `DOWN (${sub.out}h outage)` : "restored") : "stays up (critical/hardened)"}`;
      markers.push(new maplibregl.Marker({ element: el }).setLngLat(sub.c).addTo(map));
    }
    if (st.layers.help) for (const site of allSites().filter((x) => x.city === s.city)) {
      const status = M.siteStatus(s, site, h);
      const el = document.createElement("div");
      el.className = "pin " + (site.type === "cbre_help_site" ? "cbre " : "") + status;
      el.textContent = SITE_ICON[site.type] || "•";
      el.title = `${SITE_NAME[site.type]} · ${site.name} · ${status.replace("_", " ")} · ${site.cap - site.used}/${site.cap} spots`;
      markers.push(new maplibregl.Marker({ element: el }).setLngLat(site.c).addTo(map));
    }
    if (st.layers.help) for (const r of st.refs) {
      const el = document.createElement("div"); el.className = "res"; el.title = `${r.who}: "${r.body}"`;
      markers.push(new maplibregl.Marker({ element: el }).setLngLat(r.from).addTo(map));
    }
    if (st.layers.buildings) for (const b of D.buildings.filter(inCity)) {
      const i = impactOf(b);
      const el = document.createElement("div");
      el.className = "bmk" + (st.sel === b.id ? " sel" : "") + (st.approvals[b.id] ? " ok" : "");
      const r = 7 + Math.sqrt(b.value / 1e8) * 1.05;
      const openWo = st.wo.filter((w) => w.bid === b.id && w.status !== "done").length;
      el.innerHTML = `<div class="c" style="width:${2 * r}px;height:${2 * r}px;background:${RISK[i.risk]}">${st.layers.wo && openWo ? `<span class="wo">${openWo}</span>` : ""}</div>
        <div class="l">${b.name} · <b style="color:${RISK[i.risk]}">${i.net > 0 ? fmt(i.net) : "safe"}</b>${st.approvals[b.id] ? " · protected" : ""}</div>`;
      el.title = `${b.name} · ${i.risk.toUpperCase()} · ${i.drivers[0] || "no exposure"}`;
      el.addEventListener("click", (e) => { e.stopPropagation(); st.sel = b.id; st.view = "building"; render(); });
      markers.push(new maplibregl.Marker({ element: el, anchor: "top" }).setLngLat(b.c).setOffset([0, -r]).addTo(map));
    }
  }

  // animation: flood pulse, wave dashes, snow particles, wind rings
  const fx = $("#fx"), ctx = fx.getContext("2d");
  const flakes = Array.from({ length: 320 }, () => ({ x: Math.random(), y: Math.random(), r: 1 + Math.random() * 2.2, v: 0.0006 + Math.random() * 0.0012, d: Math.random() * 6 }));
  const DASHES = [[0, 4, 3], [0.5, 4, 2.5], [1, 4, 2], [1.5, 4, 1.5], [2, 4, 1], [2.5, 4, 0.5], [3, 4, 0], [0, 0.5, 3, 3.5], [0, 1, 3, 3], [0, 1.5, 3, 2.5], [0, 2, 3, 2], [0, 2.5, 3, 1.5], [0, 3, 3, 1], [0, 3.5, 3, 0.5]];
  let lastDash = 0, di = 0;
  function frame(t) {
    const w = fx.clientWidth, h = fx.clientHeight;
    if (fx.width !== w * devicePixelRatio) { fx.width = w * devicePixelRatio; fx.height = h * devicePixelRatio; }
    ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0); ctx.clearRect(0, 0, w, h);
    const s = S(), ph = step().phase, hh = H();
    if (styled && map.getLayer("water")) {
      const pulse = 0.82 + 0.18 * Math.sin(t / 900);
      map.setPaintProperty("water", "line-opacity", ["*", ["get", "op"], pulse]);
      map.setPaintProperty("pools", "fill-opacity", ["*", ["get", "op"], pulse]);
      if (t - lastDash > 70 && map.getLayer("waves")) { di = (di + 1) % DASHES.length; map.setPaintProperty("waves", "line-dasharray", DASHES[di]); lastDash = t; }
    }
    if (st.layers.hazard && s.kind === "winter" && (ph !== "recovery" || hh <= 48)) {
      const a = s.area, p1 = map.project([a.center[0] - a.rx, a.center[1] + a.ry]), p2 = map.project([a.center[0] + a.rx, a.center[1] - a.ry]);
      const x0 = Math.max(0, p1.x), y0 = Math.max(0, p1.y), x1 = Math.min(w, p2.x), y1 = Math.min(h, p2.y);
      const density = ph === "forecast" ? 0.35 : hh >= 48 ? 0.25 : 1;
      ctx.fillStyle = "rgba(255,255,255,.95)"; ctx.shadowColor = "rgba(90,120,160,.6)"; ctx.shadowBlur = 3;
      flakes.forEach((f, i) => {
        if (i / flakes.length > density) return;
        f.y += f.v * 16; if (f.y > 1) { f.y = 0; f.x = Math.random(); }
        const x = x0 + f.x * (x1 - x0) + Math.sin(t / 700 + f.d) * 6, y = y0 + f.y * (y1 - y0);
        ctx.beginPath(); ctx.arc(x, y, f.r, 0, 6.283); ctx.fill();
      });
      ctx.shadowBlur = 0;
    }
    if (st.layers.hazard && s.wind && (ph === "impact" || (ph === "forecast" && s.wind.peakMph > 100))) {
      const c = map.project(s.wind.eye), strong = s.wind.peakMph > 100;
      const scale = Math.pow(2, map.getZoom() - 10);
      for (let k = 1; k <= 5; k++) {
        const R = k * 34 * scale * (strong ? 1.6 : 1);
        ctx.strokeStyle = strong ? `rgba(120,140,170,${0.5 - k * 0.07})` : `rgba(140,160,190,${0.3 - k * 0.04})`; ctx.lineWidth = strong ? 4 : 2;
        for (let j = 0; j < 3; j++) { const a0 = t / (900 - k * 60) + j * 2.09 + k; ctx.beginPath(); ctx.arc(c.x, c.y, R, a0, a0 + 1.2); ctx.stroke(); }
      }
    }
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);

  // ---------- panel ----------
  function hero() {
    const s = S(), ph = step().phase, T = totals();
    $("#hero").className = "hero " + s.kind;
    $("#hero").style.backgroundImage = "";
    $("#hero").innerHTML = `<div class="hbg" style="background-image:url('${s.photo}'),url('${skyline(s.city, s.kind)}')"></div><div class="hsearch"><span>${icon("map-pin", 16)}</span><input id="q" placeholder="Search by building, tenant or city" value="${(st.q || "").replace(/"/g, "&quot;")}"></div>
      <div class="hbody"><span class="phase" style="background:${PHASE[ph]}">${ph} · ${step().label}</span>
      <h2>${s.name} · ${s.city}</h2><div class="sub">${s.realEvent}</div><div class="narr">${s.narrative[String(H())]}</div></div>
      <div class="htabs"><button data-view="overview">Overview</button><button data-view="buildings">Buildings</button><button data-view="help">Help</button></div>`;
    $("#t-net").textContent = fmt(T.net); $("#t-avoided").textContent = fmt(T.avoided);
  }
  // Drawn skyline used until a real city photo is added to demo/assets/ (photo layer sits on top when present).
  function skyline(city, kind) {
    const sky = { flood: ["#3d6c94", "#9cbfd8"], winter: ["#7d93a8", "#dbe6ef"], surge: ["#2f6a86", "#a8d0de"] }[kind];
    const B = (x, w, h, c = "#0f2230") => `<rect x="${x}" y="${300 - h}" width="${w}" height="${h}" fill="${c}"/>`;
    let city_ = "";
    if (city === "Houston") city_ = [[40, 50, 120], [95, 38, 170], [138, 60, 230], [204, 34, 150], [244, 52, 265], [302, 40, 190], [348, 70, 140], [424, 44, 210], [474, 60, 120], [540, 40, 90]].map(([x, w, h]) => B(x, w, h)).join("") + B(262, 16, 290);
    else if (city === "Dallas") city_ = [[30, 60, 110], [96, 44, 190], [146, 70, 150], [222, 40, 240], [268, 58, 175], [332, 46, 215], [384, 64, 130], [456, 50, 160], [512, 70, 100]].map(([x, w, h]) => B(x, w, h)).join("") +
      `<rect x="586" y="120" width="6" height="180" fill="#0f2230"/><circle cx="589" cy="112" r="20" fill="#0f2230"/>`;
    else city_ = [[20, 70, 60], [96, 54, 85], [156, 80, 70], [242, 46, 110], [294, 70, 75], [370, 58, 95], [434, 90, 55], [530, 60, 80]].map(([x, w, h]) => B(x, w, h)).join("") +
      `<rect x="0" y="282" width="640" height="18" fill="#2c6f8c"/>` + [70, 210, 480, 600].map((x) => `<rect x="${x}" y="215" width="5" height="70" fill="#0f2230"/><rect x="${x - 16}" y="210" width="37" height="7" fill="#0f2230"/>`).join("");
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 300" preserveAspectRatio="xMidYMax slice"><defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${sky[0]}"/><stop offset="1" stop-color="${sky[1]}"/></linearGradient></defs><rect width="640" height="300" fill="url(#g)"/>${city_}</svg>`;
    return "data:image/svg+xml;utf8," + encodeURIComponent(svg);
  }
  function layersUI() {
    const T = totals();
    const rows = [["hazard", "#2f80ed", "waves", "Hazard overlay", "overview"], ["buildings", "#d93025", "building-2", "Buildings by $ at risk", "buildings"],
      ["power", "#5f6368", "zap", "Power grid", "overview"], ["help", "#1a56c4", "map-pin", "Help sites and residents", "help"], ["wo", "#17603a", "wrench", "Work orders", "workorders"]];
    $("#layers").innerHTML = `<div class="lhead"><span style="margin-right:auto;color:var(--ink-2)">MAP LAYERS</span><button data-all="1">SELECT ALL</button><button data-all="0">CLEAR</button></div>` +
      rows.map(([k, col, ic, l, view]) => `<div class="lrow"><span class="ic" style="background:${col}">${icon(ic, 16)}</span><label data-view="${view}">${l}</label><span class="chev" data-view="${view}">${icon("chevron-right", 18)}</span><input type="checkbox" data-layer="${k}" ${st.layers[k] ? "checked" : ""}></div>`).join("");
  }
  const planCard = (p, compact) => {
    const left = p.actBy - H();
    const when = p.missed ? `<span class="badge red">MISSED · deadline ${p.actBy}h</span>` : left <= 0 ? `<span class="badge red">act now</span>` : `<span class="badge ${left <= 12 ? "amber" : "purple"}">act within ${left}h</span>`;
    return `<div class="card ${p.missed ? "missed" : "click"}" data-bid="${p.building.id}">
      <div class="row between"><div class="title">${p.building.name}</div>${when}</div>
      <div class="small" style="margin:4px 0">${p.actions.map((a) => a.title).join(" · ")}</div>
      <div class="row between"><div class="num">${p.missed ? `would have saved <b>${fmt(p.avoided)}</b> for ${fmt(p.cost)}` : `cost <b>${fmt(p.cost)}</b> → saves <b>${fmt(p.avoided)}</b> <span class="roi">${Math.round(p.roi)}×</span>`}</div>
      ${p.missed || compact ? "" : `<button class="btn sm" data-approve="${p.building.id}">Approve</button>`}</div></div>`;
  };
  function viewOverview() {
    const T = totals(), P = plans();
    return `<h3>Portfolio · this step</h3><div class="kgrid">
      <div class="kcard"><div class="k">Buildings at risk</div><div class="v num">${T.atRisk}</div></div>
      <div class="kcard"><div class="k">Gross loss</div><div class="v num">${fmt(T.gross)}</div></div>
      <div class="kcard"><div class="k">Insurance recovers</div><div class="v num" style="color:var(--low)">−${fmt(T.ins)}</div></div>
      <div class="kcard"><div class="k">Net to the business</div><div class="v num" style="color:var(--severe)">${fmt(T.net)}</div></div></div>
      <h3>Fix-First</h3>${P.live.slice(0, 5).map((p) => planCard(p)).join("") || `<div class="empty">No actions available at this step.</div>`}
      ${P.missed.length ? `<h3>Missed</h3>${P.missed.map((p) => planCard(p)).join("")}` : ""}`;
  }
  function viewBuildings() {
    const q = (st.q || "").toLowerCase();
    const list = D.buildings.filter((b) => !q || (b.name + b.city + b.tenants.map((t) => t.name).join(" ")).toLowerCase().includes(q))
      .map((b) => ({ b, i: impactOf(b) })).sort((x, y) => y.i.net - x.i.net || (inCity(y.b) - inCity(x.b)));
    return `<h3>Buildings · sorted by net exposure</h3>` + list.map(({ b, i }) => `<div class="card click" data-bid="${b.id}"><div class="row between">
      <div class="row"><span class="dot" style="background:${RISK[i.risk]}"></span><div><div class="title">${TYPE_ICON[b.type] || ""} ${b.name}</div><div class="small">${b.city} · ${b.type.replace("_", " ")}</div></div></div>
      <div class="num big" style="font-size:16px">${inCity(b) ? fmt(i.net) : "—"}</div></div></div>`).join("");
  }
  function viewBuilding() {
    const b = D.buildings.find((x) => x.id === st.sel); if (!b) return viewOverview();
    const i = impactOf(b), m = i.money, ap = st.approvals[b.id];
    const p = ap ? null : M.bestPlan(S(), b, H()), init = initialPlan(b);
    const missed = !ap && init && H() > init.actBy;
    const max = Math.max(m.gross, 1);
    const bar = (label, v, cls = "") => `<div class="r"><span>${label}</span><div class="bar ${cls}" style="width:${Math.max(2, (v / max) * 100)}%"></div><span class="amt num">${cls === "neg" ? "−" : ""}${fmt(v)}</span></div>`;
    const canHost = b.can_host && inCity(b) && i.net === 0 && !st.cbre.some((s) => s.bid === b.id);
    return `<div class="row between" style="margin-top:12px"><button class="btn ghost sm" data-view="overview">Back</button><span class="badge" style="background:${RISK[i.risk]};color:#fff">${i.risk.toUpperCase()}</span></div>
      <div class="bname">${TYPE_ICON[b.type] || ""} ${b.name}</div><div class="small">${b.city} · ${b.type.replace("_", " ")} · ${(b.sqft / 1000).toFixed(0)}k sq ft · value ${fmt(b.value)}</div>
      <h3>Fragmented data → one record</h3><div class="chips">${b.data_sources.map((d) => `<span class="chip">${d}</span>`).join("")}</div>
      ${inCity(b) ? `<h3>Why</h3>${i.chain.length ? `<div class="chain">${i.chain.map((c) => `<span>${c}</span>`).join("<i>→</i>")}</div>` : ""}
      <ul class="drivers">${i.drivers.map((d) => `<li>${d}</li>`).join("") || "<li>No exposure at this step</li>"}</ul>
      <h3>What it costs the business</h3><div class="wf">${bar("Property damage", m.property)}${bar("Rent abatement", m.rent)}${bar("Tenant SLA penalties", m.sla)}${bar("Operations", m.ops)}${bar("Insurance recovers", m.insurance, "neg")}${bar("Net exposure", m.net, "net")}
      <div class="small">Downtime ≈ ${m.downtimeDays.toFixed(0)} days</div></div>
      <h3>Action plan</h3>
      ${ap ? `<div class="card done"><div class="title">Approved at ${ap.at}h</div><div class="small">${ap.plan.actions.map((a) => a.title).join(" · ")}</div><div class="num">saves ${fmt(Math.max(0, baselineOf(b).net - i.net))}</div></div>` : ""}
      ${missed ? planCard({ ...init, missed: true }) : ""}${p ? planCard(p) : !ap && !missed ? `<div class="empty">No action pays for itself here.</div>` : ""}
      ${canHost ? `<div class="card"><div class="title">Offer as community help site</div><div class="small">Predicted safe with power. ${b.host_capacity} spots for residents routed by Operation Storm.</div><button class="btn sm" data-host="${b.id}" style="margin-top:6px">Offer</button></div>` : ""}` : `<div class="empty">Not in this scenario's hazard area.</div>`}
      <h3>Tenants</h3><table class="t"><tr><th>Tenant</th><th>Rent/day</th><th>SLA/h</th></tr>${b.tenants.map((t) => `<tr><td>${t.name}</td><td class="num">${fmt(t.rent_per_day_cents)}</td><td class="num">${t.sla_penalty_per_hour_cents ? fmt(t.sla_penalty_per_hour_cents) : "—"}</td></tr>`).join("")}</table>
      <h3>Work orders</h3>${woList(st.wo.filter((w) => w.bid === b.id))}`;
  }
  function woList(list) {
    return list.map((w) => `<div class="card"><div class="row between"><div class="title">${w.id} · ${w.action}</div><span class="badge ${w.status === "done" ? "green" : w.status === "blocked" ? "red" : "blue"}">${w.status}</span></div>
      <div class="small">${w.b} · ${w.who}${w.updates.length ? " · " + w.updates.join(" · ") : ""}</div></div>`).join("") || `<div class="empty">No work orders yet. Approve a plan to create them.</div>`;
  }
  function viewFixFirst() {
    const P = plans(), hosts = D.buildings.filter((b) => inCity(b) && b.can_host && impactOf(b).net === 0 && !st.cbre.some((s) => s.bid === b.id));
    return `<h3>Fix-First · ranked by urgency, then dollars saved per dollar spent</h3>${P.live.map((p, k) => planCard(p).replace('<div class="title">', `<div class="title">#${k + 1} `)).join("") || `<div class="empty">Nothing to do at this step.</div>`}
      ${P.missed.length ? `<h3>Missed deadlines</h3>${P.missed.map((p) => planCard(p)).join("")}` : ""}
      <h3>Community actions</h3>${hosts.map((b) => `<div class="card"><div class="row between"><div><div class="title">${b.name}</div><div class="small">Offer as help site · ${b.host_capacity} spots</div></div><button class="btn sm" data-host="${b.id}">Offer</button></div></div>`).join("") || `<div class="empty">No more buildings available to host.</div>`}`;
  }
  function viewHelp() {
    const s = S(), h = H();
    const sites = allSites().filter((x) => x.city === s.city);
    return `<h3>Text the help line (simulated Photon)</h3><div class="small">Try: "our apartment flooded, 2 kids, need a dry place" · "no heat and it's freezing" · "mi papá usa oxígeno"</div>
      <div class="sim"><input id="res-in" placeholder="Resident's text message…"><button class="btn" id="res-send">Send</button></div>
      <h3>Referrals (${st.refs.length})</h3>${st.refs.slice().reverse().map((r) => { const site = allSites().find((x) => x.id === r.site);
        return `<div class="card ${r.status === "urgent" || r.status === "unrouted" ? "missed" : ""}"><div class="row between"><div class="title">${r.who}</div><span class="badge ${r.status === "routed" ? "green" : r.status === "rerouted" ? "amber" : "red"}">${r.status}</span></div>
        <div class="small">"${r.body}" → needs: ${r.need.needs.join(", ")} · ${r.need.people} people</div>${site ? `<div class="small">→ <b>${site.name}</b> · ${r.dist.toFixed(1)} mi</div>` : ""}</div>`; }).join("") || `<div class="empty">No requests yet.</div>`}
      <h3>Help sites in ${s.city}</h3>${sites.map((x) => { const status = M.siteStatus(s, x, h);
        return `<div class="card"><div class="row between"><div class="title">${x.name}</div><span class="badge ${status === "open" ? "green" : status === "unsafe" ? "red" : "amber"}">${status.replace("_", " ")}</span></div>
        <div class="small">${SITE_NAME[x.type]} · ${x.cap - x.used} of ${x.cap} spots free${status === "unsafe" ? " · inside the hazard zone or no power: we won't send anyone here" : ""}</div><div class="cap"><div style="width:${(x.used / x.cap) * 100}%"></div></div></div>`; }).join("")}`;
  }
  function viewMessages() {
    return `<h3>Texts (simulated Photon)</h3><div class="small">Every text Operation Storm sends or receives. With Photon connected these go to real phones.</div>
      ${st.msgs.slice().reverse().map((m) => `<div class="msg ${m.dir}"><div class="meta">${m.dir === "out" ? "→ " : "← "}${m.party} · ${m.at}</div>${m.body}</div>`).join("") || `<div class="empty">No texts yet. Approve a plan or send a resident text.</div>`}`;
  }
  function viewReports() {
    return `<h3>Reports</h3><div class="card"><div class="title">Executive summary</div><div class="small">For owners and leadership: exposure, actions, avoided losses, missed deadlines.</div><button class="btn sm" id="rep-exec" style="margin-top:6px">Generate</button></div>
      <div class="card"><div class="title">Tenant notices</div><div class="small">One notice per affected building, sent to tenant contacts.</div><button class="btn sm" id="rep-ten" style="margin-top:6px">Generate & send</button></div>`;
  }
  function execReport() {
    const s = S(), T = totals(), P = plans();
    const rows = D.buildings.filter(inCity).map((b) => ({ b, i: impactOf(b) })).sort((x, y) => y.i.net - x.i.net);
    $("#modalbox").innerHTML = `<div class="row between noprint"><span class="badge green">Operation Storm · Executive summary</span><div><button class="btn ghost sm" onclick="window.print()">Print / PDF</button> <button class="btn sm" id="close">Close</button></div></div>
      <h1>${s.name} · ${s.city} portfolio impact</h1><div class="small">${s.realEvent} · status at ${step().label} (${step().phase}) · illustrative data</div>
      <h2>Bottom line</h2><p>Gross loss <b>${fmt(T.gross)}</b>, insurance recovers <b>${fmt(T.ins)}</b>, net exposure to the business <b>${fmt(T.net)}</b>. Approved actions have avoided <b>${fmt(T.avoided)}</b> so far.</p>
      <h2>Buildings</h2><table class="t"><tr><th>Building</th><th>Risk</th><th>Net</th><th>Top driver</th></tr>${rows.map(({ b, i }) => `<tr><td>${b.name}</td><td>${i.risk}</td><td class="num">${fmt(i.net)}</td><td>${i.drivers[0] || "—"}</td></tr>`).join("")}</table>
      <h2>Actions</h2><ul>${Object.entries(st.approvals).map(([bid, a]) => `<li>Approved at ${a.at}h · ${a.plan.building.name}: ${a.plan.actions.map((x) => x.title).join(", ")} (cost ${fmt(a.plan.cost)})</li>`).join("") || "<li>None approved yet.</li>"}
      ${P.missed.map((p) => `<li style="color:#b42318">Missed · ${p.building.name}: deadline ${p.actBy}h passed. Would have saved ${fmt(p.avoided)} for ${fmt(p.cost)}.</li>`).join("")}</ul>
      <h2>Community</h2><p>${st.cbre.length} CBRE building(s) offered as help sites. ${st.refs.filter((r) => r.site).length} resident(s) routed to safe sites, ${st.refs.filter((r) => !r.site).length} escalated.</p>
      <h2>Work orders</h2><p>${st.wo.length} created · ${st.wo.filter((w) => w.status === "done").length} done.</p>`;
    $("#modal").classList.add("on"); $("#close").onclick = () => $("#modal").classList.remove("on");
  }
  function tenantNotices() {
    let n = 0;
    for (const b of D.buildings.filter((b) => inCity(b) && impactOf(b).net > 0)) {
      const i = impactOf(b);
      b.tenants.forEach((t) => { n++; text(t.name, `${b.name} storm notice: ${i.drivers[0] || "storm impact expected"}. Expected disruption about ${i.money.downtimeDays.toFixed(0)} days. Management is ${st.approvals[b.id] ? "executing a protection plan" : "preparing a protection plan"}. Reply with questions.`, "out", "notice", true); });
    }
    toast(`${icon("send", 14)}<b>${n} tenant notices sent.</b> See Texts.`);
    render();
  }

  function timeline() {
    $("#timeline").innerHTML = `<div class="lbl">HOUR</div><button class="arr" data-dh="-1">${icon("chevron-up", 16)}</button>` +
      D.STEPS.map((s, k) => `<button class="step ${k === st.hi ? "on" : ""}" style="--c:${PHASE[s.phase]}" data-hi="${k}" title="${s.phase}">${s.label}</button>`).join("") +
      `<button class="arr" data-dh="1">${icon("chevron-down", 16)}</button>`;
  }
  function legend() {
    const s = S();
    const hz = s.kind === "winter" ? "White = snow and ice" : s.kind === "surge" ? "Blue = storm surge · rings = wind" : "Blue = flooding, darker is deeper";
    $("#legend").innerHTML = `<div style="font-weight:600;margin-bottom:2px">Net exposure</div>${Object.entries(RISK).map(([k, c]) => `<div><span class="sw" style="background:${c}"></span>${k}</div>`).join("")}<div style="margin-top:6px;color:#6e6e73">${hz}<br>Purple = forecast · Red square = power down<br>Struck-through site = unsafe</div>`;
  }

  function render() {
    hero(); layersUI(); timeline(); legend(); renderContent(); drawHazard(); drawMarkers();
  }
  function renderContent() {
    const v = { overview: viewOverview, buildings: viewBuildings, building: viewBuilding, fixfirst: viewFixFirst, workorders: () => `<h3>Work orders</h3>` + woList(st.wo.slice().reverse()), help: viewHelp, messages: viewMessages, reports: viewReports }[st.view] || viewOverview;
    $("#content").innerHTML = v();
    document.querySelectorAll(".htabs button").forEach((b) => b.classList.toggle("on", b.dataset.view === st.view || (st.view === "building" && b.dataset.view === "buildings")));
    document.querySelectorAll("#top .tbtn[data-view]").forEach((b) => b.classList.toggle("on", b.dataset.view === st.view));
  }

  // ---------- events ----------
  document.body.addEventListener("click", (e) => {
    const t = e.target.closest("[data-view],[data-hi],[data-dh],[data-approve],[data-host],[data-bid],[data-all],#res-send,#rep-exec,#rep-ten");
    if (!t) return;
    if (t.dataset.all) { Object.keys(st.layers).forEach((k) => (st.layers[k] = t.dataset.all === "1")); render(); return; }
    if (t.dataset.approve) { e.stopPropagation(); approve(t.dataset.approve); return; }
    if (t.dataset.host) { offerHelpSite(t.dataset.host); return; }
    if (t.dataset.view) { st.view = t.dataset.view; render(); return; }
    if (t.dataset.hi !== undefined) { setHour(+t.dataset.hi); return; }
    if (t.dataset.dh) { setHour(Math.max(0, Math.min(D.STEPS.length - 1, st.hi + +t.dataset.dh))); return; }
    if (t.dataset.bid) { st.sel = t.dataset.bid; st.view = "building"; const b = D.buildings.find((x) => x.id === st.sel); if (inCity(b)) map.flyTo({ center: b.c, zoom: Math.max(map.getZoom(), 13.5), pitch: st.tilt ? 50 : 0 }); render(); return; }
    if (t.id === "res-send") { const v = $("#res-in").value.trim(); if (v) residentText(v); return; }
    if (t.id === "rep-exec") { execReport(); return; }
    if (t.id === "rep-ten") { tenantNotices(); return; }
  });
  document.body.addEventListener("change", (e) => { if (e.target.dataset.layer) { st.layers[e.target.dataset.layer] = e.target.checked; render(); } });
  document.body.addEventListener("keydown", (e) => {
    if (e.target.id === "res-in" && e.key === "Enter") { const v = e.target.value.trim(); if (v) residentText(v); return; }
    if (e.target.tagName === "INPUT") return;
    if (e.key === "ArrowDown" || e.key === "ArrowRight") setHour(Math.min(D.STEPS.length - 1, st.hi + 1));
    if (e.key === "ArrowUp" || e.key === "ArrowLeft") setHour(Math.max(0, st.hi - 1));
  });
  document.body.addEventListener("input", (e) => { if (e.target.id === "q") { st.q = e.target.value; st.view = "buildings"; renderContent(); } });
  document.querySelectorAll("[data-icon]").forEach((el) => { el.innerHTML = icon(el.dataset.icon, 16); });
  $("#tilt").onclick = () => { st.tilt = !st.tilt; $("#tilt").classList.toggle("on", st.tilt); map.easeTo({ pitch: st.tilt ? 55 : 0, zoom: st.tilt ? Math.max(map.getZoom(), 13) : map.getZoom() }); };
  function setHour(k) { st.hi = k; rerouteUnsafe(); render(); }
  const sel = $("#scenario");
  sel.innerHTML = Object.values(D.scenarios).map((s) => `<option value="${s.id}">${s.name} · ${s.city}</option>`).join("");
  sel.addEventListener("change", () => { reset(sel.value); map.flyTo({ center: S().center, zoom: S().zoom }); render(); });
  $("#reset").onclick = () => { reset(st.sid); render(); };
  $("#print").onclick = execReport;
  $("#home").onclick = () => map.flyTo({ center: S().center, zoom: S().zoom });
  $("#zin").onclick = () => map.zoomIn(); $("#zout").onclick = () => map.zoomOut();
  $("#modal").addEventListener("click", (e) => { if (e.target.id === "modal") $("#modal").classList.remove("on"); });

  window.BRACE_DEMO = { st: () => st, setHour, approve, residentText, offerHelpSite, select: (id) => { st.sel = id; st.view = "building"; render(); }, scenario: (id) => { sel.value = id; sel.dispatchEvent(new Event("change")); } };
  render();
})();
