from app.models import ScrapeRequest
from app.scraper import build_offers_url, build_product_url


def test_request_normalizes_asins_and_marketplace():
    request = ScrapeRequest(asins=[" b0f3df2l7b "], marketplace="www.amazon.com/")

    assert request.asins == ["B0F3DF2L7B"]
    assert request.marketplace == "https://www.amazon.com"


def test_url_builders():
    assert build_product_url("https://www.amazon.com", "B0F3DF2L7B") == "https://www.amazon.com/dp/B0F3DF2L7B"
    assert (
        build_offers_url("https://www.amazon.com", "B0F3DF2L7B")
        == "https://www.amazon.com/gp/offer-listing/B0F3DF2L7B?condition=all"
    )
