import sys
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    target_url = "https://shopee.co.th/product/857367802/43461659347"
    print(f"Opening {target_url}...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 1000}
        )
        page = await context.new_page()

        captured_ratings = []
        captured_videos = []

        async def handle_response(response):
            url = response.url
            if "rating" in url or "review" in url:
                print(f"Captured API: {url[:100]}")
                if "get_ratings" in url or "api/v2/item/get_ratings" in url or "api/v4/item/get_ratings" in url:
                    try:
                        data = await response.json()
                        captured_ratings.append(data)
                        print(f"--> Extracted rating json with {len(data.get('data', {}).get('ratings', []))} reviews!")
                    except Exception as e:
                        pass
            if ".mp4" in url or "m3u8" in url or "vod.susercontent.com" in url:
                print(f"Found Media Video: {url}")
                captured_videos.append(url)

        page.on("response", handle_response)

        await page.goto(target_url, timeout=60000, wait_until="domcontentloaded")
        await asyncio.sleep(3)

        # Scroll down gradually
        for i in range(1, 8):
            await page.evaluate(f"window.scrollBy(0, {i * 500})")
            await asyncio.sleep(1.5)

        # Look for the rating review section
        rating_box = page.locator(".product-ratings, .shopee-product-rating, .product-rating-overview")
        count = await rating_box.count()
        print(f"Rating container count: {count}")

        # Check for media tabs (with images/videos)
        media_buttons = page.locator(".product-rating-overview__filter, .shopee-filter-group")
        btn_count = await media_buttons.count()
        print(f"Filter buttons count: {btn_count}")
        if btn_count > 0:
            for b in await media_buttons.all():
                txt = await b.inner_text()
                print(f"  Filter text: {repr(txt)}")
                if "วิดีโอ" in txt or "รูปภาพ" in txt:
                    await b.click()
                    print(f"  Clicked: {txt}")
                    await asyncio.sleep(2)
                    break

        # Check review items in DOM
        comments = await page.locator(".shopee-product-rating__main, .shopee-product-rating").all()
        print(f"Total comments on page: {len(comments)}")

        # Save any found videos
        Path("output/review_vids_test.json").write_text(json.dumps({
            "captured_videos": captured_videos,
            "captured_ratings_count": len(captured_ratings),
            "ratings_sample": captured_ratings[0] if captured_ratings else {}
        }, ensure_ascii=False, indent=2), encoding="utf-8")

        await browser.close()
        print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
