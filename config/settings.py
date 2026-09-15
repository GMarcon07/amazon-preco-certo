import os
from pathlib import Path
from typing import List, Optional
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Carregar variáveis de ambiente do .env se existir
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class AmazonConfig(BaseModel):
    base_url: str = "https://www.amazon.es"
    locale: str = "es-ES"
    timezone: str = "Europe/Madrid"
    headless: bool = True
    page_timeout_ms: int = 30000
    delay_between_requests_min: float = 3.0
    delay_between_requests_max: float = 6.5
    max_pages_per_category: int = 3


class DetectionConfig(BaseModel):
    min_strikethrough_discount: float = 0.60
    min_historical_discount: float = 0.40
    min_category_discount: float = 0.50
    min_saving_euros: float = 50.0
    min_review_count: int = 25
    min_rating: float = 3.8
    alert_cooldown_hours: int = 24


class SchedulerConfig(BaseModel):
    interval_minutes: int = 30
    jitter_seconds: int = 120


class CategoryConfig(BaseModel):
    id: str
    name: str
    search_query: str
    url_path: str
    min_price_floor: float = 0.0
    category_blacklist: List[str] = Field(default_factory=list)


class AppSettings(BaseModel):
    amazon: AmazonConfig = Field(default_factory=AmazonConfig)
    detection: DetectionConfig = Field(default_factory=DetectionConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    blacklist_keywords: List[str] = Field(default_factory=list)
    categories: List[CategoryConfig] = Field(default_factory=list)

    # Segredos obtidos das variáveis de ambiente
    discord_webhook_url: Optional[str] = None
    database_path: Path = BASE_DIR / "data" / "amazon_prices.db"


def load_settings(config_path: Optional[Path] = None) -> AppSettings:
    """Carrega as configurações a partir do YAML e variáveis de ambiente."""
    if config_path is None:
        config_path = BASE_DIR / "config" / "config.yaml"

    config_data = {}
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f) or {}

    settings = AppSettings(**config_data)

    # Injetar segredos do .env
    webhook = os.getenv("DISCORD_WEBHOOK_URL")
    if webhook:
        settings.discord_webhook_url = webhook.strip()

    # Assegurar que a pasta data/ existe
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)

    return settings
