# This file was created by Aryaman Rastogi.

# If you have any questions, feel free to ask me on my phone number 647 679 9802

# if you wish to contirbute to this file, please add your name and phone number in the comments below

import asyncio
import re
import os
from playwright.async_api import async_playwright, TimeoutError

class LGScraper:
    """Specialized scraper for LG official website price information"""
    
    def __init__(self):
        self.base_url = "https://www.lg.com/ca_en/search/?search={}"
    
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
    
    def check_brand(self, product_name: str) -> bool:
        """Check if the first word of the product name is LG"""
        first_word = product_name.strip().split(' ')[0].lower()
        return first_word == "lg"
    
    async def handle_dialogs(self, page):
        """Handle various dialogs that might appear"""
        # Handle cookie dialogs and other possible popups
        try:
            cookie_selectors = [
                '#onetrust-accept-btn-handler',
                '.cookie-accept-btn',
                '.privacy-policy-accept',
                '.modal-dismiss',
                '#accept-recommended-btn-handler'
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
        """Scrape LG website price information based on product name"""
        result = {
            "retailer": "LG",
            "product_name": product_name,
            "model_number": None,
            "price": None,
            "url": None,
            "error": None
        }
        
        # Check if brand is LG
        if not self.check_brand(product_name):
            result["error"] = "Product is not LG brand"
            return result
        
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
                
                # Wait for products to load
                await page.wait_for_timeout(2000)
                
                # Check if there are search results
                no_results = await page.query_selector('.no-results-message')
                if no_results:
                    result["error"] = "No search results found"
                    await browser.close()
                    return result
                
                # Check if there are search results and get the first product URL
                product_link = await page.query_selector('.cs-search-result__all-item a.title[href]')
                if not product_link:
                    result["error"] = "No product links found"
                    await browser.close()
                    return result
                
                # Get detail page URL and navigate to it
                detail_url = await product_link.get_attribute('href')
                if not detail_url.startswith('http'):
                    detail_url = 'https://www.lg.com' + detail_url
                
                # Update the URL in the result
                result["url"] = detail_url
                
                # Navigate to the detail page
                await page.goto(detail_url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(2000)
                
                # Handle possible dialogs on the detail page
                await self.handle_dialogs(page)
                
                # Get the actual model number from the detail page
                model_element = await page.query_selector('.c-text-contents__eyebrow .cmp-text')
                product_model = None
                if model_element:
                    product_model = await model_element.inner_text()
                    product_model = product_model.strip()
                
                if not product_model:
                    result["error"] = "No product model found on detail page"
                    await browser.close()
                    return result
                
                # Try to get price
                try:
                    # Get price
                    price_element = await page.query_selector('.c-price__purchase')
                    if price_element:
                        price_text = await price_element.inner_text()
                        
                        # Extract numbers from price text
                        price_match = re.search(r'\$[\d,]+\.?\d*', price_text)
                        if price_match:
                            price_str = price_match.group(0).replace('$', '').replace(',', '')
                            price = float(price_str)
                        else:
                            raise ValueError("Could not parse price from text")
                        
                        # Verify if product model matches our search model number
                        # Case-insensitive exact match or close match
                        if product_model and (model_number.upper() == product_model.upper() or 
                                              model_number.upper().replace('-', '') == product_model.upper().replace('-', '')):
                            result["price"] = price
                        else:
                            result["error"] = f"Model does not match: searching for '{model_number}', found '{product_model}'"
                    else:
                        # Try other possible price selectors
                        alt_price_selectors = [
                            '.price',
                            '.product-price',
                            '[data-price]',
                            '.price-value'
                        ]
                        
                        for selector in alt_price_selectors:
                            alt_price_element = await page.query_selector(selector)
                            if alt_price_element:
                                price_text = await alt_price_element.inner_text()
                                price_match = re.search(r'\$[\d,]+\.?\d*', price_text)
                                if price_match:
                                    price_str = price_match.group(0).replace('$', '').replace(',', '')
                                    price = float(price_str)
                                    
                                    # Verify product model
                                    if product_model and (model_number.upper() in product_model.upper() or product_model.upper() in model_number.upper()):
                                        result["price"] = price
                                        break
                                    else:
                                        result["error"] = f"Model does not match product model"
                        
                        if not result["price"] and not result["error"]:
                            raise ValueError("Could not find price element")
                
                except Exception as e:
                    result["error"] = f"Price extraction error: {str(e)}"
                
                await browser.close()
                
        except TimeoutError as e:
            result["error"] = f"Timeout: {str(e)}"
        except Exception as e:
            result["error"] = str(e)
        
        return result

async def main():
    # Test cases
    products = [
        "LG 55\" QNED80 TV 55QNED80TUC",
        "Samsung 65\" QN65QN90D",  # Non-LG product, should be filtered
    ]
    
    scraper = LGScraper()
    
    for product in products:
        result = await scraper.scrape_product(product)
        
        if result["price"]:
            print(f"Found at LG: ${result['price']}")
            print(f"URL: {result['url']}")
        else:
            print(f"Error: {result['error']}")
            if result["url"]:
                print(f"Search URL: {result['url']}")

if __name__ == "__main__":
    asyncio.run(main())