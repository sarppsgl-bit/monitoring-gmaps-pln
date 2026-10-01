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
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7"
}

DIGITS = "0123456789"
NUM_PAT = r'([' + DIGITS + r']+[\.,]?' + r'[' + DIGITS + r']*)'
REV_PAT = r'([' + DIGITS + r'\.]+)'

def extract_rating_and_reviews(html):
    rating = 0.0
    reviews = 0
    
    r1 = re.search(NUM_PAT + r'\s*(?:★|bintang|stars|dari|out of)', html, re.IGNORECASE)
    r2 = re.search(r'Rating:\s*' + NUM_PAT, html, re.IGNORECASE)
    r3 = re.search(r'aria-label="' + NUM_PAT, html, re.IGNORECASE)
    
    for r_mat in [r1, r2, r3]:
        if r_mat:
            try:
                val = float(r_mat.group(1).replace(',', '.'))
                if 1.0 &lt;= val &lt;= 5.0:
                    rating = val
                    break
            except Exception:
                pass
                
    rev1 = re.search(REV_PAT + r'\s*(?:ulasan|reviews|penilaian)', html, re.IGNORECASE)
    rev2 = re.search(r'\\(' + REV_PAT + r'\\)\s*(?:ulasan|reviews)?', html, re.IGNORECASE)
    
    for rev_mat in [rev1, rev2]:
        if rev_mat:
            try:
                rev_str = rev_mat.group(1).replace('.', '')
                if rev_str.isdigit():
                    reviews = int(rev_str)
                    break
            except Exception:
                pass
                
    return rating, reviews

def scrape():
    results = []
    print("Memulai penarikan data Rating GMaps 4 Unit PLN Sigli...")
    
    for u in UNITS:
        query = f"PLN {u['namaUnit']}"
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.google.com/search?q={encoded_query}&amp;hl=id"
        
        rating = 0.0
        reviews = 0
        
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                rating, reviews = extract_rating_and_reviews(resp.text)
        except Exception as e:
            print(f"Requests error {u['namaUnit']}: {e}")
            
        print(f"FETCH (Requests) {u['namaUnit']} -&gt; Rating: {rating}, Ulasan: {reviews}")
        
        results.append({
            "idUnit": u["idUnit"],
            "namaUnit": u["namaUnit"],
            "rating": rating,
            "reviews": reviews
        })

    needs_playwright = any(item["rating"] == 0 for item in results)
    
    if needs_playwright:
        print("Mencoba Playwright Fallback untuk unit yang belum terbaca...")
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=HEADERS["User-Agent"],
                    locale="id-ID"
                )
                page = context.new_page()
                
                for item in results:
                    if item["rating"] == 0:
                        u_name = item["namaUnit"]
                        query = f"PLN {u_name}"
                        encoded_query = urllib.parse.quote(query)
                        url = f"https://www.google.com/search?q={encoded_query}&amp;hl=id"
                        
                        try:
                            page.goto(url, timeout=15000, wait_until="commit")
                            page.wait_for_timeout(2000)
                            html = page.content()
                            r, rev = extract_rating_and_reviews(html)
                            if r &gt; 0:
                                item["rating"] = r
                                item["reviews"] = rev
                            print(f"FETCH (Playwright) {u_name} -&gt; Rating: {r}, Ulasan: {rev}")
                        except Exception as p_err:
                            print(f"Playwright error {u_name}: {p_err}")
                browser.close()
        except Exception as pw_init_err:
            print(f"Playwright fallback skipped: {pw_init_err}")

    print("HASIL AKHIR:", results)

    valid_results = [item for item in results if item["rating"] &gt; 0]
    
    if valid_results:
        try:
            post_resp = requests.post(WEB_APP_URL, json=valid_results, headers={"Content-Type": "application/json"}, timeout=15)
            print("RESPON GOOGLE SHEETS:", post_resp.text)
        except Exception as send_err:
            print("SEND ERROR:", send_err)
    else:
        print("PERINGATAN: Semua rating 0. Pengiriman ditunda demi keamanan sheet.")

if __name__ == "__main__":
    scrape()
