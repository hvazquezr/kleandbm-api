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
    ksqldb_cluster: str
    ksqldb_key: str
    ksqldb_secret: str
    kafka_server: str
    kafka_username: str
    kafka_password: str
    openai_model: str
    openai_key: str

    class Config:
        env_file = Path(__file__).parent / ".env"

@lru_cache()
def get_settings():
    return Settings()