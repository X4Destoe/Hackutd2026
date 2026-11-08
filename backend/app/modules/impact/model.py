"""The money model as a pure function (PRD 03 §3; reference implementation demo/model.js `impact`).

No store, no events, no other modules: everything comes in as arguments, so it is easy to test and fast.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.shared import schemas

from . import constants as C

WATER = ("flood", "surge")


@dataclass
class Site:
    """Everything the model needs to know about a building's situation at one step."""
    hazard: dict                     # scenarios.hazard_at(...) (damage reading)
    water_kind: str                  # "flood" or "surge"
    power_out_hours: float           # total outage duration of its utility node known at this step
    grid_down: bool
    hour: int
    utility_name: str
    in_scenario: bool = True
    actions: list[schemas.ActionTemplate] = field(default_factory=list)


def interp(points: list[tuple[float, float]], x: float) -> float:
    if x <= points[0][0]:
        return points[0][1]
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return points[-1][1]


def money_fmt(cents: float) -> str:
    d = cents / 100
    for scale, suffix in ((1e6, "M"), (1e3, "k")):
        if abs(d) >= scale:
            return f"${d / scale:.2f}".rstrip("0").rstrip(".") + suffix
    return f"${d:,.0f}"


def risk_for(net_cents: int) -> str:
    if net_cents <= 0:
        return "none"
    return next((name for limit, name in C.RISK_BANDS if net_cents < limit), "severe")


def _applies(effect: schemas.ActionEffect, has_generator: bool) -> bool:
    if effect.requires_generator and not has_generator:
        return False
    if effect.requires_no_generator and has_generator:
        return False
    return True


def zero_impact(b: schemas.Building, hour: int, driver: str) -> schemas.Impact:
    money = schemas.MoneyBreakdown(property_damage_cents=0, downtime_days=0, rent_abatement_cents=0, sla_penalty_cents=0,
                                   operations_cents=0, insurance_recovery_cents=0, net_exposure_cents=0)
    exposure = schemas.Exposure(building_id=b.id, step_hour=hour, grid_down=False, power_out_hours=0, on_generator=False)
    return schemas.Impact(building_id=b.id, step_hour=hour, risk="none", damage_ratio=0, money=money, drivers=[driver],
                          exposure=exposure, with_approved_actions=False)


def _tag(text: str, sources: dict, tags: dict) -> str:
    for key, words in tags.items():
        if key in sources and any(w in text for w in words):
            return f"{text} — {sources[key]}"
    return text


def compute(b: schemas.Building, s: Site, with_approved_actions: bool = False) -> schemas.Impact:
    if not s.in_scenario:
        return zero_impact(b, s.hour, "Not in the hazard area")
    hz, sysm = s.hazard, b.systems
    actions = [a for a in s.actions if _applies(a.effect, sysm.has_generator)]

    # power cascade: grid -> generator -> unpowered hours
    gen_hours = sysm.generator_fuel_hours + sum(a.effect.add_generator_hours or 0 for a in actions)
    unpowered = max(0.0, s.power_out_hours - gen_hours)

    # damage ratio per hazard
    water = hz.get("flood_depth_ft", 0) or 0
    above = water - b.first_floor_elev_ft
    r: dict[str, float] = {}
    if above > 0:
        fr = interp(C.FLOOD_CURVE, above) + (C.GROUND_EQUIPMENT_ADD if sysm.ground_floor_equipment else 0)
        if s.water_kind == "surge":
            fr = min(C.SURGE_CAP, fr * C.SURGE_MULT)
        r[s.water_kind] = fr
    wind = hz.get("wind_mph", 0) or 0
    if wind > C.HURRICANE_MPH:
        excess = wind - sysm.roof_wind_rating_mph
        r["wind"] = C.WIND_AT_RATING if excess <= 0 else min(C.WIND_CAP, C.WIND_BASE + C.WIND_PER_MPH * excess)
    temp, ice = hz.get("temp_f"), hz.get("ice_in", 0) or 0
    pipes = False
    if temp is not None:
        w = 0.0
        if not sysm.freeze_protection and temp <= C.FREEZE_TEMP_F and unpowered > C.FREEZE_UNPOWERED_H:
            w += min(C.PIPES_CAP, C.PIPES_BASE + C.PIPES_PER_H * (unpowered - C.FREEZE_UNPOWERED_H))
            pipes = True
        if ice >= C.ROOF_ICE_IN:
            w += C.ROOF_ICE_ADD
        if w:
            r["winter"] = w
    if hz.get("in_burn_zone"):
        r["wildfire"] = C.BURN_ZONE

    # action effects
    down_mult = sla_mult = 1.0
    for a in actions:
        e, hazards = a.effect, [str(h) for h in a.effect.hazards]
        if e.damage_mult is not None:
            for k in r:
                if hazards and k not in hazards:
                    continue
                if e.max_depth_above_floor_ft is not None and k in WATER and above > e.max_depth_above_floor_ft:
                    r[k] *= e.damage_mult_above_max if e.damage_mult_above_max is not None else 1.0
                else:
                    r[k] *= e.damage_mult
        if e.downtime_mult is not None and (not hazards or any(h in r for h in hazards)):
            down_mult *= e.downtime_mult
        if e.sla_mult is not None:
            sla_mult *= e.sla_mult

    keep = 1.0
    for x in r.values():
        keep *= 1 - x
    ratio = 1 - keep

    # dollars (cents), each line rounded so the waterfall balances exactly
    rent_day = sum(t.rent_per_day_cents for t in b.tenants)
    sla_hour = sum(t.sla_penalty_per_hour_cents for t in b.tenants)
    downtime = (ratio * C.DOWNTIME_DAYS_PER_RATIO + unpowered / 24) * down_mult
    prop = round(b.replacement_value_cents * ratio)
    rent = round(downtime * rent_day)
    sla = round(min(unpowered + downtime * 24, C.SLA_HOURS_CAP) * sla_hour * sla_mult)
    ops = round(downtime * b.sqft * C.OPS_CENTS_PER_SQFT_DAY)
    ins = b.insurance
    recovery = round(min(ins.limit_cents, max(0, prop - ins.deductible_cents)) + min(downtime, ins.bi_days_covered) * rent_day)
    net = prop + rent + sla + ops - recovery
    money = schemas.MoneyBreakdown(property_damage_cents=prop, downtime_days=round(downtime, 1), rent_abatement_cents=rent,
                                   sla_penalty_cents=sla, operations_cents=ops, insurance_recovery_cents=recovery,
                                   net_exposure_cents=net)

    # drivers, ordered by dollar contribution
    per_day = rent_day + b.sqft * C.OPS_CENTS_PER_SQFT_DAY
    damage_dollars = prop + ratio * C.DOWNTIME_DAYS_PER_RATIO * down_mult * per_day
    share = {k: damage_dollars * v / sum(r.values()) for k, v in r.items()} if r else {}
    ranked: list[tuple[float, str]] = []
    if above > 0:
        what = "storm surge" if s.water_kind == "surge" else "water"
        ranked.append((share[s.water_kind], f"{above:.1f} ft of {what} above the first floor"))
    elif water > 0:
        ranked.append((0, f"{water:.1f} ft of water at the site; first floor is {b.first_floor_elev_ft:g} ft up"))
    if "wind" in r:
        ranked.append((share["wind"], f"{wind:.0f} mph wind vs roof rated {sysm.roof_wind_rating_mph} mph"))
    if "winter" in r:
        text = f"{temp:g}°F, {unpowered:.0f}h without power, no pipe freeze protection: burst pipes" if pipes \
            else f"{ice:g} in of ice on the roof"
        ranked.append((share["winter"], text))
    if "wildfire" in r:
        ranked.append((share["wildfire"], "inside the burn zone"))
    if s.power_out_hours > 0:
        backup = f"generator covers {gen_hours:g}h" if gen_hours > 0 else "no generator"
        tail = f" → {unpowered:.0f}h without power" if unpowered > 0 else ""
        ranked.append((unpowered / 24 * down_mult * per_day, f"{s.utility_name} down {s.power_out_hours:g}h, {backup}{tail}"))
    if sla > 0:
        n = sum(1 for t in b.tenants if t.sla_penalty_per_hour_cents)
        ranked.append((sla, f"{n} critical tenant{'s' if n != 1 else ''}: SLA {money_fmt(sla_hour)}/h → {money_fmt(sla)}"))
    src = hz.get("sources") or {}  # live scenarios: which NWS alert a proxy value came from (shown, never hidden)
    if src:
        tags = {"water": ("water", "storm surge"), "wind": ("mph wind",), "winter": ("°F", "ice on the roof")}
        ranked = [(w, _tag(text, src, tags)) for w, text in ranked]
    drivers = [text for _, text in sorted(ranked, key=lambda x: -x[0])][:4]
    if recovery > 0:
        drivers.append(f"Insurance ({ins.carrier}) recovers {money_fmt(recovery)} after a {money_fmt(ins.deductible_cents)} deductible")
    if not drivers:
        drivers = ["No damage or outage expected at this step"]

    chain: list[str] = []
    if s.power_out_hours > 0:
        chain.append(f"{s.utility_name} down ({s.power_out_hours:g}h)")
        chain.append(f"generator covers {gen_hours:g}h" if gen_hours > 0 else "no backup power")
        if unpowered > 0:
            chain.append(f"{unpowered:g}h unpowered")
            if b.type == "data_center":
                chain.append("cooling lost → SLA breach")
        if pipes:
            chain.append("pipes freeze")
    if above > 0:
        chain += [f"{above:.1f} ft above first floor", f"tenants out {downtime:.0f} days"]

    since_landfall = max(s.hour, 0)
    exposure = schemas.Exposure(
        building_id=b.id, step_hour=s.hour, flood_depth_ft=round(water, 2), wind_mph=round(wind, 1), ice_in=ice, temp_f=temp,
        in_burn_zone=bool(hz.get("in_burn_zone")), grid_down=s.grid_down, power_out_hours=s.power_out_hours,
        on_generator=s.grid_down and gen_hours > since_landfall,
        generator_hours_left=max(0.0, gen_hours - since_landfall) if gen_hours > 0 else None, cause_chain=chain)
    return schemas.Impact(building_id=b.id, step_hour=s.hour, risk=risk_for(net), damage_ratio=round(ratio, 4), money=money,
                          drivers=drivers, exposure=exposure, with_approved_actions=with_approved_actions)
