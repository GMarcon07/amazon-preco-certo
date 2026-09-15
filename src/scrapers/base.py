from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel
from config.settings import CategoryConfig


class ScrapedProduct(BaseModel):
    asin: str
    title: str
    url: str
    image_url: Optional[str] = None
    current_price: float
    strikethrough_price: Optional[float] = None
    discount_pct: Optional[float] = None
    rating: float = 0.0
    review_count: int = 0
    seller_name: Optional[str] = None
    is_prime: bool = False
    category_id: str


class BaseScraper(ABC):
    """Interface base para scrapers (Amazon, Worten, PCComponentes, etc.)."""

    @abstractmethod
    def start(self) -> None:
        """Inicia instâncias de navegador / sessões HTTP."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Fecha instâncias abertas de navegador / sessões."""
        pass

    @abstractmethod
    def scrape_category(self, category: CategoryConfig) -> List[ScrapedProduct]:
        """Varre os produtos de uma determinada categoria."""
        pass

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
