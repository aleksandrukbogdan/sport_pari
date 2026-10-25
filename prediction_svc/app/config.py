from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "prediction-notify"
    database_url: str = (
        "postgresql+psycopg://prediction:prediction@localhost:5432/prediction"
    )
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic: str = "sports.matches"
    kafka_group_id: str = "prediction-notify"
    admin_user_ids: str = "admin"


@lru_cache
def get_settings() -> Settings:
    return Settings()
