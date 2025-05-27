# This file was created by Aryaman Rastogi.

# If you have any questions, feel free to ask me on my phone number 647 679 9802

# if you wish to contribute to this file, please add your name and phone number in the comments below

import asyncio
import re
from playwright.async_api import async_playwright, TimeoutError
from urllib.parse import quote_plus
from utils.extract_model_number import extract_model_number
import os

class CostcoScraper:
    def __init__(self):
        self.base_url = "https://www.costco.ca/s?langId=-24&keyword={}"

    async def handle_dialogs(self, page):
        print("Handling possible dialogs...")
        selectors = [
            '#onetrust-accept-btn-handler',
            '.cookie-banner .close-button',
            '#privacy-banner button',
            'button[aria-label="Close"]',
            '.modal-dialog .close'
        ]
        for selector in selectors:
            try:
                btn = await page.query_selector(selector)
                if btn:
                    await btn.click()
                    await page.wait_for_timeout(1000)
                    print(f"Closed dialog with selector: {selector}")
                    break
            except Exception as e:
                print(f"Error handling {selector}: {e}")

    async def try_navigate(self, page, url, retries=3):
        for attempt in range(retries):
            try:
                print(f"Attempting navigation to {url} (try {attempt+1})")
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                return True
            except Exception as e:
                print(f"Navigation failed: {e}")
                await asyncio.sleep(1 + attempt * 1.5)
        return False

    async def extract_price_from_element(self, element):
        try:
            price_text = await element.inner_text()
            match = re.search(r'[\d,]+\.?\d*', price_text)
            if match:
                return float(match.group(0).replace(',', ''))
        except:
            return None
        return None

    async def scrape_product(self, product_name: str) -> dict:
        result = {
            "retailer": "Costco",
            "product_name": product_name,
            "model_number": None,
            "price": None,
            "url": None,
            "error": None
        }

        model_number = extract_model_number(product_name)
        result["model_number"] = model_number

        try:
            async with async_playwright() as p:
                browser = await p.webkit.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 13_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
                    viewport={"width": 1366, "height": 768}
                )
                page = await context.new_page()

                url = self.base_url.format(quote_plus(product_name))
                if not await self.try_navigate(page, url):
                    result["error"] = "Failed to load search page"
                    return result

                await self.handle_dialogs(page)
                await page.wait_for_timeout(2000)

                product_links = await page.query_selector_all('a[data-testid^="Link"][href*="product"]')
                if product_links:
                    print("Clicking into first product link...")
                    await product_links[0].click()
                    await page.wait_for_load_state("networkidle")

                    os.makedirs("debug_screenshots", exist_ok=True)
                    await page.screenshot(path=f"debug_screenshots/{model_number}_detail.png", full_page=True)

                    price_selector = '.product-price .value, .price-value, .your-price .value, [data-automation="price"], [data-testid^="Text_Price"]'
                    price_elem = await page.query_selector(price_selector)
                    if price_elem:
                        price = await self.extract_price_from_element(price_elem)
                        if price:
                            result["price"] = price
                            result["url"] = page.url
                        else:
                            result["error"] = "Price element found but no valid price parsed"
                    else:
                        result["error"] = "Price element not found"
                else:
                    result["error"] = "No product link found"

                await browser.close()

        except Exception as e:
            result["error"] = str(e)

        return result

if __name__ == "__main__":
    async def main():
        scraper = CostcoScraper()
        result = await scraper.scrape_product("Samsung 75\" Class - QN90F Series 4K UHD NEO QLED Mini LED TV - QN75QN90FAFXZC")
        print(result)

    asyncio.run(main())