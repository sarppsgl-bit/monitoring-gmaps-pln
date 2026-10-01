import json
import re
import urllib.parse
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
    print("Memulai scraping Google Maps 4 Unit PLN Sigli...")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="id-ID"
            )

            # BYPASS COOKIE CONSENT GOOGLE
            context.add_cookies([
                {
                    "name": "SOCS",
                    "value": "CAISHAgBEhJnd3NfMjAyMzA4MTAtMF9SQzEaAmVuIAEaBgiAo_CmBg",
                    "domain": ".google.com",
                    "path": "/"
                }
            ])

            page = context.new_page()

            for u in UNITS:
                query = f"PLN {u['namaUnit']}"
                encoded_query = urllib.parse.quote(query)
                url = f"https://www.google.com/search?q={encoded_query}&amp;hl=id"
                
                rating = 0.0
                reviews = 0

                try:
                    page.goto(url, timeout=30000, wait_until="domcontentloaded")
                    page.wait_for_timeout(3000)
                    content = page.content()

                    # Deteksi Rating
                    r1 = re.search(r'([\.,])\s*(?:★|bintang|stars|dari)', content, re.IGNORECASE)
                    r2 = re.search(r'Rating:\s*([\.,])', content, re.IGNORECASE)
                    r3 = re.search(r'aria-label="([\.,])', content, re.IGNORECASE)
                    
                    r_match = r1 or r2 or r3
                    if r_match:
                        rating = float(r_match.group(1).replace(',', '.'))

                    # Deteksi Jumlah Ulasan
                    rev1 = re.search(r'([0-9\.]+)\s*(?:ulasan|reviews|penilaian)', content, re.IGNORECASE)
                    rev2 = re.search(r'\\(([0-9\.]+)\\)\s*ulasan', content, re.IGNORECASE)
                    
                    rev_match = rev1 or rev2
                    if rev_match:
                        rev_str = rev_match.group(1).replace('.', '')
                        if rev_str.isdigit():
                            reviews = int(rev_str)

                    print(f"FETCH RESULT: {u['namaUnit']} -&gt; Rating: {rating}, Ulasan: {reviews}")
                except Exception as err_fetch:
                    print(f"FETCH ERROR {u['namaUnit']}: {err_fetch}")

                # KONTROL KETAT: Hanya masukkan jika rating &gt; 0
                if rating &gt; 0 and reviews &gt; 0:
                    results.append({
                        "idUnit": u["idUnit"],
                        "namaUnit": u["namaUnit"],
                        "rating": rating,
                        "reviews": reviews
                    })

            browser.close()
    except Exception as err_browser:
        print(f"BROWSER ERROR: {err_browser}")

    # Kirim hasil ke Google Sheets hanya jika ada data valid
    if results:
        try:
            resp = requests.post(WEB_APP_URL, json=results, headers={"Content-Type": "application/json"}, timeout=15)
            print("RESPON GOOGLE SHEETS:", resp.text)
        except Exception as err_send:
            print("SEND ERROR:", err_send)
    else:
        print("TIDAK ADA DATA VALID (Semua 0). Pengiriman dibatalkan demi keamanan sheet.")

if __name__ == "__main__":
    scrape()
