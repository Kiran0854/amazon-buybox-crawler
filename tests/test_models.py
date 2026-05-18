from fastapi.testclient import TestClient

from app.main import app
from app.models import ScrapeRequest
from app.scraper import _locale_for_marketplace, _parse_count, build_offers_url, build_product_url


def test_request_normalizes_asins_and_marketplace():
    request = ScrapeRequest(asins=[" b0f3df2l7b "], marketplace="www.amazon.fr/")

    assert request.asins == ["B0F3DF2L7B"]
    assert request.marketplace == "https://www.amazon.fr"
    assert request.max_concurrency == 3


def test_url_builders():
    assert build_product_url("https://www.amazon.fr", "B0F3DF2L7B") == "https://www.amazon.fr/dp/B0F3DF2L7B"
    assert (
        build_offers_url("https://www.amazon.fr", "B0F3DF2L7B")
        == "https://www.amazon.fr/gp/offer-listing/B0F3DF2L7B?condition=all"
    )


def test_parse_count_handles_french_thousands_separators():
    assert _parse_count("1 234 offres") == 1234
    assert _parse_count("1\u202f234 vendeurs") == 1234
    assert _parse_count("Aucune offre") is None


def test_marketplace_locale_defaults_to_fr_for_amazon_fr():
    assert _locale_for_marketplace("https://www.amazon.fr") == "fr-FR"
    assert _locale_for_marketplace("https://www.amazon.com") == "en-US"


def test_index_ui_is_served_with_prefilled_asin_and_fr_marketplace():
    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    assert "B0F3DF2L7B" in response.text
    assert "https://www.amazon.fr" in response.text
    assert "Crawl ASINs" in response.text
