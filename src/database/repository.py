from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from src.database.db import Database


class Repository:
    def __init__(self, db: Database):
        self.db = db

    def upsert_product(self, product_data: Dict[str, Any]) -> None:
        """Insere ou atualiza os metadados do produto."""
        now = datetime.now(timezone.utc).isoformat()
        query = """
        INSERT INTO products (
            asin, title, url, image_url, category_id,
            rating, review_count, seller_name, is_prime,
            first_seen_at, last_seen_at
        ) VALUES (
            :asin, :title, :url, :image_url, :category_id,
            :rating, :review_count, :seller_name, :is_prime,
            :now, :now
        )
        ON CONFLICT(asin) DO UPDATE SET
            title = excluded.title,
            url = excluded.url,
            image_url = COALESCE(excluded.image_url, products.image_url),
            rating = excluded.rating,
            review_count = excluded.review_count,
            seller_name = COALESCE(excluded.seller_name, products.seller_name),
            is_prime = excluded.is_prime,
            last_seen_at = excluded.last_seen_at
        """
        payload = {
            "asin": product_data["asin"],
            "title": product_data["title"],
            "url": product_data["url"],
            "image_url": product_data.get("image_url"),
            "category_id": product_data["category_id"],
            "rating": product_data.get("rating", 0.0),
            "review_count": product_data.get("review_count", 0),
            "seller_name": product_data.get("seller_name"),
            "is_prime": product_data.get("is_prime", 0),
            "now": now,
        }
        with self.db.get_connection() as conn:
            conn.execute(query, payload)

    def record_price(
        self,
        asin: str,
        price: float,
        strikethrough_price: Optional[float] = None,
        discount_pct: Optional[float] = None,
        seller_name: Optional[str] = None,
    ) -> None:
        """Regista um novo ponto no histórico de preços."""
        now = datetime.now(timezone.utc).isoformat()
        query = """
        INSERT INTO price_history (
            asin, price, strikethrough_price, discount_pct, seller_name, recorded_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """
        with self.db.get_connection() as conn:
            conn.execute(
                query,
                (asin, price, strikethrough_price, discount_pct, seller_name, now),
            )

    def get_product(self, asin: str) -> Optional[Dict[str, Any]]:
        query = "SELECT * FROM products WHERE asin = ?"
        with self.db.get_connection() as conn:
            row = conn.execute(query, (asin,)).fetchone()
            return dict(row) if row else None

    def get_historical_prices(self, asin: str, limit: int = 50) -> List[float]:
        """Devolve os últimos preços registados para o produto (excluindo leituras nulas/inválidas)."""
        query = """
        SELECT price FROM price_history
        WHERE asin = ? AND price > 0
        ORDER BY recorded_at DESC
        LIMIT ?
        """
        with self.db.get_connection() as conn:
            rows = conn.execute(query, (asin, limit)).fetchall()
            return [row["price"] for row in rows]

    def get_historical_average_price(self, asin: str) -> Optional[float]:
        """Calcula a média histórica de preço para o ASIN."""
        prices = self.get_historical_prices(asin, limit=100)
        if not prices:
            return None
        return sum(prices) / len(prices)

    def get_category_median_price(
        self, category_id: str, exclude_asin: Optional[str] = None, min_samples: int = 15
    ) -> Optional[float]:
        """Calcula a mediana dos preços mais recentes de produtos na mesma categoria."""
        query = """
        SELECT ph.price
        FROM price_history ph
        INNER JOIN products p ON p.asin = ph.asin
        WHERE p.category_id = ? AND ph.price > 0
        """
        params = [category_id]
        if exclude_asin:
            query += " AND p.asin != ?"
            params.append(exclude_asin)

        query += " ORDER BY ph.recorded_at DESC LIMIT 200"

        with self.db.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            if not rows:
                return None
            prices = sorted([row["price"] for row in rows])
            n = len(prices)
            if n < min_samples:
                return None
            if n % 2 == 1:
                return prices[n // 2]
            return (prices[n // 2 - 1] + prices[n // 2]) / 2.0

    def can_send_alert(
        self, asin: str, current_price: float, cooldown_hours: int = 24
    ) -> Tuple[bool, Optional[str]]:
        """
        Verifica se deve disparar alerta.
        Não dispara se já foi alertado nas últimas `cooldown_hours` horas,
        A MENOS QUE o preço atual seja pelo menos 10% mais baixo do que no alerta anterior.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=cooldown_hours)).isoformat()
        query = """
        SELECT price_at_alert, sent_at
        FROM alerts_history
        WHERE asin = ? AND sent_at >= ?
        ORDER BY sent_at DESC
        LIMIT 1
        """
        with self.db.get_connection() as conn:
            row = conn.execute(query, (asin, cutoff)).fetchone()
            if not row:
                return True, None

            last_alert_price = row["price_at_alert"]
            # Se baixou ainda mais (pelo menos 10% de redução face ao último alerta)
            if current_price < last_alert_price * 0.90:
                return True, f"Preço caiu ainda mais face ao último alerta ({last_alert_price:.2f}€ -> {current_price:.2f}€)"

            return False, f"Alerta recente já enviado às {row['sent_at']} com preço {last_alert_price:.2f}€"

    def record_alert(
        self,
        asin: str,
        price_at_alert: float,
        reference_price: float,
        discount_pct: float,
        anomaly_type: str,
    ) -> None:
        """Regista que um alerta foi enviado para este produto."""
        now = datetime.now(timezone.utc).isoformat()
        query = """
        INSERT INTO alerts_history (
            asin, price_at_alert, reference_price, discount_pct, anomaly_type, sent_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """
        with self.db.get_connection() as conn:
            conn.execute(
                query,
                (asin, price_at_alert, reference_price, discount_pct, anomaly_type, now),
            )

    def get_stats(self) -> Dict[str, Any]:
        """Estatísticas globais da base de dados."""
        with self.db.get_connection() as conn:
            total_products = conn.execute("SELECT COUNT(*) as c FROM products").fetchone()["c"]
            total_prices = conn.execute("SELECT COUNT(*) as c FROM price_history").fetchone()["c"]
            total_alerts = conn.execute("SELECT COUNT(*) as c FROM alerts_history").fetchone()["c"]
            categories_count = conn.execute(
                "SELECT category_id, COUNT(*) as count FROM products GROUP BY category_id"
            ).fetchall()

            return {
                "total_products": total_products,
                "total_prices_logged": total_prices,
                "total_alerts_sent": total_alerts,
                "categories": {row["category_id"]: row["count"] for row in categories_count},
            }
