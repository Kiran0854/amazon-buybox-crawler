# Amazon Buybox Crawler

FastAPI + Playwright app that accepts one or more Amazon ASINs and crawls each product detail page plus the offer-listing page. It defaults to Amazon France and includes a small browser UI so you can paste ASINs such as `B0F3DF2L7B` without writing JSON by hand.

## Extracted fields

For each ASIN, the API returns:

- `title`
- `current_price`
- `buybox_seller`
- `seller_count`
- `bullet_points` and `product_details` from the detail page when present
- `offers`: seller prices found on the offers page, including seller, price, shipping, condition, and delivery text when available
- `product_url` and `offers_url`
- `error`: populated when Amazon blocks, redirects, times out, or changes markup before all fields can be read

> Amazon frequently changes markup and may show CAPTCHA, geo, consent, or bot-detection pages. The scraper returns partial JSON plus an `error` field when a page cannot be fully read. Make sure your usage complies with Amazon's terms and applicable laws.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Run the app

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then open <http://localhost:8000> and paste one ASIN per line. The UI is prefilled with:

```text
B0F3DF2L7B
```

The default marketplace is:

```text
https://www.amazon.fr
```

## API request

```bash
curl -X POST http://localhost:8000/scrape \
  -H 'Content-Type: application/json' \
  -d '{"asins":["B0F3DF2L7B"],"marketplace":"https://www.amazon.fr","max_concurrency":3}'
```

Request options:

- `asins` (required): 1-50 ASINs.
- `marketplace`: Amazon marketplace base URL. Defaults to `https://www.amazon.fr`.
- `timeout_ms`: page timeout from `5000` to `120000`. Defaults to `45000`.
- `headless`: run Chromium in headless mode. Defaults to `true`.
- `max_concurrency`: number of ASINs to crawl at the same time from `1` to `10`. Defaults to `3`.

## Response shape

```json
{
  "results": [
    {
      "asin": "B0F3DF2L7B",
      "title": "Example product title",
      "current_price": "39,99 €",
      "buybox_seller": "Amazon.fr",
      "seller_count": 8,
      "bullet_points": ["Example feature bullet"],
      "product_details": {
        "ASIN": "B0F3DF2L7B"
      },
      "offers": [
        {
          "seller": "Amazon.fr",
          "price": "39,99 €",
          "shipping": "Livraison GRATUITE",
          "condition": "Neuf",
          "delivery": "Expédié par Amazon"
        }
      ],
      "product_url": "https://www.amazon.fr/dp/B0F3DF2L7B",
      "offers_url": "https://www.amazon.fr/gp/offer-listing/B0F3DF2L7B?condition=all",
      "error": null,
      "raw": {}
    }
  ]
}
```
