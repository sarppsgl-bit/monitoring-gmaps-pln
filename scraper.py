import re
import json
import requests
from playwright.sync_api import sync_playwright

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwG0n7k4j9LkdumyKuyCi3s4rxd_XK9Oi_11s8fKp7WOa5L6dDJjWtFWGdPTMdxipmn/exec"

UNITS = [
    {"idUnit": "UP3_SGL", "namaUnit": "UP3 Sigli", "query": "PLN UP3 Sigli", "keyword": "UP3 Sigli"},
    {"idUnit": "ULP_SGL", "namaUnit": "ULP Sigli Kota", "query": "PLN ULP Sigli Kota", "keyword": "Sigli Kota"},
    {"idUnit": "ULP_BRN", "namaUnit": "ULP Beureunuen", "query": "PLN ULP Beureunuen", "keyword": "Beureunuen"},
    {"idUnit": "ULP_MRD", "namaUnit": "ULP Meureudu", "query": "PLN ULP Meureudu", "keyword": "Meureudu"}
]

def scrape_unit(context, unit):
    name = unit["namaUnit"]
    query = unit["query"]
    keyword = unit["keyword"]
    url = "https://www.google.com/maps/search/" + query.replace(" ", "+")
    
    rating = 0.0
    reviews = 0
    stars = {"bintang5": 0, "bintang4": 0, "bintang3": 0, "bintang2": 0, "bintang1": 0}

    page = context.new_page()
    print("Navigating to " + name + "...")

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(4000)

        cards = page.locator('a[href*="/maps/place/"]')
        card_count = cards.count()
        if card_count != 0:
            target_idx = 0
            for i, card in enumerate(cards.all()[:5]):
                label = card.get_attribute("aria-label") or card.inner_text() or ""
                if keyword.lower() in label.lower():
                    target_idx = i
                    break
            cards.nth(target_idx).click()
            page.wait_for_timeout(4000)

        content = page.content()

        # 1. Ambil rating dan total ulasan
        aria_matches = re.findall(r'aria-label="([0-9.,]+)\s*(?:bintang|stars|dari|out of)[^"]*?([0-9.]+)\s*(?:ulasan|reviews)', content, re.IGNORECASE)
        for r_str, rev_str in aria_matches:
            try:
                val = float(r_str.replace(',', '.'))
                rev_num = int(rev_str.replace('.', ''))
                if int(val) in (1, 2, 3, 4, 5) and rev_num not in (0, 1, 2, 3, 4):
                    rating = round(val, 1)
                    reviews = rev_num
                    break
            except Exception:
                pass

        # 2. Fallback rating dan total ulasan jika aria-label utama tidak terdeteksi
        if rating == 0.0 or reviews == 0:
            spans = page.locator('div.F7L3fd span, span[aria-hidden="true"]').all_text_contents()
            for s in spans:
                s_clean = s.strip().replace(',', '.')
                try:
                    v = float(s_clean)
                    if int(v) in (1, 2, 3, 4, 5):
                        rating = round(v, 1)
                        break
                except Exception:
                    pass

            rev_btns = page.locator('button:has-text("ulasan"), button:has-text("reviews")').all_text_contents()
            for rb in rev_btns:
                nums = re.findall(r'([0-9.]+)', rb)
                if nums:
                    try:
                        r_clean = nums.replace('.', '')
                        if r_clean.isdigit():
                            r_int = int(r_clean)
                            if r_int not in (0, 1, 2, 3, 4):
                                reviews = r_int
                                break
                    except Exception:
                        pass

        # 3. Ekstrak Rincian Bintang 1-5 (FIXED REGEX)
        star_matches = re.findall(r'aria-label="([1-5])\s*(?:bintang|stars|star)[,\s]+([0-9.]+)', content, re.IGNORECASE)
        for star_num, count_str in star_matches:
            try:
                cnt = int(count_str.replace('.', '').replace(',', ''))
                key = "bintang" + star_num
                stars[key] = cnt
            except Exception:
                pass

    except Exception as e:
        print("Error scraping " + name + ": " + str(e))
    finally:
        page.close()

    print("RESULT : " + name + " Rating=" + str(rating) + ", Reviews=" + str(reviews) + " Stars=" + str(stars))
    return {
        "idUnit": unit["idUnit"],
        "namaUnit": name,
        "rating": rating,
        "reviews": reviews,
        "bintang5": stars["bintang5"],
        "bintang4": stars["bintang4"],
        "bintang3": stars["bintang3"],
        "bintang2": stars["bintang2"],
        "bintang1": stars["bintang1"]
    }

def main():
    print("=== STARTING PLAYWRIGHT GMAPS SCRAPER ===")
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="id-ID"
        )

        for unit in UNITS:
            results.append(scrape_unit(context, unit))

        browser.close()

    valid_data = [r for r in results if r["rating"] != 0.0]

    if valid_data:
        print("Sending " + str(len(valid_data)) + " records to Sheets...")
        try:
            res = requests.post(WEB_APP_URL, json=valid_data, headers={"Content-Type": "application/json"}, timeout=12)
            print("Sheets Response: " + res.text)
        except Exception as e:
            print("Error posting to Sheets: " + str(e))
    else:
        print("WARNING: No valid ratings found. Post skipped.")

if __name__ == "__main__":
    main()
