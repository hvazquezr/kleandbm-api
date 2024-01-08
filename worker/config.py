from functools import lru_cache

from pydantic_settings import BaseSettings
from pathlib import Path

class CelerySettings(BaseSettings):
    broker_url: str
    result_backend: str

    class Config:
        env_file = Path(__file__).parent / ".env"

@lru_cache()
def get_celery_settings():
    return CelerySettings()