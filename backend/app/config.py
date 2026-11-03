from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    modo: str = Field("demo", alias="BACKEND_MODO")
    influx_url: str = Field("http://localhost:8086", alias="INFLUX_URL")
    influx_org: str = Field("utec", alias="INFLUX_ORG")
    influx_bucket: str = Field("gemelo", alias="INFLUX_BUCKET")
    influx_token_lectura: str = Field("", alias="INFLUX_TOKEN_LECTURA")
    grupo: str = Field("grupo1", alias="GRUPO")
    sondeo_s: float = Field(2, alias="SONDEO_S", gt=0)
    cors_origenes: str = Field("", alias="CORS_ORIGENES")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    @field_validator("modo")
    @classmethod
    def validar_modo(cls, value: str) -> str:
        if value not in {"real", "demo"}:
            raise ValueError("BACKEND_MODO debe ser 'real' o 'demo'")
        return value

    @property
    def origenes_cors(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origenes.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


ROOT = Path(__file__).resolve().parents[1]
SENSORES_PATH = ROOT / "config" / "sensores.yaml"

