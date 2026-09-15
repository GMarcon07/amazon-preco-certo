import pytest
from pathlib import Path
from config.settings import CategoryConfig, DetectionConfig
from src.database.db import Database
from src.database.repository import Repository
from src.detector.engine import PriceDetector
from src.detector.filters import ProductFilter
from src.scrapers.base import ScrapedProduct


@pytest.fixture
def temp_repo(tmp_path: Path):
    db = Database(tmp_path / "test.db")
    return Repository(db)


@pytest.fixture
def sample_category():
    return CategoryConfig(
        id="gpu",
        name="Placas Gráficas (Média-Alta e Alta)",
        search_query="rtx 4070 4080 rx 7800",
        url_path="/s?k=rtx+4070",
        min_price_floor=250.0,
        category_blacklist=["cooler", "suporte gpu", "rtx 3050"],
    )


@pytest.fixture
def detector_components(temp_repo):
    det_cfg = DetectionConfig(
        min_strikethrough_discount=0.60,
        min_historical_discount=0.40,
        min_category_discount=0.50,
        min_saving_euros=50.0,
        min_review_count=25,
        min_rating=3.8,
        alert_cooldown_hours=24,
    )
    blacklist = ["funda", "capa", "case", "protector", "cable"]
    p_filter = ProductFilter(global_blacklist=blacklist, detection_config=det_cfg)
    detector = PriceDetector(
        repository=temp_repo,
        detection_config=det_cfg,
        product_filter=p_filter,
    )
    return p_filter, detector, temp_repo


def test_filter_accessories(detector_components, sample_category):
    p_filter, _, _ = detector_components

    accessory = ScrapedProduct(
        asin="B000TEST01",
        title="Funda protectora de silicone para comando",
        url="https://www.amazon.es/dp/B000TEST01",
        current_price=12.99,
        rating=4.5,
        review_count=150,
        category_id="controllers",
    )
    valid, reason = p_filter.evaluate(accessory, sample_category)
    assert not valid
    assert "piso" in reason.lower() or "funda" in reason.lower()

    # Preço abaixo do piso para GPU de gama média-alta
    entry_gpu = ScrapedProduct(
        asin="B000TEST02",
        title="NVIDIA GeForce RTX 3050 6GB",
        url="https://www.amazon.es/dp/B000TEST02",
        current_price=180.0,
        rating=4.3,
        review_count=200,
        category_id="gpu",
    )
    valid, reason = p_filter.evaluate(entry_gpu, sample_category)
    assert not valid
    assert "abaixo do piso mínimo" in reason.lower() or "bloqueada" in reason.lower()


def test_filter_scam_or_low_reviews(detector_components, sample_category):
    p_filter, _, _ = detector_components

    scam_listing = ScrapedProduct(
        asin="B000TEST03",
        title="NVIDIA GeForce RTX 4080 16GB Gaming OC",
        url="https://www.amazon.es/dp/B000TEST03",
        current_price=450.0,
        rating=4.0,
        review_count=5,  # Abaixo do mínimo de 25
        category_id="gpu",
    )
    valid, reason = p_filter.evaluate(scam_listing, sample_category)
    assert not valid
    assert "Poucas reviews" in reason


def test_glitch_strikethrough_real(detector_components, sample_category):
    _, detector, _ = detector_components

    # Placa gráfica com 65% de desconto riscado real (999€ -> 349€, poupança de 650€)
    glitch_gpu = ScrapedProduct(
        asin="B000GLITCH1",
        title="Gigabyte GeForce RTX 4070 Ti Super 16GB",
        url="https://www.amazon.es/dp/B000GLITCH1",
        current_price=349.0,
        strikethrough_price=999.0,
        discount_pct=0.6506,
        rating=4.7,
        review_count=850,
        category_id="gpu",
    )
    res = detector.analyze_product(glitch_gpu, sample_category)
    assert res.is_anomaly
    assert res.anomaly_type == "STRIKETHROUGH_GLITCH"
    assert res.discount_pct >= 0.60


def test_fake_pvp_rejected(detector_components, sample_category):
    _, detector, repo = detector_components

    # Caso 1: O produto já custava 350€ no histórico. O vendedor meteu PVP de 1000€
    # para fingir 65% de desconto. Preço atual continua 350€.
    repo.upsert_product({
        "asin": "B000FAKE01",
        "title": "Zotac Gaming GeForce RTX 4070 Twin Edge",
        "url": "https://www.amazon.es/dp/B000FAKE01",
        "category_id": "gpu",
        "rating": 4.5,
        "review_count": 120,
    })
    repo.record_price("B000FAKE01", price=350.0)
    repo.record_price("B000FAKE01", price=348.0)

    fake_promo = ScrapedProduct(
        asin="B000FAKE01",
        title="Zotac Gaming GeForce RTX 4070 Twin Edge",
        url="https://www.amazon.es/dp/B000FAKE01",
        current_price=349.0,  # Não baixou nada!
        strikethrough_price=999.0,  # PVP inflacionado artificialmente
        discount_pct=0.6506,
        rating=4.5,
        review_count=120,
        category_id="gpu",
    )
    res = detector.analyze_product(fake_promo, sample_category)
    # Deve rejeitar como falsa anomalia!
    assert not res.is_anomaly


def test_glitch_historical_drop(detector_components, sample_category):
    _, detector, repo = detector_components

    repo.upsert_product({
        "asin": "B000HIST01",
        "title": "ASUS TUF Gaming GeForce RTX 4070 Ti",
        "url": "https://www.amazon.es/dp/B000HIST01",
        "category_id": "gpu",
        "rating": 4.6,
        "review_count": 300,
    })
    repo.record_price("B000HIST01", price=820.0)
    repo.record_price("B000HIST01", price=799.0)
    repo.record_price("B000HIST01", price=805.0)

    dropped_gpu = ScrapedProduct(
        asin="B000HIST01",
        title="ASUS TUF Gaming GeForce RTX 4070 Ti",
        url="https://www.amazon.es/dp/B000HIST01",
        current_price=380.0,
        rating=4.6,
        review_count=300,
        category_id="gpu",
    )
    res = detector.analyze_product(dropped_gpu, sample_category)
    assert res.is_anomaly
    assert res.anomaly_type == "HISTORICAL_DROP"


def test_alert_cooldown_logic(temp_repo):
    asin = "B000COOL01"
    temp_repo.upsert_product({
        "asin": asin,
        "title": "Test Product",
        "url": "https://amazon.es/dp/test",
        "category_id": "gpu",
        "rating": 4.5,
        "review_count": 100,
    })

    can_send, _ = temp_repo.can_send_alert(asin, current_price=300.0, cooldown_hours=24)
    assert can_send

    temp_repo.record_alert(asin, price_at_alert=300.0, reference_price=800.0, discount_pct=0.625, anomaly_type="HISTORICAL")

    can_send_again, reason = temp_repo.can_send_alert(asin, current_price=300.0, cooldown_hours=24)
    assert not can_send_again

    can_send_lower, _ = temp_repo.can_send_alert(asin, current_price=250.0, cooldown_hours=24)
    assert can_send_lower
