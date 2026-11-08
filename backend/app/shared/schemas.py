"""Shared models: the contract every module codes against. Mirrors docs/prd/02-contracts.md §3 (FROZEN).

Conventions: snake_case fields, money in integer USD cents, hours relative to impact (0), GeoJSON as dict.
Optional fields default to None, lists default to []. Do not add fields here without a DECISIONS.md entry.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from .enums import (BuildingType, Direction, HazardKind, MessageKind, NeedType, OverlayStyle, PartyType, Phase,
                    PlanStatus, ReportKind, ResourceStatus, ResourceType, RiskLevel, WorkOrderStatus)


class Model(BaseModel):
    model_config = ConfigDict(use_enum_values=False, populate_by_name=True)


# ---------- Portfolio (owned by scenarios) ----------
class Tenant(Model):
    id: str
    name: str
    sqft: int
    rent_per_day_cents: int
    sla_penalty_per_hour_cents: int = 0
    critical_ops: bool = False
    contact_party_id: Optional[str] = None


class Insurance(Model):
    carrier: str
    deductible_cents: int
    limit_cents: int
    bi_days_covered: int


class Systems(Model):
    has_generator: bool
    generator_fuel_hours: float = 0
    freeze_protection: bool
    flood_barriers_installed: bool = False
    roof_wind_rating_mph: int
    ground_floor_equipment: bool


class Building(Model):
    id: str
    name: str
    type: BuildingType
    city: str
    address: str
    lat: float
    lon: float
    sqft: int
    floors: int
    year_built: int
    first_floor_elev_ft: float
    replacement_value_cents: int
    utility_node_id: str
    systems: Systems
    tenants: list[Tenant] = Field(default_factory=list)
    insurance: Insurance
    onsite_party_id: str
    can_host_help_site: bool
    host_capacity: int = 0
    data_sources: list[str] = Field(default_factory=list)


class UtilityNode(Model):
    id: str
    kind: Literal["substation", "water_plant", "telecom"]
    name: str
    city: str
    lat: float
    lon: float


class Party(Model):
    id: str
    type: PartyType
    name: str
    phone: str
    language: str = "en"
    demo_live: bool = False


# ---------- Scenarios and hazard (owned by scenarios) ----------
class Overlay(Model):
    id: str
    style: OverlayStyle
    hazard: HazardKind
    geojson: dict


class UtilityOutage(Model):
    node_id: str
    hours: float


class TimelineStep(Model):
    hour: int
    phase: Phase
    label: str
    overlays: list[Overlay] = Field(default_factory=list)
    utility_outages: list[UtilityOutage] = Field(default_factory=list)
    narrative: str


class LatLon(Model):
    lat: float
    lon: float


class Scenario(Model):
    id: str
    name: str
    real_event: str
    date_label: str
    city: str
    center: LatLon
    zoom: float
    hazards: list[HazardKind] = Field(default_factory=list)
    steps: list[TimelineStep] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    disclaimer: str


class ScenarioMeta(Model):
    id: str
    name: str
    real_event: str
    date_label: str
    city: str
    hazards: list[HazardKind] = Field(default_factory=list)
    step_hours: list[int] = Field(default_factory=list)


class DemoState(Model):
    scenario_id: str
    step_hour: int
    phase: Phase
    messaging_mode: Literal["sim", "photon"]
    llm_provider: str


# ---------- Impact (owned by impact) ----------
class Exposure(Model):
    building_id: str
    step_hour: int
    flood_depth_ft: float = 0
    wind_mph: float = 0
    ice_in: float = 0
    temp_f: Optional[float] = None
    in_burn_zone: bool = False
    grid_down: bool
    power_out_hours: float
    on_generator: bool
    generator_hours_left: Optional[float] = None
    cause_chain: list[str] = Field(default_factory=list)


class MoneyBreakdown(Model):
    property_damage_cents: int
    downtime_days: float
    rent_abatement_cents: int
    sla_penalty_cents: int
    operations_cents: int
    insurance_recovery_cents: int
    net_exposure_cents: int


class Impact(Model):
    building_id: str
    step_hour: int
    risk: RiskLevel
    damage_ratio: float
    money: MoneyBreakdown
    drivers: list[str] = Field(default_factory=list)
    exposure: Exposure
    with_approved_actions: bool


class PortfolioSummary(Model):
    scenario_id: str
    step_hour: int
    buildings_at_risk: int
    gross_loss_cents: int
    net_exposure_cents: int
    avoided_cents: int
    actions_approved: int
    worst_building_ids: list[str] = Field(default_factory=list)


# ---------- Actions (owned by actions) ----------
class ActionEffect(Model):
    damage_mult: Optional[float] = None
    downtime_mult: Optional[float] = None
    sla_mult: Optional[float] = None
    add_generator_hours: Optional[float] = None
    max_depth_above_floor_ft: Optional[float] = None
    damage_mult_above_max: Optional[float] = None
    requires_generator: Optional[bool] = None
    requires_no_generator: Optional[bool] = None
    hazards: list[HazardKind] = Field(default_factory=list)  # [] = all hazards


class ActionTemplate(Model):
    code: str
    title: str
    description: str
    cost_cents: int
    act_by_hour: int
    effect: ActionEffect
    task_text: str
    tenant_notice_text: Optional[str] = None
    creates_help_site: bool = False
    community: bool = False


class PlanAction(Model):
    code: str
    title: str
    cost_cents: int
    act_by_hour: int
    feasible: bool


class Plan(Model):
    id: str
    building_id: str
    scenario_id: str
    actions: list[PlanAction] = Field(default_factory=list)
    cost_cents: int
    avoided_cents: int
    roi: float
    act_by_hour: int
    status: PlanStatus
    rationale: str
    approved_by: Optional[str] = None
    approved_at_hour: Optional[int] = None


class FixFirstItem(Model):
    rank: int
    plan_id: str
    building_id: str
    building_name: str
    title: str
    cost_cents: int
    avoided_cents: int
    roi: float
    act_by_hour: int
    hours_left: int
    why: str


class WorkOrder(Model):
    id: str
    plan_id: str
    building_id: str
    action_code: str
    party_id: str
    text: str
    status: WorkOrderStatus
    created_at_hour: int
    updates: list[str] = Field(default_factory=list)
    photo_urls: list[str] = Field(default_factory=list)


# ---------- Messaging, resources, reports ----------
class Message(Model):
    id: str
    party_id: str
    party_type: PartyType
    direction: Direction
    kind: MessageKind
    body: str
    media_urls: list[str] = Field(default_factory=list)
    work_order_id: Optional[str] = None
    referral_id: Optional[str] = None
    status: Literal["queued", "sent", "failed", "received"]
    channel: str
    created_wall: str
    error: Optional[str] = None


class MessagingStatus(Model):
    mode: Literal["sim", "photon"]
    live_parties: list[str] = Field(default_factory=list)
    sent: int
    received: int
    last_error: Optional[str] = None


class Resource(Model):
    id: str
    type: ResourceType
    name: str
    address: str
    city: str
    lat: float
    lon: float
    capacity: int
    used: int = 0
    status: ResourceStatus
    needs_served: list[NeedType] = Field(default_factory=list)
    building_id: Optional[str] = None
    utility_node_id: Optional[str] = None
    phone: Optional[str] = None
    hours: str
    source: Literal["statefarm", "city", "redcross", "partner", "cbre"]


class Referral(Model):
    id: str
    party_id: str
    needs: list[NeedType] = Field(default_factory=list)
    people: int = 1
    summary: str
    resource_id: Optional[str] = None
    distance_mi: Optional[float] = None
    status: Literal["routed", "rerouted", "unrouted", "arrived"]
    history: list[str] = Field(default_factory=list)


class Report(Model):
    id: str
    kind: ReportKind
    scenario_id: str
    building_id: Optional[str] = None
    title: str
    markdown: str
    created_wall: str


ALL_MODELS = [Tenant, Insurance, Systems, Building, UtilityNode, Party, Overlay, UtilityOutage, TimelineStep, LatLon,
              Scenario, ScenarioMeta, DemoState, Exposure, MoneyBreakdown, Impact, PortfolioSummary, ActionEffect,
              ActionTemplate, PlanAction, Plan, FixFirstItem, WorkOrder, Message, MessagingStatus, Resource, Referral,
              Report]
