# This file was created by Aryaman Rastogi.

# If you have any questions, feel free to ask me on my phone number 647 679 9802

# if you wish to contirbute to this file, please add your name and phone number in the comments below

import asyncio
import re
import os
from playwright.async_api import async_playwright, TimeoutError

class DufresneScraper:
    """Specialized scraper for Dufresne Canada website price information"""
    
    def __init__(self):
        self.base_url = "https://dufresne.ca/search?shopify_dufresne_production_products%5Bquery%5D={}"
    
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
                'button.btn-accept-cookies',
                '.cookie-banner button',
                'button[data-testid="accept-cookie-button"]',
                'button.accept-cookies'
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
        """Scrape Dufresne price information based on product name"""
        result = {
            "retailer": "Dufresne",
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
                
                # Wait for products to load
                await page.wait_for_timeout(2000)
                
                # Check if there are search results
                no_results = await page.query_selector('div.search-no-results')
                if no_results:
                    result["error"] = "No search results found"
                    await browser.close()
                    return result
                
                # Get first search result
                product_title_element = await page.query_selector('a.product-title-card')
                if not product_title_element:
                    result["error"] = "Product title not found"
                    await browser.close()
                    return result
                
                # Get product URL and navigate to product detail page
                product_url = await product_title_element.get_attribute('href')
                if not product_url:
                    result["error"] = "Product URL not found"
                    await browser.close()
                    return result
                
                if product_url.startswith('/'):
                    product_url = f"https://dufresne.ca{product_url}"
                
                result["url"] = product_url
                
                # Navigate to product detail page
                await page.goto(product_url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(2000)
                
                # First click on the "Specifications" tab to reveal the details
                specs_tab_selector = "h3.leading-6.font-semibold.text-base.w-full.text-center.py-1.tg-title.desc-open-desktop:has-text('Specifications')"
                try:
                    specs_tab = await page.query_selector(specs_tab_selector)
                    if specs_tab:
                        # Find the clickable parent element - the tab might be nested in a clickable div
                        parent = await specs_tab.evaluate_handle('node => node.closest(".cursor-pointer")')
                        if parent:
                            await parent.click()
                            # Wait for tab content to load
                            await page.wait_for_timeout(1000)
                        else:
                            # If we can't find the proper parent, try clicking directly on the tab
                            await specs_tab.click()
                            await page.wait_for_timeout(1000)
                    else:
                        # Try alternative selector
                        alt_specs_tab = await page.query_selector("div.cursor-pointer:has-text('Specifications')")
                        if alt_specs_tab:
                            await alt_specs_tab.click()
                            await page.wait_for_timeout(1000)
                except Exception as e:
                    result["error"] = f"Failed to click on Specifications tab: {str(e)}"
                
                # Find Vendor Model Number in specifications tab
                vendor_model = None
                
                # Look for divs containing "Vendor Model Number" text
                dt_elements = await page.query_selector_all('dt.font-medium')
                for dt in dt_elements:
                    text = await dt.inner_text()
                    if "Vendor Model Number" in text:
                        # Get the adjacent dd element containing the model number
                        parent_div = await dt.evaluate_handle('node => node.parentElement')
                        dd_element = await parent_div.query_selector('dd div div')
                        
                        if dd_element:
                            vendor_model = await dd_element.inner_text()
                            vendor_model = vendor_model.strip()
                            break
                
                if not vendor_model:
                    result["error"] = "Vendor Model Number not found on product page"
                    await browser.close()
                    return result
                
                # Check if the model number from the detail page matches what we searched for
                if model_number.upper() not in vendor_model.upper():
                    result["error"] = f"Model number mismatch: Expected {model_number}, found {vendor_model}"
                    await browser.close()
                    return result
                
                # Only get price if model number matches
                # Get price since we found the vendor model
                price_element = await page.query_selector('span[data-cy="product_price"]')
                if price_element:
                    price_text = await price_element.inner_text()
                    
                    # Extract price number
                    price_match = re.search(r'[\d,]+\.\d+', price_text.replace(',', ''))
                    if price_match:
                        price = float(price_match.group(0))
                        result["price"] = price
                    else:
                        result["error"] = "Price extraction failed"
                else:
                    # Try alternative price selectors
                    alt_price_element = await page.query_selector('.product-price')
                    if alt_price_element:
                        price_text = await alt_price_element.inner_text()
                        price_match = re.search(r'\$\s*([\d,.]+)', price_text)
                        if price_match:
                            price = float(price_match.group(1).replace(',', ''))
                            result["price"] = price
                        else:
                            result["error"] = "Price extraction failed"
                    else:
                        result["error"] = "Price element not found"
                
                await browser.close()
                
        except TimeoutError as e:
            result["error"] = f"Timeout: {str(e)}"
        except Exception as e:
            result["error"] = str(e)
        
        return result

async def main():
    # Test case
    products = [
        "Samsung 75\" 4K Tizen Smart CUHD TV - UN75DU7100FXZC"
    ]
    
    scraper = DufresneScraper()
    
    for product in products:
        result = await scraper.scrape_product(product)
        
        if result["price"]:
            print(f"Found at Dufresne: ${result['price']}")
            print(f"URL: {result['url']}")
        else:
            print(f"Error: {result['error']}")
            print(f"Search URL: {result['url']}")

if __name__ == "__main__":
    asyncio.run(main())