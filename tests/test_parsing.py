import pytest
from src.scrapers.selectors import (
    parse_price,
    parse_rating,
    parse_review_count,
    extract_asin_from_url,
)


def test_parse_price_formats():
    assert parse_price("1.299,99 €") == 1299.99
    assert parse_price("49,99 €") == 49.99
    assert parse_price("14,50€") == 14.50
    assert parse_price("599 €") == 599.0
    assert parse_price("99.95 EUR") == 99.95
    assert parse_price("1,499.00") == 1499.00
    assert parse_price("0,99 €") == 0.99
    assert parse_price("") is None
    assert parse_price(None) is None
    assert parse_price("Indisponível") is None


def test_parse_rating():
    assert parse_rating("4,6 de 5 estrellas") == 4.6
    assert parse_rating("4.8 out of 5 stars") == 4.8
    assert parse_rating("5,0 de 5") == 5.0
    assert parse_rating("3 de 5") == 3.0
    assert parse_rating(None) == 0.0


def test_parse_review_count():
    assert parse_review_count("(1.234)") == 1234
    assert parse_review_count("842 valoraciones") == 842
    assert parse_review_count("2,5 mil valoraciones") == 2500
    assert parse_review_count("1.2k") == 1200
    assert parse_review_count("0") == 0
    assert parse_review_count(None) == 0


def test_extract_asin_from_url():
    assert extract_asin_from_url("https://www.amazon.es/dp/B0CKW7Q3X4") == "B0CKW7Q3X4"
    assert extract_asin_from_url("https://www.amazon.es/gp/product/B08N5WRWNW?th=1") == "B08N5WRWNW"
    assert extract_asin_from_url("https://www.amazon.es/s?k=laptop") is None
