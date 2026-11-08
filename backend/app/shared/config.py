"""Environment settings (docs/prd/01-architecture.md §4). Every value may be blank: sim messaging + template AI."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BACKEND_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")
    app_base_url: str = "http://localhost:5173"
    public_webhook_url: str = ""
    llm_provider: str = "none"
    llm_model: str = ""
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""
    messaging_mode: str = "sim"
    photon_api_key: str = ""
    photon_sender: str = ""
    demo_phones: str = ""          # "+12145550101:TECH-HOU-01,+14695550102:TEN-001"
    default_scenario: str = "harvey_houston"

    def demo_phone_map(self) -> dict[str, str]:
        """party_id -> phone for real phones used in the live demo."""
        out = {}
        for pair in filter(None, (p.strip() for p in self.demo_phones.split(","))):
            phone, _, party = pair.rpartition(":")
            if phone and party:
                out[party] = phone
        return out


settings = Settings()
