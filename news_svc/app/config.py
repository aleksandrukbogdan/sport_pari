from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings.

    User accounts and the sport catalog live in other services.
    This service only stores their ids.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://news:news@localhost:5432/news"
    # Placeholder hostname. Replace when the platform service name is known.
    user_service_url: str = "http://user-svc:8000"
    catalog_service_url: str = "http://catalog-svc:8000"


settings = Settings()
