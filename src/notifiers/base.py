from abc import ABC, abstractmethod
from typing import Optional
from src.detector.engine import AnomalyResult
from src.scrapers.base import ScrapedProduct


class BaseNotifier(ABC):
    """Interface para canais de notificação (Discord, Telegram, etc.)."""

    @abstractmethod
    def send_alert(
        self,
        product: ScrapedProduct,
        anomaly: AnomalyResult,
        category_name: str,
    ) -> bool:
        """Envia um alerta de falha de preço."""
        pass

    @abstractmethod
    def send_test_message(self) -> bool:
        """Envia mensagem de teste para validar conectividade com o canal."""
        pass
