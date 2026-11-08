"""The action catalog (backend/data/actions.json), validated against the ActionTemplate contract at import."""
import json

from app.shared.config import DATA_DIR
from app.shared.schemas import ActionTemplate

catalog: dict[str, ActionTemplate] = {
    t.code: t for t in (ActionTemplate.model_validate(a) for a in json.loads((DATA_DIR / "actions.json").read_text()))}


def is_community(code: str) -> bool:
    t = catalog.get(code)
    return bool(t and t.community)
