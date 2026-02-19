import sys
import asyncio
from playwright.async_api import async_playwright

# Set event loop policy for Windows to avoid NotImplementedError
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def test_fetch():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        print("Navigating to https://httpbin.org/html...")
        await page.goto("https://httpbin.org/html")
        content = await page.content()
        print(f"Success! Page loaded: {len(content)} characters")
        await browser.close()

# Run the test
if __name__ == "__main__":
    asyncio.run(test_fetch())