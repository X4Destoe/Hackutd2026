"""Shared enums. Values are the wire format: see docs/prd/02-contracts.md §2 (FROZEN)."""
from enum import Enum


class StrEnum(str, Enum):
    def __str__(self) -> str:  # serialize as the plain value
        return self.value


class HazardKind(StrEnum):
    flood = "flood"; wind = "wind"; winter = "winter"; surge = "surge"; wildfire = "wildfire"


class OverlayStyle(StrEnum):
    flood_water = "flood_water"; wind_swirl = "wind_swirl"; snow_ice = "snow_ice"
    surge_water = "surge_water"; fire_smoke = "fire_smoke"; forecast_cone = "forecast_cone"


class Phase(StrEnum):
    forecast = "forecast"; impact = "impact"; recovery = "recovery"


class RiskLevel(StrEnum):
    none = "none"; low = "low"; moderate = "moderate"; high = "high"; severe = "severe"


class BuildingType(StrEnum):
    office = "office"; data_center = "data_center"; retail = "retail"
    industrial = "industrial"; multifamily = "multifamily"; medical_office = "medical_office"


class PlanStatus(StrEnum):
    proposed = "proposed"; approved = "approved"; executing = "executing"
    done = "done"; rejected = "rejected"; missed = "missed"


class WorkOrderStatus(StrEnum):
    created = "created"; sent = "sent"; accepted = "accepted"; done = "done"; blocked = "blocked"


class PartyType(StrEnum):
    technician = "technician"; tenant = "tenant"; manager = "manager"; resident = "resident"


class Direction(StrEnum):
    outbound = "outbound"; inbound = "inbound"


class MessageKind(StrEnum):
    task = "task"; task_update = "task_update"; tenant_notice = "tenant_notice"; resident_chat = "resident_chat"
    redirect = "redirect"; approval_request = "approval_request"; other = "other"


class ResourceType(StrEnum):
    shelter = "shelter"; warming_center = "warming_center"; claim_site = "claim_site"
    hotel = "hotel"; repair_vendor = "repair_vendor"; cbre_help_site = "cbre_help_site"


class ResourceStatus(StrEnum):
    open = "open"; full = "full"; unsafe = "unsafe"; closed = "closed"


class NeedType(StrEnum):
    shelter = "shelter"; warmth = "warmth"; medical = "medical"; food_water = "food_water"
    repair = "repair"; claim = "claim"; info = "info"


class ReportKind(StrEnum):
    executive_summary = "executive_summary"; tenant_notice = "tenant_notice"
