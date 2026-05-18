# Amazon Buybox Crawler

FastAPI service that uses Playwright to scrape Amazon product and offer-listing pages for one or more ASINs.

## Extracted fields

For each ASIN, the API returns:

- `title`
- `current_price`
- `buybox_seller`
- `seller_count`
- `offers`: all seller prices found on the offers page, including seller, price, shipping, condition, and delivery text when available

> Amazon frequently changes markup and may show CAPTCHA, geo, consent, or bot-detection pages. The scraper returns partial JSON plus an `error` field when a page cannot be read.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Request

```bash
curl -X POST http://localhost:8000/scrape \
  -H 'Content-Type: application/json' \
  -d '{"asins":["B0F3DF2L7B"],"marketplace":"https://www.amazon.com"}'
```

## Response shape

```json
{
  "results": [
    {
      "asin": "B0F3DF2L7B",
      "title": "Example product title",
      "current_price": "$39.99",
      "buybox_seller": "Amazon.com",
      "seller_count": 8,
      "offers": [
        {
          "seller": "Amazon.com",
          "price": "$39.99",
          "shipping": "FREE delivery",
          "condition": "New",
          "delivery": "Ships from Amazon.com"
        }
      ],
      "product_url": "https://www.amazon.com/dp/B0F3DF2L7B",
      "offers_url": "https://www.amazon.com/gp/offer-listing/B0F3DF2L7B?condition=all",
      "error": null,
      "raw": {}
    }
  ]
}
```
