import sys
import asyncio
import json
import urllib.request
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding="utf-8")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # Visit shopee home first to establish genuine session cookies
        print("Visiting Shopee home...")
        await page.goto("https://shopee.co.th/", wait_until="networkidle")
        await asyncio.sleep(2)

        cookies = await context.cookies()
        cookie_header = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
        print(f"Acquired {len(cookies)} cookies.")

        # Try requesting the rating API directly with the browser's cookie header
        shop_id = "857367802"
        item_id = "43461659347"
        
        # Test API v2 and v4
        test_urls = [
            f"https://shopee.co.th/api/v2/item/get_ratings?filter=0&flag=1&itemid={item_id}&shopid={shop_id}&limit=20&offset=0&type=0",
            f"https://shopee.co.th/api/v2/item/get_ratings?filter=3&flag=1&itemid={item_id}&shopid={shop_id}&limit=20&offset=0&type=0",
            f"https://shopee.co.th/api/v4/item/get_ratings?filter=0&flag=1&itemid={item_id}&shopid={shop_id}&limit=20&offset=0&type=0"
        ]

        for u in test_urls:
            print(f"\nTesting request to: {u}")
            response = await page.request.get(u, headers={
                "Referer": f"https://shopee.co.th/product/{shop_id}/{item_id}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                "x-api-source": "pc",
                "x-shopee-language": "th"
            })
            print(f"Status: {response.status}")
            if response.status == 200:
                try:
                    data = await response.json()
                    ratings = data.get("data", {}).get("ratings", [])
                    print(f"Ratings count: {len(ratings)}")
                    videos_found = []
                    for r in ratings:
                        vids = r.get("videos") or []
                        for v in vids:
                            if isinstance(v, dict):
                                videos_found.append(v.get("url") or v.get("video_data", {}).get("url") or str(v))
                            elif isinstance(v, str):
                                videos_found.append(v)
                    print(f"Videos extracted: {len(videos_found)}")
                    for vf in videos_found:
                        print("  Video URL:", vf)
                except Exception as e:
                    print("JSON parse error:", e)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
