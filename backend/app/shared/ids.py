"""ID helpers (docs/prd/02-contracts.md §1). Runtime IDs come from per-prefix counters; seed IDs are fixed in data."""
from collections import defaultdict
from threading import Lock

WIDTHS = {"PLAN": 3, "WO": 3, "MSG": 4, "REF": 4, "RPT": 3}
_counters: dict[str, int] = defaultdict(int)
_lock = Lock()


def new_id(prefix: str, width: int | None = None) -> str:
    """new_id("WO") -> "WO-001", "WO-002", ... Width defaults per prefix (WIDTHS) or 3."""
    with _lock:
        _counters[prefix] += 1
        n = _counters[prefix]
    return f"{prefix}-{n:0{width or WIDTHS.get(prefix, 3)}d}"


def reset_ids() -> None:
    """Restart every counter (called by store.reset() on demo reset)."""
    with _lock:
        _counters.clear()
