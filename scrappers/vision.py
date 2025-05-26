# This file was created by Aryaman Rastogi.

# If you have any questions, feel free to ask me on my phone number 647 679 9802

# if you wish to contirbute to this file, please add your name and phone number in the comments below

import asyncio
import re
import os
from playwright.async_api import async_playwright, TimeoutError

class VisionsScraper:
    """Specialized scraper for Visions Canada website price information"""
    
    def __init__(self):
        self.base_url = "https://www.visions.ca/catalogsearch/result?q={}"
    
    def extract_model_number(self, product_name: str) -> str:
        """Extract model number from product name"""
        # First try to match content after hyphen as model number
        model_match = re.search(r'-\s*([A-Z0-9]+[A-Z0-9]*(?:[._-][A-Z0-9]+)*)(?:\s|$)', product_name)
        
        # If no model found after hyphen, try matching other common model patterns
        if not model_match:
            # Match number+letter+number combinations
            model_match = re.search(r'(\d+[A-Z]+\d+[A-Z0-9]*)(?:\s|$)', product_name)
            
        # If still not found, try matching letter+number combinations
        if not model_match:
            model_match = re.search(r'([A-Z]+\d+[A-Z0-9]*)(?:\s|$)', product_name)
            
        if model_match:
            return model_match.group(1)
        return product_name  # Return original name if extraction fails
    
    async def handle_dialogs(self, page):
        """Handle various dialogs that might appear"""
        # Handle cookie dialogs
        try:
            cookie_selectors = [
                '.cookie-actions button',
                '.cookie-notice .primary',
                'button.accept-cookies',
                '.modal-popup .action-close'
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
        """Scrape Visions price information based on product name"""
        result = {
            "retailer": "Visions",
            "product_name": product_name,
            "model_number": None,
            "price": None,
            "url": None,
            "error": None
        }
        
        # Extract model number
        model_number = self.extract_model_number(product_name)
        result["model_number"] = model_number
        
        # Build search URL
        search_url = self.base_url.format(model_number)
        result["url"] = search_url
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()
                
                await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
                
                # Handle possible dialogs
                await self.handle_dialogs(page)
                
                # Wait for page to load
                await page.wait_for_timeout(3000)
                
                # Check URL - if redirected to product page, it will contain "/product/"
                current_url = page.url
                
                # Check if there's a no results message
                no_results = await page.query_selector('.message.notice')
                if no_results:
                    no_results_text = await no_results.inner_text()
                    if "Your search returned no results" in no_results_text:
                        result["error"] = "No search results found"
                        await browser.close()
                        return result
                
                # Get manufacturer info for model verification
                manufacturer_element = await page.query_selector('.product.attribute.manufacturer .value')
                if manufacturer_element:
                    manufacturer = await manufacturer_element.inner_text()
                    
                    # Verify if model matches
                    if model_number.upper() in manufacturer.upper():
                        # Extract price
                        # First try to get special price
                        special_price_element = await page.query_selector('.special-price .price-wrapper .price')
                        if special_price_element:
                            price_text = await special_price_element.inner_text()
                            price_match = re.search(r'[\d,]+\.\d+', price_text.replace(',', ''))
                            if price_match:
                                price = float(price_match.group(0))
                                result["price"] = price
                            else:
                                result["error"] = "Could not parse special price"
                        else:
                            # Try to get regular price
                            regular_price_element = await page.query_selector('.price-final_price .price-wrapper .price')
                            if regular_price_element:
                                price_text = await regular_price_element.inner_text()
                                price_match = re.search(r'[\d,]+\.\d+', price_text.replace(',', ''))
                                if price_match:
                                    price = float(price_match.group(0))
                                    result["price"] = price
                                else:
                                    result["error"] = "Could not parse regular price"
                            else:
                                result["error"] = "Price element not found"
                    else:
                        result["error"] = f"Model number verification failed"
                else:
                    result["error"] = "Could not verify model number"
                
                # Get product page title
                title_element = await page.query_selector('.page-title')
                if title_element:
                    product_title = await title_element.inner_text()
                    result["product_name"] = product_title.strip()
                
                await browser.close()
                
        except TimeoutError as e:
            result["error"] = f"Timeout: {str(e)}"
        except Exception as e:
            result["error"] = str(e)
        
        return result

async def main():
    # Test case
    products = [
        "Samsung 75\" 4K QLED Smart TV - QN75Q80DAFXZC"
    ]
    
    scraper = VisionsScraper()
    
    for product in products:
        result = await scraper.scrape_product(product)
        
        if result["price"]:
            print(f"Found at Visions: ${result['price']}")
            print(f"URL: {result['url']}")
        else:
            print(f"Error: {result['error']}")
            print(f"Search URL: {result['url']}")

if __name__ == "__main__":
    asyncio.run(main()) 