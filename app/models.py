"""Pydantic schemas for the crawler API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class ScrapeRequest(BaseModel):
    """Request body for scraping one or more Amazon ASINs."""

    asins: list[str] = Field(..., min_length=1, max_length=50)
    marketplace: str = Field(default="https://www.amazon.com")
    timeout_ms: int = Field(default=45_000, ge=5_000, le=120_000)
    headless: bool = True

    @field_validator("asins")
    @classmethod
    def normalize_asins(cls, value: list[str]) -> list[str]:
        cleaned = [asin.strip().upper() for asin in value if asin and asin.strip()]
        if not cleaned:
            raise ValueError("at least one non-empty ASIN is required")
        return cleaned

    @field_validator("marketplace")
    @classmethod
    def normalize_marketplace(cls, value: str) -> str:
        marketplace = value.strip().rstrip("/")
        if not marketplace.startswith(("https://", "http://")):
            marketplace = f"https://{marketplace}"
        return marketplace


class SellerOffer(BaseModel):
    """A seller offer from the Amazon offers page."""

    seller: str | None = None
    price: str | None = None
    shipping: str | None = None
    condition: str | None = None
    delivery: str | None = None


class ProductResult(BaseModel):
    """Scraped data for an ASIN."""

    asin: str
    title: str | None = None
    current_price: str | None = None
    buybox_seller: str | None = None
    seller_count: int | None = None
    offers: list[SellerOffer] = Field(default_factory=list)
    product_url: str
    offers_url: str
    error: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class ScrapeResponse(BaseModel):
    """Response returned by scraping endpoints."""

    results: list[ProductResult]
