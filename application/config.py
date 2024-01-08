from functools import lru_cache

from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    auth0_domain: str
    auth0_api_audience: str
    auth0_issuer: str
    auth0_algorithms: str

    class Config:
        env_file = Path(__file__).parent / ".env"

@lru_cache()
def get_settings():
    return Settings()