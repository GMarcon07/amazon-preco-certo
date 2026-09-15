import logging
import signal
import sys
import time
from typing import Optional
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config.settings import AppSettings
from src.database.db import Database
from src.database.repository import Repository
from src.detector.engine import PriceDetector
from src.detector.filters import ProductFilter
from src.notifiers.discord import DiscordNotifier
from src.scrapers.amazon import AmazonScraper

logger = logging.getLogger("orchestrator")


class PriceGlitchOrchestrator:
    """Orquestrador do ciclo completo de scan, análise e alerta."""

    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.db = Database(settings.database_path)
        self.repo = Repository(self.db)
        self.notifier = DiscordNotifier(settings.discord_webhook_url)

        product_filter = ProductFilter(
            global_blacklist=settings.blacklist_keywords,
            detection_config=settings.detection,
        )
        self.detector = PriceDetector(
            repository=self.repo,
            detection_config=settings.detection,
            product_filter=product_filter,
        )

    def run_cycle(self) -> None:
        """Executa uma ronda completa por todas as categorias configuradas."""
        logger.info("=" * 60)
        logger.info("🚀 A iniciar nova ronda de varrimento da Amazon...")
        logger.info("=" * 60)

        total_scraped = 0
        total_glitches = 0
        start_time = time.time()

        scraper = AmazonScraper(self.settings.amazon)
        try:
            with scraper:
                for category in self.settings.categories:
                    logger.info(f"\n📂 A processar categoria: {category.name} (ID: {category.id})")

                    try:
                        products = scraper.scrape_category(category)
                    except Exception as exc:
                        logger.error(f"Erro ao varrer categoria {category.name}: {exc}")
                        continue

                    total_scraped += len(products)

                    for prod in products:
                        # 1. Guardar/atualizar metadados do produto
                        self.repo.upsert_product({
                            "asin": prod.asin,
                            "title": prod.title,
                            "url": prod.url,
                            "image_url": prod.image_url,
                            "category_id": prod.category_id,
                            "rating": prod.rating,
                            "review_count": prod.review_count,
                            "seller_name": prod.seller_name,
                            "is_prime": 1 if prod.is_prime else 0,
                        })

                        # 2. Avaliar se há falha de preço / anomalia
                        anomaly = self.detector.analyze_product(prod, category)

                        # 3. Registar o preço no histórico
                        self.repo.record_price(
                            asin=prod.asin,
                            price=prod.current_price,
                            strikethrough_price=prod.strikethrough_price,
                            discount_pct=prod.discount_pct,
                            seller_name=prod.seller_name,
                        )

                        # 4. Tratar alerta se for anomalia confirmada
                        if anomaly.is_anomaly:
                            can_alert, reason = self.repo.can_send_alert(
                                prod.asin,
                                prod.current_price,
                                cooldown_hours=self.settings.detection.alert_cooldown_hours,
                            )

                            if can_alert:
                                logger.warning(
                                    f"🚨 [GLITCH DETETADO] {prod.title[:50]}... "
                                    f"Preço: {prod.current_price:.2f}€ ({anomaly.reason})"
                                )
                                sent = self.notifier.send_alert(prod, anomaly, category.name)
                                if sent:
                                    self.repo.record_alert(
                                        asin=prod.asin,
                                        price_at_alert=prod.current_price,
                                        reference_price=anomaly.reference_price,
                                        discount_pct=anomaly.discount_pct,
                                        anomaly_type=anomaly.anomaly_type or "UNKNOWN",
                                    )
                                    total_glitches += 1
                            else:
                                logger.info(
                                    f"⏳ Alerta omitido para ASIN {prod.asin} devido a cooldown: {reason}"
                                )

        except Exception as err:
            logger.error(f"Erro fatal no ciclo de monitorização: {err}", exc_info=True)

        elapsed = time.time() - start_time
        logger.info("=" * 60)
        logger.info(
            f"✅ Ronda concluída em {elapsed:.1f}s. "
            f"Total de produtos: {total_scraped} | Glitches alertados: {total_glitches}"
        )
        logger.info("=" * 60)

    def start_scheduler(self) -> None:
        """Inicia o agendador em loop contínuo com APScheduler."""
        scheduler = BlockingScheduler()

        trigger = IntervalTrigger(
            minutes=self.settings.scheduler.interval_minutes,
            jitter=self.settings.scheduler.jitter_seconds,
        )

        scheduler.add_job(
            self.run_cycle,
            trigger=trigger,
            id="amazon_price_monitor",
            name="Monitor de Falhas de Preço Amazon",
            max_instances=1,
            coalesce=True,
        )

        logger.info(
            f"⏱️ Agendador ativo! Execução a cada ~{self.settings.scheduler.interval_minutes} min "
            f"(com jitter aleatório de ±{self.settings.scheduler.jitter_seconds}s)."
        )

        # Executa uma ronda inicial imediata ao arrancar
        logger.info("▶️ A executar ronda inicial de arranque...")
        self.run_cycle()

        def handle_shutdown(signum, frame):
            logger.info("\n🛑 Sinal de terminação recebido. A encerrar agendador de forma segura...")
            scheduler.shutdown(wait=False)
            sys.exit(0)

        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)

        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Agendador encerrado.")
