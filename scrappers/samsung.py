import asyncio
import re
from urllib.parse import quote_plus
from playwright.async_api import async_playwright, TimeoutError


class SamsungScraper:
    """Scraper for Samsung Canada's official site to fetch product price based on search result cards."""

    def __init__(self):
        self.search_url_template = "https://www.samsung.com/ca/aisearch/?searchvalue={}"

    def extract_model_number(self, name: str) -> str:
        match = re.search(r'(QN\d{2,}[A-Z0-9]+|UN\d{2,}[A-Z0-9]+)', name.upper())
        return match.group(1) if match else name

    async def handle_dialogs(self, page):
        selectors = [
            '#truste-consent-button',
            '.cookie-banner__close',
            '.cookie-notification__button',
            '.cookie-banner__accept-button'
        ]
        for selector in selectors:
            try:
                btn = await page.query_selector(selector)
                if btn:
                    await btn.click(timeout=3000)
                    await page.wait_for_timeout(1000)
                    break
            except:
                continue

    async def scrape_product(self, product_name: str) -> dict:
        result = {
            "retailer": "Samsung",
            "product_name": product_name,
            "model_number": None,
            "price": None,
            "url": None,
            "error": None
        }

        model_number = self.extract_model_number(product_name)
        result["model_number"] = model_number
        search_url = self.search_url_template.format(quote_plus(product_name))
        result["url"] = search_url

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
                await self.handle_dialogs(page)
                await page.wait_for_timeout(2000)

                # Iterate over all product result cards
                items = await page.query_selector_all('.aisearch__item')
                for item in items:
                    sku_elem = await item.query_selector('.aisearch-product__sku')
                    if not sku_elem:
                        continue

                    sku_text = (await sku_elem.inner_text()).strip().upper()
                    if model_number.upper() not in sku_text:
                        continue

                    # Found the right item
                    price_elem = await item.query_selector('.aisearch-product__price-current')
                    if price_elem:
                        price_text = await price_elem.inner_text()
                        match = re.search(r'\$([\d,]+\.?\d*)', price_text)
                        if match:
                            result["price"] = float(match.group(1).replace(',', ''))

                    link_elem = await item.query_selector('a.aisearch-product__image')
                    if link_elem:
                        href = await link_elem.get_attribute('href')
                        result["url"] = f"https://www.samsung.com{href}"

                    break
                else:
                    result["error"] = f"Model {model_number} not found in search results"

                await browser.close()

        except TimeoutError as te:
            result["error"] = f"Timeout occurred: {str(te)}"
        except Exception as e:
            result["error"] = str(e)

        return result


async def main():
    products = [
        "Samsung 75\" Class - QN90F Series 4K UHD NEO QLED Mini LED TV - QN75QN90FAFXZC"
    ]
    scraper = SamsungScraper()
    for product in products:
        result = await scraper.scrape_product(product)
        if result["price"]:
            print(f"✅ Price: ${result['price']}")
            print(f"🔗 URL: {result['url']}")
        else:
            print(f"❌ Error: {result['error']}")
            print(f"🔍 Search URL: {result['url']}")


if __name__ == "__main__":
    asyncio.run(main())
