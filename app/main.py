"""FastAPI entrypoint for the Amazon buybox crawler."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from .models import ScrapeRequest, ScrapeResponse
from .scraper import scrape_asins

app = FastAPI(
    title="Amazon Buybox Crawler",
    description="Extract title, current price, buybox seller, seller count, and offers for Amazon ASINs.",
    version="0.2.0",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    """Serve a small browser UI for ad-hoc ASIN crawls."""

    return r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Amazon Buybox Crawler</title>
  <style>
    :root { color-scheme: light dark; font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: #f5f7fb; color: #111827; }
    main { max-width: 1180px; margin: 0 auto; padding: 32px 20px 56px; }
    .card { background: white; border: 1px solid #e5e7eb; border-radius: 18px; box-shadow: 0 20px 50px rgb(15 23 42 / 8%); padding: 24px; }
    h1 { margin: 0 0 8px; font-size: clamp(2rem, 5vw, 3.25rem); letter-spacing: -0.05em; }
    p { color: #4b5563; line-height: 1.6; }
    label { display: block; font-weight: 700; margin: 18px 0 8px; }
    textarea, input, button { width: 100%; box-sizing: border-box; border-radius: 12px; border: 1px solid #d1d5db; font: inherit; }
    textarea, input { padding: 12px 14px; background: #fff; color: #111827; }
    textarea { min-height: 130px; resize: vertical; }
    .grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
    button { margin-top: 20px; padding: 14px 18px; border: 0; background: #ff9900; color: #111827; font-weight: 800; cursor: pointer; }
    button:disabled { cursor: not-allowed; opacity: .65; }
    .status { margin-top: 16px; font-weight: 700; }
    .results { margin-top: 24px; display: grid; gap: 18px; }
    .result { border: 1px solid #e5e7eb; border-radius: 14px; padding: 18px; background: #fff; }
    .result h2 { margin: 0 0 10px; font-size: 1.2rem; }
    .facts { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 14px 0; }
    .fact { background: #f9fafb; border-radius: 12px; padding: 12px; }
    .fact span { display: block; color: #6b7280; font-size: .82rem; }
    table { width: 100%; border-collapse: collapse; margin-top: 12px; }
    th, td { border-top: 1px solid #e5e7eb; padding: 10px 8px; text-align: left; vertical-align: top; }
    th { color: #374151; font-size: .85rem; }
    .error { color: #b91c1c; white-space: pre-wrap; }
    .muted { color: #6b7280; }
    @media (max-width: 800px) { .grid, .facts { grid-template-columns: 1fr; } }
    @media (prefers-color-scheme: dark) {
      body { background: #0f172a; color: #f8fafc; }
      .card, .result { background: #111827; border-color: #334155; }
      textarea, input { background: #0f172a; color: #f8fafc; border-color: #475569; }
      p, .muted, .fact span { color: #cbd5e1; }
      .fact { background: #1f2937; }
      th, td { border-color: #334155; }
      th { color: #e2e8f0; }
    }
  </style>
</head>
<body>
  <main>
    <section class="card">
      <h1>Amazon Buybox Crawler</h1>
      <p>Paste one or more ASINs, choose the marketplace, and crawl the detail page plus the offers page for current price, buybox winner, seller count, and offer prices.</p>
      <form id="scrape-form">
        <label for="asins">ASINs</label>
        <textarea id="asins" placeholder="B0F3DF2L7B&#10;B08N5WRWNW">B0F3DF2L7B</textarea>
        <div class="grid">
          <div>
            <label for="marketplace">Marketplace</label>
            <input id="marketplace" value="https://www.amazon.fr" />
          </div>
          <div>
            <label for="timeout">Timeout (ms)</label>
            <input id="timeout" type="number" min="5000" max="120000" step="1000" value="45000" />
          </div>
          <div>
            <label for="concurrency">Concurrency</label>
            <input id="concurrency" type="number" min="1" max="10" value="3" />
          </div>
        </div>
        <button id="submit" type="submit">Crawl ASINs</button>
      </form>
      <div id="status" class="status muted"></div>
    </section>
    <section id="results" class="results" aria-live="polite"></section>
  </main>
  <script>
    const form = document.querySelector('#scrape-form');
    const statusEl = document.querySelector('#status');
    const resultsEl = document.querySelector('#results');
    const submit = document.querySelector('#submit');

    function esc(value) {
      return String(value ?? '').replace(/[&<>'"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
    }

    function parseAsins(value) {
      return value.split(/[\s,;]+/).map(v => v.trim().toUpperCase()).filter(Boolean);
    }

    function renderResults(results) {
      resultsEl.innerHTML = results.map(item => {
        const offers = item.offers?.length ? `
          <table>
            <thead><tr><th>Seller</th><th>Price</th><th>Shipping</th><th>Condition</th><th>Delivery</th></tr></thead>
            <tbody>${item.offers.map(offer => `
              <tr>
                <td>${esc(offer.seller || 'Unknown')}</td>
                <td>${esc(offer.price || '-')}</td>
                <td>${esc(offer.shipping || '-')}</td>
                <td>${esc(offer.condition || '-')}</td>
                <td>${esc(offer.delivery || '-')}</td>
              </tr>`).join('')}</tbody>
          </table>` : '<p class="muted">No offer rows found.</p>';
        const bullets = item.bullet_points?.length ? `
          <h3>Detail page bullets</h3>
          <ul>${item.bullet_points.map(point => `<li>${esc(point)}</li>`).join('')}</ul>` : '';
        const details = item.product_details && Object.keys(item.product_details).length ? `
          <h3>Product details</h3>
          <table>
            <tbody>${Object.entries(item.product_details).map(([key, value]) => `
              <tr><th>${esc(key)}</th><td>${esc(value)}</td></tr>`).join('')}</tbody>
          </table>` : '';
        return `
          <article class="result">
            <h2>${esc(item.asin)} — ${esc(item.title || 'Title unavailable')}</h2>
            <div class="facts">
              <div class="fact"><span>Current price</span>${esc(item.current_price || '-')}</div>
              <div class="fact"><span>Buybox seller</span>${esc(item.buybox_seller || '-')}</div>
              <div class="fact"><span>Seller count</span>${esc(item.seller_count ?? '-')}</div>
              <div class="fact"><span>Offers collected</span>${esc(item.offers?.length ?? 0)}</div>
            </div>
            <p><a href="${esc(item.product_url)}" target="_blank" rel="noreferrer">Product page</a> · <a href="${esc(item.offers_url)}" target="_blank" rel="noreferrer">Offers page</a></p>
            ${item.error ? `<p class="error">${esc(item.error)}</p>` : ''}
            ${bullets}
            ${details}
            <h3>Seller offers</h3>
            ${offers}
          </article>`;
      }).join('');
    }

    form.addEventListener('submit', async event => {
      event.preventDefault();
      const asins = parseAsins(document.querySelector('#asins').value);
      if (!asins.length) {
        statusEl.textContent = 'Please enter at least one ASIN.';
        return;
      }
      submit.disabled = true;
      resultsEl.innerHTML = '';
      statusEl.textContent = `Crawling ${asins.length} ASIN(s)… Amazon may throttle or show CAPTCHA pages.`;
      try {
        const response = await fetch('/scrape', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            asins,
            marketplace: document.querySelector('#marketplace').value,
            timeout_ms: Number(document.querySelector('#timeout').value),
            max_concurrency: Number(document.querySelector('#concurrency').value),
            headless: true
          })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(JSON.stringify(data, null, 2));
        renderResults(data.results || []);
        statusEl.textContent = `Finished ${data.results?.length || 0} ASIN(s).`;
      } catch (error) {
        statusEl.textContent = 'Crawl failed.';
        resultsEl.innerHTML = `<pre class="error">${esc(error.message || error)}</pre>`;
      } finally {
        submit.disabled = false;
      }
    });
  </script>
</body>
</html>
    """


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape(request: ScrapeRequest) -> ScrapeResponse:
    results = await scrape_asins(
        request.asins,
        marketplace=request.marketplace,
        timeout_ms=request.timeout_ms,
        headless=request.headless,
        max_concurrency=request.max_concurrency,
    )
    return ScrapeResponse(results=results)
