from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


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
    trust_gateway_headers: bool = False
    admin_api_key: str = ""
    preview_enabled: bool = True
    news_sources: dict[str, str | list[str]] = {
        "football": "https://feeds.bbci.co.uk/sport/football/rss.xml",
        "tennis": "https://feeds.bbci.co.uk/sport/tennis/rss.xml",
        "basketball": [
            "https://feeds.bbci.co.uk/sport/basketball/rss.xml",
            "https://www.cbssports.com/rss/headlines/nba/",
            "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/news?limit=100",
        ],
        "hockey": [
            "https://feeds.bbci.co.uk/sport/ice-hockey/rss.xml",
            "https://www.cbssports.com/rss/headlines/nhl/",
            "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/news?limit=100",
        ],
        "formula1": "https://feeds.bbci.co.uk/sport/formula1/rss.xml",
        "rugby": "https://feeds.bbci.co.uk/sport/rugby-union/rss.xml",
        "cricket": "https://feeds.bbci.co.uk/sport/cricket/rss.xml",
        "athletics": "https://feeds.bbci.co.uk/sport/athletics/rss.xml",
        "golf": "https://feeds.bbci.co.uk/sport/golf/rss.xml",
        "cycling": "https://feeds.bbci.co.uk/sport/cycling/rss.xml",
        "boxing": "https://feeds.bbci.co.uk/sport/boxing/rss.xml",
        "baseball": "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/news?limit=100",
    }


settings = Settings()
