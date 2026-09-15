import logging
from datetime import datetime, timezone
from typing import Optional
import requests

from src.detector.engine import AnomalyResult
from src.notifiers.base import BaseNotifier
from src.scrapers.base import ScrapedProduct

logger = logging.getLogger("discord_notifier")


class DiscordNotifier(BaseNotifier):
    """Notificador de alertas via Discord Webhook com Rich Embeds."""

    def __init__(self, webhook_url: Optional[str]):
        self.webhook_url = webhook_url

    def send_test_message(self) -> bool:
        """Envia mensagem de validação para o Webhook configurado."""
        if not self.webhook_url:
            logger.error("❌ Nenhum DISCORD_WEBHOOK_URL configurado!")
            return False

        payload = {
            "content": "🔔 **Monitor de Falhas de Preço (Amazon Gaming & Tech)**",
            "embeds": [
                {
                    "title": "✅ Teste de Conexão Bem-Sucedido!",
                    "description": (
                        "O webhook do Discord está devidamente configurado e pronto para receber "
                        "alertas de *price glitches* e anomalias de preço em tempo real."
                    ),
                    "color": 0x00FF88,  # Verde neon
                    "fields": [
                        {
                            "name": "⚙️ Status",
                            "value": "Online e operacional",
                            "inline": True,
                        },
                        {
                            "name": "🌐 Mercado",
                            "value": "Amazon Espanha / Portugal (amazon.es)",
                            "inline": True,
                        },
                    ],
                    "footer": {"text": "Amazon Price Glitch Monitor"},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ],
        }

        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=10)
            if resp.status_code in (200, 204):
                logger.info("✅ Mensagem de teste enviada ao Discord com sucesso!")
                return True
            else:
                logger.error(f"❌ Falha ao enviar teste ao Discord: HTTP {resp.status_code} - {resp.text}")
                return False
        except Exception as err:
            logger.error(f"❌ Exceção ao enviar mensagem ao Discord: {err}")
            return False

    def send_alert(
        self,
        product: ScrapedProduct,
        anomaly: AnomalyResult,
        category_name: str,
    ) -> bool:
        """Envia um alerta de falha de preço formatado como Rich Embed."""
        if not self.webhook_url:
            logger.warning(
                f"[DISCORD DESATIVADO] Alerta não enviado para ASIN {product.asin}. "
                f"Defina DISCORD_WEBHOOK_URL no .env para ativar."
            )
            return False

        # Cor do embed baseada na gravidade do desconto
        if anomaly.discount_pct >= 0.70:
            color = 0xFF0033  # Vermelho Vivo (Glitch Extremo)
            severity = "🚨 GLITCH EXTREMO DETETADO!"
        elif anomaly.discount_pct >= 0.50:
            color = 0xFF8C00  # Laranja / Ouro (Promoção Anómala)
            severity = "⚡ QUEDA DE PREÇO ANÓMALA!"
        else:
            color = 0x00CC66  # Verde
            severity = "🏷️ Oportunidade Detetada"

        title = product.title
        if len(title) > 230:
            title = title[:230] + "..."

        embed = {
            "title": title,
            "url": product.url,
            "description": f"{anomaly.reason}",
            "color": color,
            "fields": [
                {
                    "name": "💰 Preço Atual",
                    "value": f"**{product.current_price:.2f} €**",
                    "inline": True,
                },
                {
                    "name": "🏷️ Preço Referência",
                    "value": f"~~{anomaly.reference_price:.2f} €~~",
                    "inline": True,
                },
                {
                    "name": "📉 Desconto",
                    "value": f"**-{anomaly.discount_pct * 100:.0f}%**",
                    "inline": True,
                },
                {
                    "name": "⭐ Avaliações",
                    "value": f"{product.rating:.1f} ★ ({product.review_count:,} reviews)",
                    "inline": True,
                },
                {
                    "name": "🏪 Vendedor",
                    "value": product.seller_name or "Amazon / Marketplace",
                    "inline": True,
                },
                {
                    "name": "📦 Categoria",
                    "value": category_name,
                    "inline": True,
                },
            ],
            "footer": {
                "text": f"ASIN: {product.asin} • Amazon.es Monitor",
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if product.image_url:
            embed["thumbnail"] = {"url": product.image_url}

        payload = {
            "content": f"**{severity}** | Link: <{product.url}>",
            "embeds": [embed],
        }

        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=10)
            if resp.status_code in (200, 204):
                logger.info(f"✅ Alerta de falha de preço enviado ao Discord: ASIN {product.asin} ({product.current_price:.2f}€)")
                return True
            else:
                logger.error(f"❌ Erro ao enviar alerta ao Discord: HTTP {resp.status_code} - {resp.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Exceção ao enviar alerta Discord: {e}")
            return False
