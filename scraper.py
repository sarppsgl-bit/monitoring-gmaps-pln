import json
import re
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
            page = context.new_page()

            for u in UNITS:
                query = f"PLN {u['namaUnit']}"
                url = f"https://www.google.com/search?q={requests.utils.quote(query)}&amp;hl=id"
                
                rating = 0.0
                reviews = 0
                
                try:
                    page.goto(url, timeout=30000, wait_until="domcontentloaded")
                    content = page.content()

                    # Extract Rating (Presisi Digit + Koma)
                    r_match = re.search(r'([0-9]+[\.,][0-9]+)\s*(?:★|bintang|stars|dari)', content, re.IGNORECASE) or \
                              re.search(r'Rating:\s*([0-9]+[\.,][0-9]+)', content, re.IGNORECASE) or \
                              re.search(r'aria-label="([0-9]+[\.,][0-9]+)', content, re.IGNORECASE)
                    
                    if r_match:
                        rating = float(r_match.group(1).replace(',', '.'))

                    # Extract Reviews
                    rev_match = re.search(r'([0-9\.]+)\s*(?:ulasan|reviews|penilaian)', content, re.IGNORECASE) or \
                                re.search(r'\\(([0-9\.]+)\\)\s*ulasan', content, re.IGNORECASE)
                    
                    if rev_match:
                        rev_str = rev_match.group(1).replace('.', '')
                        if rev_str.isdigit():
                            reviews = int(rev_str)

                    print(f"FETCH SUCCESS: {u['namaUnit']} -&gt; Rating: {rating}, Ulasan: {reviews}")
                except Exception as e:
                    print(f"ERROR fetching {u['namaUnit']}: {e}")

                results.append({
                    "idUnit": u["idUnit"],
                    "namaUnit": u["namaUnit"],
                    "rating": rating,
                    "reviews": reviews
                })

            browser.close()
    except Exception as e_playwright:
        print(f"CRITICAL PLAYWRIGHT ERROR: {e_playwright}")

    # Kirim hasil ke Google Sheets Web App
    if results:
        try:
            resp = requests.post(WEB_APP_URL, json=results, headers={"Content-Type": "application/json"})
            print("WEB APP RESPONSE:", resp.text)
        except Exception as err:
            print("SEND ERROR:", err)

if __name__ == "__main__":
    scrape()
