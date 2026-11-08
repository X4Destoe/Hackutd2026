"""Every curve and constant of the money model (docs/prd/03-data-and-scenarios.md §3). Illustrative, not actuarial."""

# Flood damage ratio by water depth above the first floor (ft), linear interpolation, flat beyond the ends.
FLOOD_CURVE = [(0, 0.0), (0.5, 0.05), (1, 0.10), (2, 0.18), (3, 0.24), (4, 0.28), (6, 0.35), (8, 0.42)]
GROUND_EQUIPMENT_ADD = 0.04          # extra flood ratio when equipment sits on the ground floor and water is inside
SURGE_MULT, SURGE_CAP = 1.3, 0.9     # wave action

HURRICANE_MPH = 74
WIND_AT_RATING = 0.01                # wind > 74 mph but within the roof rating
WIND_BASE, WIND_PER_MPH, WIND_CAP = 0.02, 0.004, 0.5

FREEZE_TEMP_F = 20
FREEZE_UNPOWERED_H = 8
PIPES_BASE, PIPES_PER_H, PIPES_CAP = 0.03, 0.002, 0.10
ROOF_ICE_IN, ROOF_ICE_ADD = 0.5, 0.01

BURN_ZONE = 0.65

DOWNTIME_DAYS_PER_RATIO = 180        # downtime_days = ratio × 180 + unpowered_hours / 24
SLA_HOURS_CAP = 720
OPS_CENTS_PER_SQFT_DAY = 5

# Risk band by net exposure (cents): none 0 · low < $50k · moderate < $250k · high < $1M · severe ≥ $1M
RISK_BANDS = [(5_000_000, "low"), (25_000_000, "moderate"), (100_000_000, "high")]

# help-site safety (site_safe)
SAFE_MAX_WATER_FT = 0.5
SAFE_MAX_WIND_MPH = 74
