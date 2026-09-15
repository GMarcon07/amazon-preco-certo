import re
from typing import List, Optional, Tuple
from config.settings import CategoryConfig, DetectionConfig
from src.scrapers.base import ScrapedProduct


class ProductFilter:
    """Filtro de falsos positivos (acessórios, produtos sem histórico fiável, scams)."""

    def __init__(
        self,
        global_blacklist: List[str],
        detection_config: DetectionConfig,
    ):
        self.global_blacklist = [w.lower().strip() for w in global_blacklist]
        self.detection_config = detection_config

    def evaluate(
        self, product: ScrapedProduct, category: CategoryConfig
    ) -> Tuple[bool, Optional[str]]:
        """
        Avalia se o produto é legítimo e elegível para análise de falha de preço.
        Retorna (True, None) se válido, ou (False, "Motivo do descarte").
        """
        title_lower = product.title.lower()

        # 1. Piso mínimo de preço da categoria (ex: GPU < 90€ é cabo/cooler/scam)
        if category.min_price_floor > 0 and product.current_price < category.min_price_floor:
            return (
                False,
                f"Preço ({product.current_price:.2f}€) abaixo do piso mínimo para {category.name} ({category.min_price_floor:.2f}€)",
            )

        # 2. Blacklist global (acessórios gerais)
        for keyword in self.global_blacklist:
            pattern = rf"\b{re.escape(keyword)}\b"
            if re.search(pattern, title_lower):
                return False, f"Palavra-chave bloqueada (acessório global): '{keyword}'"

        # 3. Blacklist específica da categoria
        for keyword in category.category_blacklist:
            kw_lower = keyword.lower().strip()
            pattern = rf"\b{re.escape(kw_lower)}\b"
            if re.search(pattern, title_lower):
                return False, f"Palavra-chave bloqueada na categoria {category.name}: '{kw_lower}'"

        # 4. Mínimo de reviews para confiabilidade
        if product.review_count < self.detection_config.min_review_count:
            return (
                False,
                f"Poucas reviews ({product.review_count} < {self.detection_config.min_review_count})",
            )

        # 5. Avaliação mínima em estrelas
        if product.rating > 0 and product.rating < self.detection_config.min_rating:
            return (
                False,
                f"Avaliação baixa ({product.rating} < {self.detection_config.min_rating})",
            )

        return True, None
