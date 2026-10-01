import sys
import re
import urllib.parse
import requests

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwG0n7k4j9LkdumyKuyCi3s4rxd_XK9Oi_11s8fKp7WOa5L6dDJjWtFWGdPTMdxipmn/exec"

UNITS = [
    {"idUnit": "UP3_SGL", "namaUnit": "UP3 Sigli"},
    {"idUnit": "ULP_SGL", "namaUnit": "ULP Sigli Kota"},
    {"idUnit": "ULP_BRN", "namaUnit": "ULP Beureunuen"},
    {"idUnit": "ULP_MRD", "namaUnit": "ULP Meureudu"}
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cookie": "SOCS=CAISHAgBEhJnd3NfMjAyMzA4MTAtMF9SQzEaAmVuIAEaBgiAo_CmBg"
}

DIGITS = "0123456789"
PAT_RATING = r'([' + DIGITS + r']+(?:[\.,][' + DIGITS + r']+)?)'
PAT_REVIEWS = r'([' + DIGITS + r'\.]+)'

def parse_rating_reviews(html_content):
    rating = 0.0
    reviews = 0

    m1 = re.search(PAT_RATING + r'\s*(?:★|bintang|stars|dari|out of)', html_content, re.IGNORECASE)
    m2 = re.search(r'Rating:\s*' + PAT_RATING, html_content, re.IGNORECASE)
    m3 = re.search(r'aria-label="' + PAT_RATING, html_content, re.IGNORECASE)

    for m in [m1, m2, m3]:
        if m:
            try:
                val = float(m.group(1).replace(',', '.'))
                if 1.0 &lt;= val &lt;= 5.0:
                    rating = val
                    break
            except Exception:
                pass

    r1 = re.search(PAT_REVIEWS + r'\s*(?:ulasan|reviews|penilaian)', html_content, re.IGNORECASE)
    r2 = re.search(r'\\(' + PAT_REVIEWS + r'\\)\s*(?:ulasan|reviews)?', html_content, re.IGNORECASE)

    for r in [r1, r2]:
        if r:
            try:
                rev_str = r.group(1).replace('.', '')
                if rev_str.isdigit():
                    reviews = int(rev_str)
                    break
            except Exception:
                pass

    return rating, reviews

def run_scraper():
    print("=== STARTING GMAPS RATING SCRAPER ===")
    results = []

    # Metode 1: HTTP Requests
    for u in UNITS:
        query_str = urllib.parse.quote("PLN " + u["namaUnit"])
        target_url = f"https://www.google.com/search?q={query_str}&amp;hl=id"
        rating, reviews = 0.0, 0

        try:
            resp = requests.get(target_url, headers=HEADERS, timeout=12)
            if resp.status_code == 200:
                rating, reviews = parse_rating_reviews(resp.text)
        except Exception as e:
            print(f"HTTP fetch error for {u['namaUnit']}: {e}")

        print(f"REQUESTS RESULT -&gt; {u['namaUnit']}: Rating={rating}, Reviews={reviews}")
        results.append({
            "idUnit": u["idUnit"],
            "namaUnit": u["namaUnit"],
            "rating": rating,
            "reviews": reviews
        })

    # Metode 2: Playwright Fallback
    if any(item["rating"] == 0 for item in results):
        print("Mencoba Playwright fallback untuk unit yang bernilai 0...")
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=HEADERS["User-Agent"],
                    locale="id-ID"
                )
                context.add_cookies([{
                    "name": "SOCS",
                    "value": "CAISHAgBEhJnd3NfMjAyMzA4MTAtMF9SQzEaAmVuIAEaBgiAo_CmBg",
                    "domain": ".google.com",
                    "path": "/"
                }])
                page = context.new_page()

                for item in results:
                    if item["rating"] == 0:
                        q_str = urllib.parse.quote("PLN " + item["namaUnit"])
                        t_url = f"https://www.google.com/search?q={q_str}&amp;hl=id"
                        try:
                            page.goto(t_url, timeout=15000, wait_until="domcontentloaded")
                            page.wait_for_timeout(2000)
                            r_val, rev_val = parse_rating_reviews(page.content())
                            if r_val &gt; 0:
                                item["rating"] = r_val
                                item["reviews"] = rev_val
                            print(f"PLAYWRIGHT RESULT -&gt; {item['namaUnit']}: Rating={r_val}, Reviews={rev_val}")
                        except Exception as pw_fetch_err:
                            print(f"Playwright error for {item['namaUnit']}: {pw_fetch_err}")

                browser.close()
        except Exception as pw_err:
            print(f"Playwright fallback skipped: {pw_err}")

    valid_data = [item for item in results if item["rating"] &gt; 0]
    print("FINAL SCRAPE DATA:", results)

    if valid_data:
        try:
            post_res = requests.post(WEB_APP_URL, json=valid_data, headers={"Content-Type": "application/json"}, timeout=15)
            print("POST RESPONSE FROM SHEETS:", post_res.text)
        except Exception as post_err:
            print("Error sending to Google Sheets:", post_err)
    else:
        print("Tidak ada data rating valid (&gt; 0). Pengiriman ke Sheets dilewati.")

if __name__ == "__main__":
    try:
        run_scraper()
    except Exception as top_err:
        print(f"Eksekusi selesai dengan catatan: {top_err}")

```

*(Klik* **Commit changes...** *)*

---

#### **2\. Perbarui File** **.github/workflows/daily.yml**

Buka file **.github/workflows/daily.yml** ➔ Klik Edit (Ikon Pensil) ➔ Ganti seluruh isinya dengan struktur ini:

```
name: Daily GMaps Rating Scraper

on:
  schedule:
    - cron: '0 0 * * *'
  workflow_dispatch:

jobs:
  scrape-job:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests playwright
          playwright install chromium

      - name: Run Scraper Script
        run: python scraper.py
