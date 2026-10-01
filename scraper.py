import os
import re
import json
import requests
from playwright.sync_api import sync_playwright

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwG0n7k4j9LkdumyKuyCi3s4rxd_XK9Oi_11s8fKp7WOa5L6dDJjWtFWGdPTMdxipmn/exec"

UNITS = [
    {"idUnit": "UP3_SGL", "namaUnit": "UP3 Sigli"},
    {"idUnit": "ULP_SGL", "namaUnit": "ULP Sigli Kota"},
    {"idUnit": "ULP_BRN", "namaUnit": "ULP Beureunuen"},
    {"idUnit": "ULP_MRD", "namaUnit": "ULP Meureudu"}
]

def scrape():
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="id-ID"
        )

        for u in UNITS:
            query = f"PLN {u['namaUnit']}"
            url = f"https://www.google.com/search?q={requests.utils.quote(query)}&amp;hl=id"
            
            rating = 0.0
            reviews = 0
            
            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                content = page.content()

                # Extract Rating
                r_match = re.search(r'([0-9][\.,][0-9])\s*(?:★|bintang|stars|dari)', content, re.IGNORECASE) or \
                          re.search(r'Rating:\s*([0-9][\.,][0-9])', content, re.IGNORECASE) or \
                          re.search(r'aria-label="([0-9][\.,][0-9])', content, re.IGNORECASE)
                
                if r_match:
                    rating = float(r_match.group(1).replace(',', '.'))

                # Extract Reviews
                rev_match = re.search(r'([0-9\.]+)\s*(?:ulasan|reviews|penilaian)', content, re.IGNORECASE) or \
                            re.search(r'\\(([0-9\.]+)\\)\s*ulasan', content, re.IGNORECASE)
                
                if rev_match:
                    rev_str = rev_match.group(1).replace('.', '')
                    if rev_str.isdigit():
                        reviews = int(rev_str)

                print(f"FETCH: {u['namaUnit']} -&gt; Rating: {rating}, Ulasan: {reviews}")
            except Exception as e:
                print(f"ERROR {u['namaUnit']}: {e}")

            results.append({
                "idUnit": u["idUnit"],
                "namaUnit": u["namaUnit"],
                "rating": rating,
                "reviews": reviews
            })

        browser.close()

    # Kirim hasil ke Google Sheets Web App
    try:
        resp = requests.post(WEB_APP_URL, json=results, headers={"Content-Type": "application/json"})
        print("WEB APP RESPONSE:", resp.text)
    except Exception as err:
        print("SEND ERROR:", err)

if __name__ == "__main__":
    scrape()

```

1. Scroll ke bawah, klik tombol **Commit changes...**.

---

#### **Langkah 3: Bikin Jadwal Otomatis (** **.github/workflows/daily.yml** **)**

1. Klik tombol **Add file** **➔** **Create new file**.
2. Masukkan nama jalur file berikut di kolom nama file (ketik persis): `.github/workflows/daily.yml`
3. Tempelkan (*paste*) kode workflow ini:

```
name: Daily GMaps Rating Scraper

on:
  schedule:
    # Jalan otomatis setiap jam 00:00 UTC (07:00 WIB Pagi)
    - cron: '0 0 * * *'
  workflow_dispatch: # Memungkinkan tombol 'Run workflow' manual untuk tes

jobs:
  scrape-job:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/checkout@v4
        with:
          python-version: '3.10'

      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests playwright
          playwright install chromium --with-deps

      - name: Run Scraper Script
        run: python scraper.py
