import re
from typing import Optional, Tuple


def parse_price(text: Optional[str]) -> Optional[float]:
    """
    Converte texto de preço da Amazon (ex: '1.299,99 €', '49,99 €', '12.50€', '899 €')
    num float válido. Retorna None se não conseguir converter.
    """
    if not text:
        return None

    cleaned = text.strip().replace("€", "").replace("&euro;", "").replace("EUR", "").strip()
    if not cleaned:
        return None

    # Caso típico europeu: '1.299,99' -> remove '.' dos milhares e substitui ',' por '.'
    # Se contiver tanto '.' quanto ','
    if "." in cleaned and "," in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            # Formato europeu: 1.234,56
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            # Formato anglo-saxão: 1,234.56
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        # Apenas vírgula: '49,99' -> '49.99'
        cleaned = cleaned.replace(",", ".")
    elif "." in cleaned:
        # Apenas ponto: pode ser '1.299' (milhares) ou '49.99' (decimal)
        parts = cleaned.split(".")
        if len(parts) == 2 and len(parts[1]) == 3 and int(parts[0]) > 0:
            # ex: '1.299' sem decimais
            cleaned = parts[0] + parts[1]
        else:
            cleaned = cleaned

    # Extrai o primeiro número decimal com regex
    match = re.search(r"\d+(\.\d+)?", cleaned)
    if match:
        try:
            val = float(match.group(0))
            return round(val, 2)
        except ValueError:
            return None
    return None


def parse_rating(text: Optional[str]) -> float:
    """Extrai nota de avaliação (ex: '4,6 de 5 estrelas' -> 4.6)."""
    if not text:
        return 0.0
    match = re.search(r"(\d+([,\.]\d+)?)\s*(?:de|out of|\/)\s*5", text, re.IGNORECASE)
    if match:
        val_str = match.group(1).replace(",", ".")
        try:
            return float(val_str)
        except ValueError:
            pass
    # Fallback simples
    match = re.search(r"(\d+([,\.]\d+)?)", text)
    if match:
        val_str = match.group(1).replace(",", ".")
        try:
            val = float(val_str)
            if 0.0 <= val <= 5.0:
                return val
        except ValueError:
            pass
    return 0.0


def parse_review_count(text: Optional[str]) -> int:
    """Extrai o número de avaliações (ex: '(1.234)', '842 valoraciones', '2,5 mil')."""
    if not text:
        return 0

    text = text.lower().replace("(", "").replace(")", "").strip()

    # Formatos como '1,2 mil' ou '1.5k'
    mil_match = re.search(r"(\d+([,\.]\d+)?)\s*(k|mil)", text)
    if mil_match:
        val = float(mil_match.group(1).replace(",", "."))
        return int(val * 1000)

    # Remove pontos e vírgulas normais de milhares
    digits_only = re.sub(r"[^\d]", "", text)
    if digits_only:
        try:
            return int(digits_only)
        except ValueError:
            return 0
    return 0


def extract_asin_from_url(url: str) -> Optional[str]:
    """Extrai ASIN de 10 caracteres alfanuméricos de um URL da Amazon."""
    if not url:
        return None
    match = re.search(r"/(?:dp|gp/product|product)/([A-Z0-9]{10})(?:[/?]|$)", url)
    if match:
        return match.group(1)
    return None


# Seletores CSS principais da Amazon para cartões de produtos
SELECTORS = {
    "product_card": "div[data-asin]:not([data-asin=''])",
    "sponsored_badge": ".puis-sponsored-label-text, .s-sponsored-label-info-icon",
    "title": "h2 a.a-link-normal span, h2 span.a-text-normal, a.a-text-normal h2 span",
    "title_link": "h2 a.a-link-normal",
    "price_offscreen": ".a-price:not(.a-text-price) .a-offscreen",
    "price_whole": ".a-price:not(.a-text-price) .a-price-whole",
    "price_fraction": ".a-price:not(.a-text-price) .a-price-fraction",
    "strikethrough_price": ".a-price.a-text-price .a-offscreen, span.a-text-strike",
    "rating": "i.a-icon-star-small span.a-icon-alt, span[aria-label*='estrellas'], span[aria-label*='stars']",
    "review_count": "span[aria-label*='valoraciones'], a[href*='#customerReviews'] span, span.s-underline-text",
    "image": "img.s-image",
    "prime_icon": "i.a-icon-prime, span.s-prime",
}
