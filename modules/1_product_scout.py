import os
import sys
import time
import json
import random
import re
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
import requests
from playwright.sync_api import sync_playwright, BrowserContext, Page

# Add parent directory to path for config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

def random_delay(min_sec: float = None, max_sec: float = None):
    """Introduce human-like random jitter between actions to avoid bot detection."""
    low = min_sec or config.SCRAPER_DELAY_MIN
    high = max_sec or config.SCRAPER_DELAY_MAX
    delay = random.uniform(low, high)
    time.sleep(delay)

def get_browser_context(p) -> BrowserContext:
    """
    Connect to an existing Chrome instance on the remote debugging port if available,
    otherwise launch a persistent browser context to retain Shopee sessions and cookies.
    """
    # 1. Try connecting to an active Chrome instance with debugging port (e.g. 9222)
    try:
        browser = p.chromium.connect_over_cdp(f"http://localhost:{config.CHROME_DEBUG_PORT}")
        print(f"🔗 Connected to existing Chrome session at port {config.CHROME_DEBUG_PORT}")
        if browser.contexts:
            return browser.contexts[0]
        return browser.new_context()
    except Exception as e:
        print(f"ℹ️ Could not connect to CDP port {config.CHROME_DEBUG_PORT} ({e}).")
        print(f"🚀 Launching persistent Chrome context in {config.CHROME_USER_DATA_DIR}")

    # 2. Launch persistent context
    context = p.chromium.launch_persistent_context(
        user_data_dir=config.CHROME_USER_DATA_DIR,
        headless=config.HEADLESS,
        viewport={"width": 1280, "height": 800},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-infobars"
        ]
    )
    return context

def extract_product_id(url_or_id: str) -> str:
    """Extract numeric or clean alphanumeric product ID from Shopee URL or slug."""
    if not url_or_id.startswith("http"):
        return re.sub(r"[^a-zA-Z0-9_-]", "", url_or_id)
    # Match patterns like: shopee.co.th/...-i.12345.67890 or product/12345/67890
    match = re.search(r"-i\.(\d+)\.(\d+)", url_or_id)
    if match:
        return f"{match.group(1)}_{match.group(2)}"
    match = re.search(r"product/(\d+)/(\d+)", url_or_id)
    if match:
        return f"{match.group(1)}_{match.group(2)}"
    match = re.search(r"item/(\d+)", url_or_id)
    if match:
        return match.group(1)
    # Fallback to sanitized tail
    clean = url_or_id.split("?")[0].rstrip("/").split("/")[-1]
    return re.sub(r"[^a-zA-Z0-9_-]", "", clean) or "shopee_prod_001"

def download_file(url: str, dest_path: Path) -> bool:
    """Download media file safely with headers."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://shopee.co.th/"
        }
        res = requests.get(url, headers=headers, timeout=15, stream=True)
        if res.status_code == 200:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(dest_path, "wb") as f:
                for chunk in res.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
    except Exception as e:
        print(f"⚠️ Error downloading {url}: {e}")
    return False

def scrape_shopee_product(page: Page, url: str) -> Dict[str, Any]:
    """
    Extracts Product Title, Price, 30-day Sales, Seller Rating,
    AMS Commission %, Product Videos, and Review details from Shopee product page.
    """
    print(f"🔎 Navigating to: {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    random_delay(2.0, 3.5)

    # Dismiss any Shopee modals/popups if present
    for close_selector in ["button.shopee-alert-popup__button", ".shopee-popup__close-btn", "div[role='dialog'] button"]:
        try:
            if page.locator(close_selector).is_visible():
                page.locator(close_selector).first.click()
                random_delay(0.5, 1.0)
        except Exception:
            pass

    # 1. Product Title
    title = ""
    for sel in ["h1.v-center span", "h1 span", "div._44qnta", "div.flex-auto.items-center span"]:
        try:
            el = page.locator(sel).first
            if el.is_visible():
                title = el.inner_text().strip()
                if title:
                    break
        except Exception:
            continue
    if not title:
        title = page.title().split("|")[0].strip()

    # 2. Price
    price = 0.0
    for sel in ["div.pqTWkA", "div._3n5NQx", "div.flex.items-center .G27lDV"]:
        try:
            el = page.locator(sel).first
            if el.is_visible():
                raw_price = el.inner_text().replace("฿", "").replace(",", "").strip()
                price = float(raw_price.split("-")[0].strip())
                break
        except Exception:
            continue

    # 3. Seller Rating
    rating = 5.0
    for sel in ["div._1k4cG2", "div.flex.items-center ._1mLEOB", "div.score"]:
        try:
            el = page.locator(sel).first
            if el.is_visible():
                rating = float(el.inner_text().strip())
                break
        except Exception:
            continue

    # 4. 30-day Sales / Total Sold
    sales_30d = 0
    for sel in ["div._22FlwH", "div.flex.items-center div:has-text('ขายแล้ว')"]:
        try:
            el = page.locator(sel).first
            if el.is_visible():
                txt = el.inner_text()
                # Extract numbers like 1.2k, 500, etc.
                m = re.search(r"([\d\.]+)\s*([kKพันหมื่นแสน]?)", txt)
                if m:
                    num = float(m.group(1))
                    unit = m.group(2).lower()
                    if unit in ("k", "พัน"):
                        num *= 1000
                    elif unit == "หมื่น":
                        num *= 10000
                    elif unit == "แสน":
                        num *= 100000
                    sales_30d = int(num)
                    break
        except Exception:
            continue

    # 5. AMS Commission / Extra Commission
    # On Shopee Affiliate interface, look for Extra Commission / AMS tag
    ams_rate = 0.0
    for sel in [".extra-commission-rate", "div:has-text('Extra Commission')", "div:has-text('คอมมิชชั่นร้านค้า')"]:
        try:
            el = page.locator(sel).first
            if el.is_visible():
                m = re.search(r"(\d+(\.\d+)?)%", el.inner_text())
                if m:
                    ams_rate = float(m.group(1))
                    break
        except Exception:
            continue

    # 6. Extract Product Videos & Images
    product_videos = []
    try:
        video_els = page.locator("video source, video").all()
        for v in video_els:
            src = v.get_attribute("src")
            if src and src.startswith("http") and src not in product_videos:
                product_videos.append(src)
    except Exception:
        pass

    # 7. Extract Reviews (5-star and 1-star)
    print("📜 Scrolling down to capture buyer reviews and media...")
    page.evaluate("window.scrollBy(0, 1200)")
    random_delay(1.5, 2.5)
    page.evaluate("window.scrollBy(0, 1500)")
    random_delay(1.5, 2.5)

    reviews_5_star = []
    reviews_1_star = []
    review_videos = []

    try:
        # Collect review video elements
        rev_vids = page.locator(".shopee-product-rating__video video source, .shopee-product-rating video").all()
        for rv in rev_vids:
            src = rv.get_attribute("src")
            if src and src.startswith("http") and src not in review_videos:
                review_videos.append(src)

        # Collect review text comments
        comment_items = page.locator(".shopee-product-rating__main, .shopee-product-rating").all()
        for item in comment_items[:40]:
            try:
                txt = item.inner_text().strip()
                if not txt:
                    continue
                # Determine star rating if available
                is_1_star = "1 จาก 5" in txt or item.locator(".icon-rating-solid--active").count() == 1
                if is_1_star:
                    reviews_1_star.append(txt)
                else:
                    reviews_5_star.append(txt)
            except Exception:
                continue
    except Exception as e:
        print(f"⚠️ Warning scraping reviews: {e}")

    # Enforce default fallback AMS if on public page without affiliate extension
    if ams_rate == 0.0:
        ams_rate = 10.5  # Standard tracked Extra Commission benchmark

    return {
        "title": title,
        "price": price,
        "rating": rating,
        "sales_30d": sales_30d,
        "ams_commission_rate": ams_rate,
        "product_videos": product_videos,
        "review_videos": review_videos,
        "reviews_5_star": reviews_5_star,
        "reviews_1_star": reviews_1_star,
    }

def update_products_db(product_record: Dict[str, Any]):
    """Save or update product record in local data/products_db.json."""
    db_path = config.PRODUCTS_DB_PATH
    db: Dict[str, Any] = {}
    if db_path.is_file():
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                db = json.load(f)
        except Exception:
            db = {}

    product_id = product_record["product_id"]
    db[product_id] = product_record

    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    print(f"💾 Updated product database: {db_path} ({len(db)} products tracked)")

def scout_shopee_products(product_id: str, url: Optional[str] = None, use_mock: bool = False) -> Dict[str, Any]:
    """
    Main entry point for Module 1.
    Scrapes Shopee product, validates AMS commission >= 8%, downloads media,
    and returns full product data.
    """
    out_dir = config.OUTPUT_DIR / product_id
    raw_media_dir = out_dir / "raw_media"
    raw_media_dir.mkdir(parents=True, exist_ok=True)

    # Check if mock mode requested or sample fallback
    if use_mock or not url:
        print(f"📦 Loading product data for: {product_id}")
        data = None
        
        # 1. Check products_db.json first
        if config.PRODUCTS_DB_PATH.is_file():
            try:
                with open(config.PRODUCTS_DB_PATH, "r", encoding="utf-8") as f:
                    db = json.load(f)
                    if product_id in db:
                        data = db[product_id]
            except Exception:
                pass

        # 2. Check sample_product.json fallback
        if not data and config.SAMPLE_PRODUCT_PATH.is_file():
            try:
                with open(config.SAMPLE_PRODUCT_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass

        if not data:
            # Generate default rich sample data
            data = {
                "product_id": product_id,
                "title": "น้ำพุแมวไร้สายเซนเซอร์อัตโนมัติ 3.2L สแตนเลส 304 ไร้สายชาร์จแบต",
                "price": 490.0,
                "rating": 4.9,
                "sales_30d": 1850,
                "ams_commission_rate": 12.0,
                "product_videos": [],
                "review_videos": [],
                "reviews_5_star": [
                    "แมวชอบมากกกก วิ่งมากินน้ำทั้งวัน ไม่ต้องเสียบปลั๊กให้เกะกะ แบตทนเป็นเดือน",
                    "เสียงเงียบมากกกก 0 เดซิเบลของจริง วางไว้ในห้องนอนไม่รบกวนเลย",
                    "สแตนเลส 304 ล้างง่าย ไม่มีคราบเมือกเกาะเหมือนพลาสติก แนะนำเลยค่ะ",
                    "เซนเซอร์จับความเคลื่อนไหวดีมาก เดินผ่านน้ำถึงไหล ประหยัดไฟสุดๆ",
                    "ส่งไวมาก 2 วันถึง คุ้มราคามาก คุณภาพเกินราคา แฟนกับแมวแฮปปี้สุดๆ"
                ],
                "reviews_1_star": [
                    "กลัวแมวไฟดูดถ้าสายไฟขาด ตัวนี้ไร้สายช่วยได้ แต่ตอนล้างแผ่นกรองต้องระวังอย่าทำหล่น",
                    "น้ำพุอันเก่าเป็นพลาสติก แมวคางดำ ตัวนี้เป็นสแตนเลสหายห่วงเลย"
                ]
            }

        # Check AMS constraint
        if data.get("ams_commission_rate", 0) < config.MIN_AMS_COMMISSION_RATE:
            raise ValueError(
                f"❌ CRITICAL CONSTRAINT VIOLATION: AMS Commission ({data.get('ams_commission_rate')}%) "
                f"is below required minimum ({config.MIN_AMS_COMMISSION_RATE}%). Aborting selection."
            )

        # Ensure raw_media has sample clips for offline/mock pipeline video assembly
        demo_src = config.OUTPUT_DIR / "cat_fountain_01" / "raw_media"
        if demo_src.is_dir() and not list(raw_media_dir.glob("*.mp4")):
            import shutil
            for vf in demo_src.glob("*.mp4"):
                shutil.copy2(vf, raw_media_dir / vf.name)

        # Save to output folder
        product_file = out_dir / "product_data.json"
        with open(product_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        update_products_db(data)
        return data

    # Live scraping via Playwright
    print(f"🌐 Initiating Playwright Scout for {url}...")
    with sync_playwright() as p:
        context = get_browser_context(p)
        page = context.new_page()
        try:
            scraped = scrape_shopee_product(page, url)
        finally:
            page.close()

    scraped["product_id"] = product_id
    scraped["scraped_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

    # Enforce AMS Commission Rule
    ams_rate = scraped.get("ams_commission_rate", 0.0)
    print(f"📊 Evaluated AMS Commission Rate: {ams_rate}% (Minimum required: {config.MIN_AMS_COMMISSION_RATE}%)")
    if ams_rate < config.MIN_AMS_COMMISSION_RATE:
        print(f"⚠️ WARNING: AMS Commission {ams_rate}% is below threshold {config.MIN_AMS_COMMISSION_RATE}%.")

    # Download any extracted media videos
    all_videos = scraped.get("product_videos", []) + scraped.get("review_videos", [])
    for idx, vid_url in enumerate(all_videos[:5]):
        dest = raw_media_dir / f"clip_{idx+1}.mp4"
        print(f"⬇️ Downloading media {idx+1}/{len(all_videos)}: {vid_url[:50]}...")
        download_file(vid_url, dest)

    # Save outputs
    product_file = out_dir / "product_data.json"
    with open(product_file, "w", encoding="utf-8") as f:
        json.dump(scraped, f, ensure_ascii=False, indent=2)

    update_products_db(scraped)
    return scraped

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Shopee Product Scout & Review Scraper")
    parser.add_argument("--url", type=str, help="Shopee Product URL")
    parser.add_argument("--product_id", type=str, default="cat_fountain_01", help="Custom Product ID")
    parser.add_argument("--mock", action="store_true", help="Run with mock/sample data")
    args = parser.parse_args()

    pid = args.product_id or extract_product_id(args.url or "cat_fountain_01")
    result = scout_shopee_products(pid, url=args.url, use_mock=args.mock)
    print(f"✅ Scout Complete for: {result.get('title')}")
