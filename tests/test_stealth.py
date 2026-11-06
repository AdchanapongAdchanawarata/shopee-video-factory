import sys
import asyncio
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding="utf-8")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")

        res = await page.goto("https://shopee.co.th/product/857367802/43461659347", wait_until="networkidle")
        print("Final URL:", page.url)
        print("Title:", await page.title())

        # Check if there is an item title
        title_el = page.locator("h1, .page-product__breadcrumb, .v-center span")
        print("Title elements count:", await title_el.count())
        if await title_el.count() > 0:
            print("Title text:", await title_el.first.inner_text())

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
