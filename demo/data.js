// Brace demo - seed data. Everything here is ILLUSTRATIVE: real disasters, hand-drawn approximate
// footprints, fictional buildings/tenants/dollars. Money is in cents. Hours are relative to impact (0).
/* eslint-disable */
window.BRACE_DATA = (function () {
  const STEPS = [
    { hour: -48, phase: "forecast", label: "−48h" },
    { hour: -24, phase: "forecast", label: "−24h" },
    { hour: -12, phase: "forecast", label: "−12h" },
    { hour: 0, phase: "impact", label: "0h" },
    { hour: 12, phase: "impact", label: "+12h" },
    { hour: 48, phase: "recovery", label: "+48h" },
    { hour: 168, phase: "recovery", label: "+7d" },
  ];
  // How much of the peak hazard is physically present at each step (forecast steps show the predicted peak).
  const PRESENT = { "-48": 0, "-24": 0, "-12": 0, "0": 0.7, "12": 1, "48": 0.5, "168": 0.1 };

  const scenarios = {
    harvey_houston: {
      id: "harvey_houston", name: "Hurricane Harvey", city: "Houston", realEvent: "Hurricane Harvey · Aug 25–30, 2017",
      center: [-95.47, 29.75], zoom: 10.3, kind: "flood",
      narrative: {
        "-48": "Forecast: Harvey expected to stall over Houston. NWS warns of catastrophic, life-threatening rainfall.",
        "-24": "Forecast: 30–40 in. of rain possible. Bayous and reservoirs projected to overtop.",
        "-12": "Final window for pre-storm actions. Rain bands arriving.",
        "0": "Impact: Buffalo, Brays and White Oak bayous out of their banks. Substations flooding.",
        "12": "Peak flooding. Reservoir releases flood the Energy Corridor.",
        "48": "Water receding slowly. Power restoration begins in dry areas.",
        "168": "Recovery: most water gone. Demand surge for contractors and materials.",
      },
      rivers: [ // [lon,lat] polylines with peak depth (ft) at centerline and half-width (miles)
        { name: "Buffalo Bayou", peak: 8, hw: 0.55, coords: [[-95.70,29.785],[-95.64,29.772],[-95.59,29.762],[-95.54,29.760],[-95.48,29.762],[-95.44,29.764],[-95.40,29.760],[-95.375,29.762],[-95.355,29.760],[-95.33,29.752],[-95.29,29.745]] },
        { name: "Brays Bayou", peak: 10, hw: 0.9, coords: [[-95.60,29.690],[-95.54,29.690],[-95.49,29.688],[-95.46,29.690],[-95.43,29.700],[-95.40,29.708],[-95.37,29.712],[-95.34,29.715],[-95.30,29.705]] },
        { name: "White Oak Bayou", peak: 7, hw: 0.55, coords: [[-95.52,29.830],[-95.47,29.810],[-95.42,29.790],[-95.38,29.770],[-95.365,29.763]] },
      ],
      pools: [{ name: "Addicks/Barker reservoir releases", center: [-95.635, 29.775], radius: 2.1, peak: 5.4 }],
      wind: { peakMph: 55, track: [[-97.0,27.9],[-96.6,28.6],[-96.0,29.3],[-95.6,29.6]], eye: [-95.9, 29.4] },
      substations: { "UTL-HOU-SUB1": { name: "Downtown substation", c: [-95.368, 29.758], out: 96 },
        "UTL-HOU-SUB2": { name: "Galleria substation", c: [-95.455, 29.742], out: 0 },
        "UTL-HOU-SUB3": { name: "Meyerland substation", c: [-95.468, 29.692], out: 120 },
        "UTL-HOU-SUB4": { name: "Energy Corridor substation", c: [-95.622, 29.777], out: 144 },
        "UTL-HOU-SUB5": { name: "NW Houston substation", c: [-95.545, 29.852], out: 72 } },
    },
    uri_dallas: {
      id: "uri_dallas", name: "Winter Storm Uri", city: "Dallas", realEvent: "Winter Storm Uri · Feb 13–17, 2021",
      center: [-96.82, 32.84], zoom: 10.4, kind: "winter",
      narrative: {
        "-48": "Forecast: arctic outbreak. Single-digit temperatures and ice expected across North Texas.",
        "-24": "Forecast: grid operator warns of record demand. Rotating outages likely.",
        "-12": "Final window: fuel, pipe protection, tenant continuity.",
        "0": "Impact: rotating outages begin. Temperatures fall to about 5°F.",
        "12": "Outages extend for days. Buildings without heat begin freezing.",
        "48": "Thaw starts. Burst pipes discovered as heat returns.",
        "168": "Recovery: plumbers and restoration crews booked weeks out.",
      },
      temps: { "-48": 22, "-24": 15, "-12": 10, "0": 5, "12": 2, "48": 18, "168": 40 },
      ice: 0.3,
      area: { center: [-96.82, 32.84], rx: 0.32, ry: 0.22 },
      substations: { "UTL-DAL-SUB1": { name: "Downtown substation", c: [-96.796, 32.784], out: 40 },
        "UTL-DAL-SUB2": { name: "Market Center (critical circuit)", c: [-96.83, 32.80], out: 0 },
        "UTL-DAL-SUB3": { name: "Farmers Branch substation", c: [-96.885, 32.92], out: 60 },
        "UTL-DAL-SUB4": { name: "Lakewood substation", c: [-96.752, 32.822], out: 50 } },
    },
    ian_fort_myers: {
      id: "ian_fort_myers", name: "Hurricane Ian", city: "Fort Myers", realEvent: "Hurricane Ian · Sep 28, 2022",
      center: [-81.88, 26.55], zoom: 10.2, kind: "surge",
      narrative: {
        "-48": "Forecast: Ian rapidly intensifying. Track shifts toward Southwest Florida.",
        "-24": "Forecast: Category 4 landfall likely. Life-threatening storm surge for Lee County.",
        "-12": "Final window: shutters, barriers, move equipment, pre-book contractors.",
        "0": "Impact: catastrophic surge on Fort Myers Beach. Hurricane-force winds inland.",
        "12": "Peak surge and wind. Widespread outages.",
        "48": "Surge recedes. Barrier islands cut off.",
        "168": "Recovery: long rebuilds on the islands. Inland sites reopen.",
      },
      rivers: [
        { name: "Gulf coast (Estero Island)", peak: 13, hw: 2.6, coords: [[-82.00,26.50],[-81.97,26.47],[-81.95,26.455],[-81.92,26.44],[-81.89,26.42],[-81.86,26.39],[-81.83,26.36]] },
        { name: "Caloosahatchee River", peak: 7, hw: 1.0, coords: [[-82.00,26.52],[-81.95,26.55],[-81.90,26.60],[-81.87,26.645],[-81.84,26.66],[-81.80,26.69],[-81.75,26.71]] },
      ],
      pools: [],
      wind: { peakMph: 150, track: [[-82.7,25.6],[-82.45,26.2],[-82.25,26.69],[-81.95,27.05],[-81.5,27.6]], eye: [-82.25, 26.69] },
      substations: { "UTL-FMY-SUB1": { name: "Downtown Fort Myers substation", c: [-81.866, 26.638], out: 120 },
        "UTL-FMY-SUB2": { name: "Inland hardened substation", c: [-81.828, 26.553], out: 0 },
        "UTL-FMY-SUB3": { name: "Fort Myers Beach substation", c: [-81.942, 26.452], out: 240 } },
    },
  };

  const T = (id, name, sqft, rentPerSqftYr, sla = 0, critical = false) =>
    ({ id, name, sqft, rent_per_day_cents: Math.round(sqft * rentPerSqftYr * 100 / 365), sla_penalty_per_hour_cents: sla, critical_ops: critical });
  const SRC = ["Lease abstracts", "BMS telemetry", "Utility map", "Insurance SOV", "Work orders"];
  const B = (o) => Object.assign({ data_sources: SRC, can_host: false, host_capacity: 0 }, o);

  const buildings = [
    B({ id: "BLD-HOU-01", name: "Bayou Plaza", type: "office", city: "Houston", c: [-95.3625, 29.7567], sqft: 420000, value: 62e8, floorFt: 1.0, groundEquip: true, gen: 18, freeze: true, roofMph: 110, util: "UTL-HOU-SUB1", tech: "TECH-HOU-01",
      tenants: [T("TEN-001", "Harbor Legal LLP", 120000, 38), T("TEN-002", "Gulfline Energy", 210000, 36), T("TEN-003", "Bayou Coffee Co.", 4000, 45)], ins: { carrier: "State Farm", ded: 0.03, bi: 60 } }),
    B({ id: "BLD-HOU-02", name: "Northwest Data Hub", type: "data_center", city: "Houston", c: [-95.538, 29.849], sqft: 180000, value: 95e8, floorFt: 4.0, groundEquip: false, gen: 30, freeze: true, roofMph: 130, util: "UTL-HOU-SUB5", tech: "TECH-HOU-01",
      tenants: [T("TEN-004", "CloudCore Hosting", 90000, 60, 120000, true), T("TEN-005", "MedRecords Inc.", 50000, 60, 55000, true)], ins: { carrier: "Other", ded: 0.02, bi: 30 } }),
    B({ id: "BLD-HOU-03", name: "Meyerland Retail Center", type: "retail", city: "Houston", c: [-95.4625, 29.6885], sqft: 160000, value: 28e8, floorFt: 0.5, groundEquip: true, gen: 0, freeze: false, roofMph: 100, util: "UTL-HOU-SUB3", tech: "TECH-HOU-01",
      tenants: [T("TEN-006", "FreshMart Grocery", 60000, 22), T("TEN-007", "Meyerland Pharmacy", 12000, 30)], ins: { carrier: "State Farm", ded: 0.05, bi: 45 } }),
    B({ id: "BLD-HOU-04", name: "Galleria Medical Offices", type: "medical_office", city: "Houston", c: [-95.4605, 29.7395], sqft: 240000, value: 48e8, floorFt: 3.0, groundEquip: false, gen: 48, freeze: true, roofMph: 130, util: "UTL-HOU-SUB2", tech: "TECH-HOU-01",
      tenants: [T("TEN-008", "Uptown Clinics", 200000, 34)], ins: { carrier: "State Farm", ded: 0.03, bi: 60 }, can_host: true, host_capacity: 250 }),
    B({ id: "BLD-HOU-05", name: "Energy Corridor Tower", type: "office", city: "Houston", c: [-95.628, 29.7785], sqft: 380000, value: 54e8, floorFt: 2.0, groundEquip: true, gen: 12, freeze: true, roofMph: 110, util: "UTL-HOU-SUB4", tech: "TECH-HOU-01",
      tenants: [T("TEN-009", "Westpark Petroleum", 300000, 32)], ins: { carrier: "Other", ded: 0.03, bi: 60 } }),
    B({ id: "BLD-DAL-01", name: "Elm Street Tower", type: "office", city: "Dallas", c: [-96.799, 32.781], sqft: 350000, value: 50e8, floorFt: 2, groundEquip: false, gen: 8, freeze: true, roofMph: 110, util: "UTL-DAL-SUB1", tech: "TECH-DAL-01",
      tenants: [T("TEN-010", "Trinity Capital", 200000, 34)], ins: { carrier: "State Farm", ded: 0.02, bi: 60 } }),
    B({ id: "BLD-DAL-02", name: "Lone Star Data Center", type: "data_center", city: "Dallas", c: [-96.889, 32.924], sqft: 200000, value: 110e8, floorFt: 3, groundEquip: false, gen: 5, freeze: true, roofMph: 130, util: "UTL-DAL-SUB3", tech: "TECH-DAL-01",
      tenants: [T("TEN-011", "Prairie Cloud", 90000, 65, 1100000, true), T("TEN-012", "LoneStar Payments", 60000, 65, 900000, true), T("TEN-013", "Texas Health Data", 40000, 65, 500000, true)], ins: { carrier: "Other", ded: 0.02, bi: 30 } }),
    B({ id: "BLD-DAL-03", name: "Lakewood Retail Center", type: "retail", city: "Dallas", c: [-96.7505, 32.8185], sqft: 120000, value: 22e8, floorFt: 1, groundEquip: false, gen: 0, freeze: false, roofMph: 100, util: "UTL-DAL-SUB4", tech: "TECH-DAL-01",
      tenants: [T("TEN-014", "Lakewood Grocers", 50000, 24), T("TEN-015", "Bluebonnet Fitness", 30000, 22)], ins: { carrier: "State Farm", ded: 0.02, bi: 45 } }),
    B({ id: "BLD-DAL-04", name: "Market Center Expo Hall", type: "retail", city: "Dallas", c: [-96.8265, 32.8015], sqft: 300000, value: 40e8, floorFt: 1, groundEquip: false, gen: 24, freeze: true, roofMph: 110, util: "UTL-DAL-SUB2", tech: "TECH-DAL-01",
      tenants: [T("TEN-016", "Dallas Market Events", 300000, 18)], ins: { carrier: "State Farm", ded: 0.02, bi: 60 }, can_host: true, host_capacity: 400 }),
    B({ id: "BLD-FMY-01", name: "Riverside Commons", type: "office", city: "Fort Myers", c: [-81.8705, 26.6415], sqft: 150000, value: 24e8, floorFt: 3, groundEquip: true, gen: 12, freeze: true, roofMph: 130, util: "UTL-FMY-SUB1", tech: "TECH-FMY-01",
      tenants: [T("TEN-017", "Caloosa Law Group", 60000, 30), T("TEN-018", "SWFL Title Co.", 30000, 30)], ins: { carrier: "State Farm", ded: 0.05, bi: 45 } }),
    B({ id: "BLD-FMY-02", name: "Gulf Coast Medical Pavilion", type: "medical_office", city: "Fort Myers", c: [-81.829, 26.5535], sqft: 180000, value: 36e8, floorFt: 6, groundEquip: false, gen: 48, freeze: true, roofMph: 160, util: "UTL-FMY-SUB2", tech: "TECH-FMY-01",
      tenants: [T("TEN-019", "Lee Health Partners", 150000, 32)], ins: { carrier: "State Farm", ded: 0.05, bi: 60 }, can_host: true, host_capacity: 200 }),
    B({ id: "BLD-FMY-03", name: "Estero Boulevard Retail", type: "retail", city: "Fort Myers", c: [-81.9475, 26.4525], sqft: 60000, value: 14e8, floorFt: 1, groundEquip: true, gen: 0, freeze: true, roofMph: 120, util: "UTL-FMY-SUB3", tech: "TECH-FMY-01",
      tenants: [T("TEN-020", "Beach Outfitters", 20000, 40), T("TEN-021", "Salt Life Café", 6000, 45)], ins: { carrier: "State Farm", ded: 0.05, bi: 30 } }),
  ];

  // Help sites (State Farm piece). Names of real venues used in these events are marked VERIFY in the PRD.
  const sites = [
    { id: "RES-HOU-01", city: "Houston", type: "shelter", name: "Convention Center Mega-Shelter (GRB)", address: "1001 Avenida de las Americas, Houston", c: [-95.3585, 29.7515], cap: 10000, used: 7200, util: "UTL-HOU-SUB2" },
    { id: "RES-HOU-02", city: "Houston", type: "shelter", name: "NRG Center Shelter", address: "1 NRG Pkwy, Houston", c: [-95.4105, 29.6845], cap: 3000, used: 900, util: "UTL-HOU-SUB2" },
    { id: "RES-HOU-03", city: "Houston", type: "shelter", name: "Bayou Community Center Shelter", address: "Memorial Dr (generic)", c: [-95.445, 29.7635], cap: 300, used: 40, util: "UTL-HOU-SUB1" },
    { id: "RES-HOU-04", city: "Houston", type: "claim_site", name: "State Farm Catastrophe Claims Site – Galleria", address: "Post Oak Blvd lot (generic)", c: [-95.4585, 29.7425], cap: 400, used: 60, util: "UTL-HOU-SUB2" },
    { id: "RES-HOU-05", city: "Houston", type: "hotel", name: "Westside Hotel (ALE rooms)", address: "Westheimer Rd (generic)", c: [-95.555, 29.735], cap: 80, used: 30, util: "UTL-HOU-SUB2" },
    { id: "RES-DAL-01", city: "Dallas", type: "warming_center", name: "Convention Center Warming Center (KBHCC)", address: "650 S Griffin St, Dallas", c: [-96.8005, 32.7745], cap: 600, used: 150, util: "UTL-DAL-SUB2" },
    { id: "RES-DAL-02", city: "Dallas", type: "warming_center", name: "Oak Lawn Library Warming Center", address: "Oak Lawn Ave (generic)", c: [-96.808, 32.812], cap: 120, used: 20, util: "UTL-DAL-SUB4" },
    { id: "RES-DAL-03", city: "Dallas", type: "claim_site", name: "State Farm Claims Site – North Dallas", address: "LBJ Fwy lot (generic)", c: [-96.80, 32.915], cap: 300, used: 20, util: "UTL-DAL-SUB2" },
    { id: "RES-DAL-04", city: "Dallas", type: "hotel", name: "Love Field Hotel (ALE rooms)", address: "Mockingbird Ln (generic)", c: [-96.849, 32.845], cap: 60, used: 25, util: "UTL-DAL-SUB2" },
    { id: "RES-FMY-01", city: "Fort Myers", type: "shelter", name: "Lee County Inland Shelter", address: "Inland Fort Myers (generic)", c: [-81.78, 26.60], cap: 1500, used: 600, util: "UTL-FMY-SUB2" },
    { id: "RES-FMY-02", city: "Fort Myers", type: "shelter", name: "Beachside Rec Center", address: "Estero Blvd (generic)", c: [-81.944, 26.4555], cap: 200, used: 10, util: "UTL-FMY-SUB3" },
    { id: "RES-FMY-03", city: "Fort Myers", type: "claim_site", name: "State Farm Claims Site – Fort Myers", address: "Colonial Blvd lot (generic)", c: [-81.84, 26.585], cap: 300, used: 15, util: "UTL-FMY-SUB2" },
    { id: "RES-FMY-04", city: "Fort Myers", type: "hotel", name: "Daniels Parkway Hotel (ALE rooms)", address: "Daniels Pkwy (generic)", c: [-81.80, 26.548], cap: 70, used: 20, util: "UTL-FMY-SUB2" },
  ];

  const actions = [
    { code: "FLOOD_BARRIERS", title: "Deploy temporary flood barriers", cost: 1800000, actBy: -12, hazards: ["flood", "surge"], damage: 0.3, maxDepth: 3, damageAbove: 0.85, task: "deploy temporary flood barriers at all ground-level entrances", notice: "Ground-floor entrances will be closed while flood barriers are in place." },
    { code: "SANDBAGS", title: "Sandbag entrances", cost: 250000, actBy: -6, hazards: ["flood", "surge"], damage: 0.85, maxDepth: 1.5, damageAbove: 1, task: "sandbag all ground-floor entrances and loading docks" },
    { code: "RELOCATE_EQUIPMENT", title: "Move ground-floor equipment up", cost: 600000, actBy: -6, hazards: ["flood", "surge"], damage: 0.8, downtime: 0.7, task: "move ground-floor electrical and IT equipment to level 2 or higher", notice: "Please move servers and critical equipment off the ground floor today." },
    { code: "STORM_SHUTTERS", title: "Install storm shutters", cost: 2200000, actBy: -24, hazards: ["wind"], damage: 0.55, task: "install storm shutters on all exposed glazing" },
    { code: "SECURE_ROOFTOP", title: "Secure rooftop units and debris", cost: 350000, actBy: -12, hazards: ["wind"], damage: 0.8, task: "strap rooftop units and clear loose roof debris" },
    { code: "GENERATOR_FUEL", title: "Top off and pre-book fuel delivery", cost: 380000, actBy: -6, hazards: [], addGen: 24, needGen: true, task: "top off generator fuel and confirm the next delivery slot" },
    { code: "RENTAL_GENERATOR", title: "Rent and hook up a portable generator", cost: 950000, actBy: -24, hazards: [], addGen: 72, needNoGen: true, task: "receive and connect a rental generator to the transfer switch" },
    { code: "TENANT_CONTINUITY", title: "Activate tenant continuity (move critical ops)", cost: 150000, actBy: -12, hazards: [], sla: 0.4, needSla: true, task: "coordinate tenant failover to their secondary site", notice: "Please activate your continuity plan and fail over critical systems before the storm." },
    { code: "PIPE_PROTECTION", title: "Drain and heat-trace exposed pipes", cost: 210000, actBy: -6, hazards: ["winter"], damage: 0.1, task: "drain exposed lines and install heat trace in mechanical rooms" },
    { code: "PRESTAGE_CONTRACTOR", title: "Pre-book a restoration contractor", cost: 500000, actBy: -24, hazards: [], downtime: 0.6, task: "confirm the restoration contractor retainer and on-site arrival time" },
    { code: "EMERGENCY_DRYOUT", title: "Emergency dry-out and mold prevention", cost: 1500000, actBy: 48, hazards: ["flood", "surge"], downtime: 0.7, task: "start emergency water extraction and drying" },
    { code: "OFFER_HELP_SITE", title: "Offer as community help site", cost: 200000, actBy: 12, hazards: [], community: true, task: "open the lobby as a community help site (staff, security, cots)" },
  ];

  const parties = {
    "TECH-HOU-01": { name: "Marcus (Houston engineer)" }, "TECH-DAL-01": { name: "Priya (Dallas engineer)" }, "TECH-FMY-01": { name: "Luis (Fort Myers engineer)" },
  };

  return { STEPS, PRESENT, scenarios, buildings, sites, actions, parties };
})();
