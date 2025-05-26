# This file was created by Aryaman Rastogi.

# If you have any questions, feel free to ask me on my phone number 647 679 9802

# if you wish to contirbute to this file, please add your name and phone number in the comments below

import asyncio
import re
import os
from playwright.async_api import async_playwright, TimeoutError
from urllib.parse import quote_plus

class LondonDrugsScraper:
    """Specialized scraper for London Drugs website price information"""
    
    def __init__(self):
        self.base_url = "https://www.londondrugs.com/search?q={}"
    
    def extract_brand_and_model(self, product_name: str) -> tuple:
        """Extract brand and model from product name"""
        # Extract brand (usually the first word in product name)
        brand_match = re.match(r'^([A-Za-z]+)', product_name)
        brand = brand_match.group(1) if brand_match else ""
        
        # Extract model number from product name
        # First try to match content after hyphen as model number
        model_match = re.search(r'-\s*([A-Z0-9]+[A-Z0-9]*(?:[._-][A-Z0-9]+)*)(?:\s|$)', product_name)
        
        # If no model found after hyphen, try matching other common model patterns
        if not model_match:
            # Match number+letter+number combinations
            model_match = re.search(r'(\d+[A-Z]+\d+[A-Z0-9]*)(?:\s|$)', product_name)
            
        # If still not found, try matching letter+number combinations
        if not model_match:
            model_match = re.search(r'([A-Z]+\d+[A-Z0-9]*)(?:\s|$)', product_name)
        
        model = model_match.group(1) if model_match else ""
        
        return brand, model
    
    async def handle_dialogs(self, page):
        """Handle various dialogs that might appear"""
        # Handle cookie dialogs and other possible popups
        try:
            cookie_selectors = [
                '#onetrust-accept-btn-handler',
                '.cookie-notice-button',
                '.cookie-consent-button',
                'button[aria-label="Close"]',
                '.modal-close'
            ]
            
            for selector in cookie_selectors:
                cookie_btn = await page.query_selector(selector)
                if cookie_btn:
                    try:
                        await cookie_btn.click(timeout=5000)
                        await page.wait_for_timeout(1000)
                        break
                    except Exception:
                        pass
        except Exception:
            pass
    
    async def scrape_product(self, product_name: str) -> dict:
        """Scrape London Drugs price information based on product name"""
        result = {
            "retailer": "London Drugs",
            "product_name": product_name,
            "brand": None,
            "model_number": None,
            "price": None,
            "url": None,
            "error": None
        }
        
        # Extract brand and model
        brand, model_number = self.extract_brand_and_model(product_name)
        result["brand"] = brand
        result["model_number"] = model_number
        
        # Build search URL (brand name + model number format)
        search_query = f"{brand} {model_number}" if brand else model_number
        search_url = self.base_url.format(quote_plus(search_query))
        result["url"] = search_url
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
                )
                
                page = await context.new_page()
                
                await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                
                # Handle possible dialogs
                await self.handle_dialogs(page)
                
                # Wait for products to load
                await page.wait_for_timeout(2000)
                
                # Check if there are search results
                no_results = await page.query_selector('div.no-results, div:has-text("No results found")')
                if no_results:
                    result["error"] = "No search results found"
                    await browser.close()
                    return result
                
                # Get first search result product name
                product_elements = await page.query_selector_all('.product-card, .product-item')
                
                if not product_elements or len(product_elements) == 0:
                    result["error"] = "No product elements found"
                    await browser.close()
                    return result
                
                # Iterate through product elements, looking for matching model
                for product_element in product_elements:
                    # Get product name
                    title_element = await product_element.query_selector('.product-name, h3')
                    if not title_element:
                        continue
                    
                    product_title = await title_element.inner_text()
                    product_title = product_title.strip()
                    
                    # Verify if product title contains our search model
                    if model_number.upper() not in product_title.upper():
                        continue
                    
                    # Try to get price information - first check for discount price
                    try:
                        # Check if there's a discount price
                        discount_price_element = await product_element.query_selector('small.font-semibold.text-accent')
                        
                        if discount_price_element:
                            # If discount price found
                            price_text = await discount_price_element.inner_text()
                        else:
                            # If no discount price, try to get regular price
                            regular_price_element = await product_element.query_selector('small.font-semibold')
                            
                            if regular_price_element:
                                price_text = await regular_price_element.inner_text()
                            else:
                                # If regular price can't be found, try other price selectors
                                alt_price_element = await product_element.query_selector('.product-card-price, .price')
                                if alt_price_element:
                                    price_text = await alt_price_element.inner_text()
                                else:
                                    continue
                        
                        # Extract number from price text
                        price_match = re.search(r'\$[\d,]+\.?\d*', price_text)
                        if price_match:
                            price_str = price_match.group(0).replace('$', '').replace(',', '')
                            price = float(price_str)
                            result["price"] = price
                            
                            # Get product URL
                            try:
                                link_element = await product_element.query_selector('a')
                                if link_element:
                                    product_url = await link_element.get_attribute('href')
                                    if product_url:
                                        if product_url.startswith('/'):
                                            product_url = f"https://www.londondrugs.com{product_url}"
                                        result["url"] = product_url
                            except Exception:
                                # This won't affect price result, so keep original search URL
                                pass
                            
                            # Found matching product and price, can exit loop
                            break
                        else:
                            continue
                        
                    except Exception:
                        continue
                
                # If no matching product and price found
                if not result["price"]:
                    result["error"] = "Could not find matching product with price"
                
                await browser.close()
                
        except TimeoutError as e:
            result["error"] = f"Timeout: {str(e)}"
        except Exception as e:
            result["error"] = str(e)
        
        return result

async def main():
    # Test cases
    products = [
        "Samsung 75\" QLED 4K Smart TV - QN75Q80DAFXZC",
        "Samsung QN55Q60DAFXZC"  # Simplified format test case
    ]
    
    scraper = LondonDrugsScraper()
    
    for product in products:
        result = await scraper.scrape_product(product)
        
        if result["price"]:
            print(f"Found at London Drugs: ${result['price']}")
            print(f"URL: {result['url']}")
        else:
            print(f"Error: {result['error']}")
            print(f"Search URL: {result['url']}")

if __name__ == "__main__":
    asyncio.run(main())