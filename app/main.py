"""FastAPI entrypoint for the Amazon buybox crawler."""

from __future__ import annotations

from fastapi import FastAPI

from .models import ScrapeRequest, ScrapeResponse
from .scraper import scrape_asins

app = FastAPI(
    title="Amazon Buybox Crawler",
    description="Extract title, current price, buybox seller, seller count, and offers for Amazon ASINs.",
    version="0.1.0",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape(request: ScrapeRequest) -> ScrapeResponse:
    results = await scrape_asins(
        request.asins,
        marketplace=request.marketplace,
        timeout_ms=request.timeout_ms,
        headless=request.headless,
    )
    return ScrapeResponse(results=results)
