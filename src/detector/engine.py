import logging
from typing import Optional
from pydantic import BaseModel

from config.settings import CategoryConfig, DetectionConfig
from src.database.repository import Repository
from src.detector.filters import ProductFilter
from src.scrapers.base import ScrapedProduct

logger = logging.getLogger("price_detector")


class AnomalyResult(BaseModel):
    is_anomaly: bool
    anomaly_type: Optional[str] = None
    current_price: float
    reference_price: float
    discount_pct: float
    reason: Optional[str] = None


class PriceDetector:
    """Motor de deteção de anomalias e falhas de preço."""

    def __init__(
        self,
        repository: Repository,
        detection_config: DetectionConfig,
        product_filter: ProductFilter,
    ):
        self.repo = repository
        self.config = detection_config
        self.filter = product_filter

    def analyze_product(
        self, product: ScrapedProduct, category: CategoryConfig
    ) -> AnomalyResult:
        """
        Analisa um produto recolhido aplicando filtros e heurísticas de deteção de falha.
        """
        # 1. Filtro de falsos positivos (acessórios, scammers, reviews insuficientes)
        is_valid, discard_reason = self.filter.evaluate(product, category)
        if not is_valid:
            logger.debug(f"Produto ignorado [{product.asin}] '{product.title[:40]}...': {discard_reason}")
            return AnomalyResult(
                is_anomaly=False,
                current_price=product.current_price,
                reference_price=product.current_price,
                discount_pct=0.0,
                reason=discard_reason,
            )

        historical_avg = self.repo.get_historical_average_price(product.asin)

        # 2. Heurística 1: Comparação com histórico individual do produto na BD (mais fiável que PVP)
        if historical_avg and historical_avg > product.current_price:
            saving_hist = historical_avg - product.current_price
            drop_ratio = saving_hist / historical_avg
            if (
                drop_ratio >= self.config.min_historical_discount
                and saving_hist >= self.config.min_saving_euros
            ):
                reason = (
                    f"📉 Queda real de {drop_ratio * 100:.0f}% (-{saving_hist:.2f}€) face à média histórica "
                    f"(média: {historical_avg:.2f}€ -> atual: {product.current_price:.2f}€)"
                )
                return AnomalyResult(
                    is_anomaly=True,
                    anomaly_type="HISTORICAL_DROP",
                    current_price=product.current_price,
                    reference_price=historical_avg,
                    discount_pct=drop_ratio,
                    reason=reason,
                )

        # 3. Heurística 2: Desconto riscado oficial (PVP) com validação anti-PVP falso
        if (
            product.strikethrough_price
            and product.discount_pct
            and product.discount_pct >= self.config.min_strikethrough_discount
        ):
            saving_strike = product.strikethrough_price - product.current_price

            # Filtro A: Poupança mínima em euros (evita "descontos" de 10€ ou 20€ em produtos baratos)
            if saving_strike < self.config.min_saving_euros:
                logger.debug(
                    f"PVP descartado [{product.asin}]: Poupança de {saving_strike:.2f}€ "
                    f"inferior ao mínimo exigido ({self.config.min_saving_euros:.2f}€)"
                )
            # Filtro B: Detetar PVP artificial/inflacionado (se o preço atual coincide com o que sempre custou na BD)
            elif historical_avg and product.current_price >= historical_avg * 0.85:
                logger.debug(
                    f"PVP artificial/falso detetado [{product.asin}]: O preço atual ({product.current_price:.2f}€) "
                    f"já era o preço habitual ({historical_avg:.2f}€). O PVP riscado ({product.strikethrough_price:.2f}€) é cosmético."
                )
            else:
                reason = (
                    f"⚡ Desconto riscado extraordinário de {product.discount_pct * 100:.0f}% (-{saving_strike:.2f}€) "
                    f"(de {product.strikethrough_price:.2f}€ para {product.current_price:.2f}€)"
                )
                return AnomalyResult(
                    is_anomaly=True,
                    anomaly_type="STRIKETHROUGH_GLITCH",
                    current_price=product.current_price,
                    reference_price=product.strikethrough_price,
                    discount_pct=product.discount_pct,
                    reason=reason,
                )

        # 4. Heurística 3: Comparação com a mediana da categoria (Cold Start / Sem histórico)
        category_median = self.repo.get_category_median_price(
            category.id, exclude_asin=product.asin
        )
        if category_median and category_median > 0:
            saving_cat = category_median - product.current_price
            category_ratio = saving_cat / category_median
            if (
                category_ratio >= self.config.min_category_discount
                and saving_cat >= self.config.min_saving_euros
            ):
                reason = (
                    f"🔥 Preço {category_ratio * 100:.0f}% (-{saving_cat:.2f}€) abaixo da mediana da categoria "
                    f"({category.name}: mediana {category_median:.2f}€ -> este item: {product.current_price:.2f}€)"
                )
                return AnomalyResult(
                    is_anomaly=True,
                    anomaly_type="CATEGORY_OUTLIER",
                    current_price=product.current_price,
                    reference_price=category_median,
                    discount_pct=category_ratio,
                    reason=reason,
                )

        # Nenhuma anomalia detetada
        ref_price = product.strikethrough_price or product.current_price
        disc_pct = product.discount_pct or 0.0
        return AnomalyResult(
            is_anomaly=False,
            current_price=product.current_price,
            reference_price=ref_price,
            discount_pct=disc_pct,
            reason="Preço dentro da normalidade de mercado",
        )
