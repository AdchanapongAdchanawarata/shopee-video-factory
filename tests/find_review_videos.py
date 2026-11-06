import sys
import asyncio
import re
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding="utf-8")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 900}
        )
        page = await context.new_page()

        video_urls = set()

        async def on_response(res):
            url = res.url
            if any(k in url for k in [".mp4", "vod.susercontent", "play-ws", "cv.shopee"]):
                if url not in video_urls:
                    video_urls.add(url)
                    print(f"🎬 [VIDEO URL DETECTED] {url}")

            # Check if JSON contains video URLs
            if "rating" in url or "review" in url or "item" in url:
                try:
                    txt = await res.text()
                    matches = re.findall(r"https?://[a-zA-Z0-9\.\-_/]+\.mp4[^\s\"\'\\]*", txt)
                    for m in matches:
                        clean_m = m.replace("\\u002F", "/").replace("\\", "")
                        if clean_m not in video_urls:
                            video_urls.add(clean_m)
                            print(f"⭐ [REVIEW VIDEO EXTRACTED FROM API] {clean_m}")
                except Exception:
                    pass

        page.on("response", on_response)

        print("Loading Shopee product page...")
        await page.goto("https://shopee.co.th/product/857367802/43461659347", wait_until="domcontentloaded")
        await asyncio.sleep(2)

        # Scroll in increments of 400px down to 6000px
        for offset in range(500, 7000, 500):
            await page.evaluate(f"window.scrollTo(0, {offset})")
            await asyncio.sleep(0.8)

        # Wait for dynamic sections
        await asyncio.sleep(3)

        # Find any video play buttons or review thumbnails
        review_thumbnails = await page.locator(".shopee-product-rating__video, .product-rating-overview, .shopee-product-rating__main img").all()
        print(f"Review thumbnail elements: {len(review_thumbnails)}")
        for thumb in review_thumbnails[:10]:
            try:
                await thumb.scroll_into_view_if_needed()
                await thumb.click(timeout=1500)
                await asyncio.sleep(1)
            except Exception:
                pass

        print(f"\nTotal unique videos captured: {len(video_urls)}")
        for v in video_urls:
            print(f"- {v}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
