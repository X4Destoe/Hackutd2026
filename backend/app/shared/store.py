"""In-memory repositories (docs/prd/modules/core.md). Single process; reset() per demo run."""
from __future__ import annotations

from typing import Any, Generic, Iterable, TypeVar

from . import ids

T = TypeVar("T")


class Repo(Generic[T]):
    def __init__(self, name: str):
        self.name = name
        self._items: dict[str, T] = {}

    def get(self, id: str) -> T | None:
        return self._items.get(id)

    def require(self, id: str) -> T:
        """Like get, but raises KeyError (the app turns it into HTTP 404)."""
        if id not in self._items:
            raise KeyError(f"{self.name}: {id} not found")
        return self._items[id]

    def list(self, **filters: Any) -> list[T]:
        """Equality filters on attributes, e.g. list(status="sent", building_id="BLD-HOU-01")."""
        items = list(self._items.values())
        for key, value in filters.items():
            items = [x for x in items if _value(getattr(x, key, None)) == _value(value)]
        return items

    def put(self, obj: T) -> T:
        self._items[getattr(obj, "id")] = obj
        return obj

    def put_all(self, objs: Iterable[T]) -> None:
        for o in objs:
            self.put(o)

    def delete(self, id: str) -> None:
        self._items.pop(id, None)

    def count(self) -> int:
        return len(self._items)

    def clear(self) -> None:
        self._items.clear()


def _value(v: Any) -> Any:
    return getattr(v, "value", v)  # compare enums by value


class Store:
    REPOS = ["buildings", "utilities", "parties", "plans", "workorders", "messages", "resources", "referrals", "reports"]

    def __init__(self):
        for name in self.REPOS:
            setattr(self, name, Repo(name))
        self.state: dict[str, Any] = {}  # DemoState and other singletons, owned by the scenarios module

    def reset(self) -> None:
        for name in self.REPOS:
            getattr(self, name).clear()
        self.state.clear()
        ids.reset_ids()


store = Store()
