"""Playwright-powered Amazon scraping helpers."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from .models import ProductResult, SellerOffer

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

TITLE_SELECTORS = ["#productTitle", "#title", "h1"]
PRICE_SELECTORS = [
    "#corePrice_feature_div .a-offscreen",
    "#priceblock_ourprice",
    "#priceblock_dealprice",
    "#price_inside_buybox",
    ".a-price .a-offscreen",
]
BUYBOX_SELLER_SELECTORS = [
    "#sellerProfileTriggerId",
    "#merchant-info a",
    "#merchant-info",
    "#tabular-buybox .tabular-buybox-text[tabular-attribute-name='Sold by']",
]
SELLER_COUNT_SELECTORS = [
    "#olpLinkWidget_feature_div a",
    "#olp_feature_div a",
    "a[href*='/gp/offer-listing/']",
    "a[href*='offer-listing']",
]
OFFER_ROW_SELECTORS = ["#aod-offer", ".olpOffer", ".aod-offer"]


def build_product_url(marketplace: str, asin: str) -> str:
    return f"{marketplace}/dp/{asin}"


def build_offers_url(marketplace: str, asin: str) -> str:
    return f"{marketplace}/gp/offer-listing/{asin}?condition=all"


async def scrape_asins(
    asins: list[str], marketplace: str, timeout_ms: int, headless: bool
) -> list[ProductResult]:
    """Scrape a collection of ASINs in a single browser session."""

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=headless)
        try:
            return await asyncio.gather(
                *(scrape_asin(browser, asin, marketplace, timeout_ms) for asin in asins)
            )
        finally:
            await browser.close()


async def scrape_asin(
    browser: Browser, asin: str, marketplace: str, timeout_ms: int
) -> ProductResult:
    """Scrape the product page and offers page for one ASIN."""

    product_url = build_product_url(marketplace, asin)
    offers_url = build_offers_url(marketplace, asin)
    result = ProductResult(asin=asin, product_url=product_url, offers_url=offers_url)

    context = await _new_context(browser, timeout_ms)
    page = await context.new_page()
    try:
        await page.goto(product_url, wait_until="domcontentloaded", timeout=timeout_ms)
        await _dismiss_overlays(page)
        result.title = await _first_text(page, TITLE_SELECTORS)
        result.current_price = await _first_text(page, PRICE_SELECTORS)
        result.buybox_seller = await _extract_buybox_seller(page)
        result.seller_count = await _extract_seller_count(page)

        await page.goto(offers_url, wait_until="domcontentloaded", timeout=timeout_ms)
        await _dismiss_overlays(page)
        result.offers = await _extract_offers(page)
        if result.seller_count is None and result.offers:
            result.seller_count = len(result.offers)
    except Exception as exc:  # Keep API responses JSON-friendly for partial failures.
        result.error = f"{type(exc).__name__}: {exc}"
    finally:
        await context.close()
    return result


async def _new_context(browser: Browser, timeout_ms: int) -> BrowserContext:
    context = await browser.new_context(
        user_agent=USER_AGENT,
        locale="en-US",
        viewport={"width": 1365, "height": 900},
    )
    context.set_default_timeout(timeout_ms)
    return context


async def _dismiss_overlays(page: Page) -> None:
    for selector in ["#sp-cc-accept", "input[name='accept']", "#a-autoid-0"]:
        element = page.locator(selector).first
        if await _safe_count(lambda: element.count()):
            await _safe(lambda: element.click(timeout=1_000))


async def _first_text(page: Page, selectors: list[str]) -> str | None:
    for selector in selectors:
        locator = page.locator(selector).first
        if await _safe_count(lambda: locator.count()):
            text = _clean_text(await _safe_text(lambda: locator.inner_text()))
            if text:
                return text
    return None


async def _extract_buybox_seller(page: Page) -> str | None:
    seller = await _first_text(page, BUYBOX_SELLER_SELECTORS)
    if not seller:
        return None
    seller = re.sub(r"^Sold by\s*", "", seller, flags=re.I)
    seller = re.sub(r"\s+and\s+Fulfilled by Amazon.*$", "", seller, flags=re.I)
    return _clean_text(seller)


async def _extract_seller_count(page: Page) -> int | None:
    for selector in SELLER_COUNT_SELECTORS:
        locator = page.locator(selector).first
        if await _safe_count(lambda: locator.count()):
            text = _clean_text(await _safe_text(lambda: locator.inner_text()))
            count = _parse_count(text)
            if count is not None:
                return count
    return None


async def _extract_offers(page: Page) -> list[SellerOffer]:
    rows = None
    for selector in OFFER_ROW_SELECTORS:
        candidate = page.locator(selector)
        if await _safe_count(lambda: candidate.count()):
            rows = candidate
            break
    if rows is None:
        return []

    offers: list[SellerOffer] = []
    for index in range(await rows.count()):
        row = rows.nth(index)
        offer = SellerOffer(
            seller=await _first_row_text(
                row,
                [
                    "#aod-offer-soldBy a",
                    "[aria-label*='seller']",
                    ".olpSellerName a",
                    ".olpSellerName",
                ],
            ),
            price=await _first_row_text(
                row,
                [
                    ".a-price .a-offscreen",
                    ".olpOfferPrice",
                    "[data-a-color='price'] .a-offscreen",
                ],
            ),
            shipping=await _first_row_text(
                row,
                [
                    "#mir-layout-DELIVERY_BLOCK-slot-PRIMARY_DELIVERY_MESSAGE_LARGE",
                    ".olpShippingInfo",
                    "[id*='deliveryBlockMessage']",
                ],
            ),
            condition=await _first_row_text(
                row,
                ["#aod-offer-heading", ".olpCondition", "[class*='condition']"],
            ),
            delivery=await _first_row_text(
                row,
                ["#mir-layout-DELIVERY_BLOCK", "[id*='DELIVERY_BLOCK']"],
            ),
        )
        if any([offer.seller, offer.price, offer.shipping, offer.condition, offer.delivery]):
            offers.append(offer)
    return offers


async def _first_row_text(row, selectors: list[str]) -> str | None:
    for selector in selectors:
        locator = row.locator(selector).first
        if await _safe_count(lambda: locator.count()):
            text = _clean_text(await _safe_text(lambda: locator.inner_text()))
            if text:
                return text
    return None


def _parse_count(text: str | None) -> int | None:
    if not text:
        return None
    match = re.search(r"(\d[\d,]*)", text)
    if not match:
        return None
    return int(match.group(1).replace(",", ""))


def _clean_text(text: str | None) -> str | None:
    if text is None:
        return None
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned or None


async def _safe_text(call: Callable[[], Awaitable[str]]) -> str | None:
    return await _safe(call)


async def _safe_count(call: Callable[[], Awaitable[int]]) -> int:
    return (await _safe(call)) or 0


async def _safe(call: Callable[[], Awaitable]):
    try:
        return await call()
    except Exception:
        return None
