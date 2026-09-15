import random
import time
import logging
from typing import List, Optional
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

from config.settings import AmazonConfig, CategoryConfig
from src.scrapers.base import BaseScraper, ScrapedProduct
from src.scrapers.selectors import (
    SELECTORS,
    parse_price,
    parse_rating,
    parse_review_count,
)

logger = logging.getLogger("amazon_scraper")


class AmazonScraper(BaseScraper):
    """Scraper com Playwright configurado para Amazon.es com evasão anti-bot."""

    def __init__(self, config: AmazonConfig):
        self.config = config
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    def start(self) -> None:
        """Inicializa o Chromium com proteções anti-deteção."""
        if self._browser is not None:
            return

        logger.info("A iniciar navegador Chromium com proteções stealth...")
        self._playwright = sync_playwright().start()

        # Argumentos do Chromium para evitar deteção de automação
        args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-infobars",
            "--disable-dev-shm-usage",
            "--window-size=1920,1080",
        ]

        self._browser = self._playwright.chromium.launch(
            headless=self.config.headless,
            args=args,
        )

        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )

        self._context = self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=user_agent,
            locale=self.config.locale,
            timezone_id=self.config.timezone,
            extra_http_headers={
                "Accept-Language": "es-ES,es;q=0.9,pt-PT;q=0.8,pt;q=0.7,en;q=0.6",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
            },
        )

        # Injetar script para eliminar sinais óbvios de automação
        self._context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            window.chrome = {
                runtime: {},
            };
            """
        )

    def close(self) -> None:
        """Fecha o contexto e o navegador com segurança."""
        try:
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
        except Exception as e:
            logger.debug(f"Erro ao fechar navegador: {e}")
        finally:
            self._context = None
            self._browser = None
            self._playwright = None
            logger.info("Navegador fechado.")

    def _sleep_human(self) -> None:
        """Gera um atraso aleatório para simular comportamento humano."""
        delay = random.uniform(
            self.config.delay_between_requests_min,
            self.config.delay_between_requests_max,
        )
        time.sleep(delay)

    def _handle_cookies_banner(self, page: Page) -> None:
        """Aceita o banner de cookies da Amazon se estiver visível."""
        try:
            accept_btn = page.query_selector("#sp-cc-accept")
            if accept_btn and accept_btn.is_visible():
                accept_btn.click()
                time.sleep(0.5)
        except Exception:
            pass

    def _check_captcha(self, page: Page) -> bool:
        """Verifica se a Amazon apresentou uma página de verificação/captcha."""
        title = page.title().lower()
        if "captcha" in title or "robot check" in title:
            return True
        content = page.content().lower()
        if "introduce los caracteres que ves a continuación" in content or "type the characters you see in this image" in content:
            return True
        return False

    def scrape_category(self, category: CategoryConfig) -> List[ScrapedProduct]:
        """Varre as páginas da categoria selecionada e extrai produtos."""
        if not self._context:
            self.start()

        products: List[ScrapedProduct] = []
        page = self._context.new_page()

        try:
            for page_num in range(1, self.config.max_pages_per_category + 1):
                # Constrói o URL com paginação
                query_separator = "&" if "?" in category.url_path else "?"
                url = f"{self.config.base_url}{category.url_path}{query_separator}page={page_num}"

                logger.info(f"[{category.name}] A ler página {page_num}/{self.config.max_pages_per_category}: {url}")

                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=self.config.page_timeout_ms)
                except Exception as e:
                    logger.warning(f"Timeout ou erro ao carregar {url}: {e}")
                    continue

                self._handle_cookies_banner(page)

                if self._check_captcha(page):
                    logger.error("⚠️ Detetada página de verificação/CAPTCHA da Amazon! A aguardar backoff...")
                    time.sleep(15.0)
                    break

                # Scroll leve para carregar lazy images
                try:
                    page.evaluate("window.scrollBy(0, 700)")
                    time.sleep(0.8)
                except Exception:
                    pass

                page_products = self._extract_products_from_page(page, category)
                logger.info(f"[{category.name}] Encontrados {len(page_products)} produtos na página {page_num}.")
                products.extend(page_products)

                # Pausa antes da próxima página
                self._sleep_human()

        finally:
            page.close()

        return products

    def _extract_products_from_page(
        self, page: Page, category: CategoryConfig
    ) -> List[ScrapedProduct]:
        """Extrai todos os cartões de produtos visíveis na página."""
        cards = page.query_selector_all(SELECTORS["product_card"])
        scraped: List[ScrapedProduct] = []

        for card in cards:
            try:
                asin = card.get_attribute("data-asin")
                if not asin or len(asin) < 8:
                    continue

                # Título
                title_elem = card.query_selector(SELECTORS["title"])
                if not title_elem:
                    continue
                title = title_elem.inner_text().strip()
                if not title:
                    continue

                # Preço Atual
                price = None
                price_offscreen = card.query_selector(SELECTORS["price_offscreen"])
                if price_offscreen:
                    price = parse_price(price_offscreen.inner_text())

                # Fallback para componentes whole + fraction
                if price is None:
                    whole = card.query_selector(SELECTORS["price_whole"])
                    fraction = card.query_selector(SELECTORS["price_fraction"])
                    if whole:
                        whole_text = whole.inner_text().strip().replace(".", "").replace(",", "")
                        fraction_text = fraction.inner_text().strip() if fraction else "00"
                        price = parse_price(f"{whole_text}.{fraction_text}")

                # Se não tem preço disponível, ignorar
                if price is None or price <= 0:
                    continue

                # Preço riscado / original (se existir)
                strikethrough_price = None
                strike_elem = card.query_selector(SELECTORS["strikethrough_price"])
                if strike_elem:
                    parsed_strike = parse_price(strike_elem.inner_text())
                    if parsed_strike and parsed_strike > price:
                        strikethrough_price = parsed_strike

                # Desconto percentual calculado
                discount_pct = None
                if strikethrough_price and strikethrough_price > 0:
                    discount_pct = round(
                        (strikethrough_price - price) / strikethrough_price, 4
                    )

                # Avaliações
                rating = 0.0
                rating_elem = card.query_selector(SELECTORS["rating"])
                if rating_elem:
                    rating = parse_rating(rating_elem.inner_text())

                # Número de avaliações
                review_count = 0
                reviews_elem = card.query_selector(SELECTORS["review_count"])
                if reviews_elem:
                    review_count = parse_review_count(reviews_elem.inner_text())

                # Imagem
                image_url = None
                img_elem = card.query_selector(SELECTORS["image"])
                if img_elem:
                    image_url = img_elem.get_attribute("src")

                # URL limpo do produto
                product_url = f"{self.config.base_url}/dp/{asin}"

                # Prime
                is_prime = card.query_selector(SELECTORS["prime_icon"]) is not None

                scraped.append(
                    ScrapedProduct(
                        asin=asin,
                        title=title,
                        url=product_url,
                        image_url=image_url,
                        current_price=price,
                        strikethrough_price=strikethrough_price,
                        discount_pct=discount_pct,
                        rating=rating,
                        review_count=review_count,
                        seller_name="Amazon / Marketplace",
                        is_prime=is_prime,
                        category_id=category.id,
                    )
                )
            except Exception as err:
                logger.debug(f"Erro ao extrair cartão de produto: {err}")
                continue

        return scraped
