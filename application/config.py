from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    auth0_domain: str
    auth0_api_audience: str
    auth0_issuer: str
    auth0_algorithms: str
    cors_allow_origins: List[str]
    cors_allow_credentials: bool
    cors_allow_methods: List[str]
    cors_allow_headers: List[str]
    api_prefix: str
    kdsqldb_cluster: str
    kdsqldb_key: str
    kdsqldb_secret:str

    class Config:
        env_file = Path(__file__).parent / ".env"

@lru_cache()
def get_settings():
    return Settings()