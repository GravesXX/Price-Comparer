# This file was created by Aryaman Rastogi.

# If you have any questions, feel free to ask me on my phone number 647 679 9802

# if you wish to contirbute to this file, please add your name and phone number in the comments below

import asyncio
import re
import os
from playwright.async_api import async_playwright, TimeoutError

class TeppermansScraper:
    """Specialized scraper for TepperMan's website price information"""
    
    def __init__(self):
        self.base_url = "https://www.teppermans.com/catalogsearch/result/?q={}"
    
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
        # Handle cookie dialogs or other possible popups
        try:
            cookie_selectors = [
                '.privacy-policy-consent .agree',
                '.cookie-notice .accept',
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
        """Scrape TepperMan's price information based on product name"""
        result = {
            "retailer": "TepperMan's",
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
                no_results = await page.query_selector('.message.notice')
                if no_results:
                    no_results_text = await no_results.inner_text()
                    if "no results" in no_results_text.lower():
                        result["error"] = "No search results found"
                        await browser.close()
                        return result
                
                # Try different selectors for product links (in order of preference)
                product_link_selectors = [
                    '.product-item-link-overlay',  # Main product link overlay
                    'a.product.photo.product-item-photo',  # Product image link
                    '.product.name.product-item-name',  # Product name
                    '.product-item-info a[href*="' + model_number + '"]',  # Any link containing model number
                    '.product-item-info a'  # Any link in product-item-info
                ]
                
                product_link = None
                for selector in product_link_selectors:
                    links = await page.query_selector_all(selector)
                    if links and len(links) > 0:
                        product_link = links[0]
                        break
                
                if not product_link:
                    result["error"] = "No product link found"
                    await browser.close()
                    return result
                
                # Get the URL from the link before clicking
                product_url = await product_link.get_attribute('href')
                
                if not product_url:
                    result["error"] = "Product URL not found"
                    await browser.close()
                    return result
                
                # Navigate directly to the product URL instead of clicking
                await page.goto(product_url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(2000)
                
                # Update the URL in the result to the detail page
                result["url"] = page.url
                
                # Get Product ID from detail page
                product_sku = await page.query_selector('li.product-sku span')
                vendor_model = None
                
                if product_sku:
                    product_id_text = await product_sku.inner_text()
                    # Extract the model number after "Product ID: "
                    id_match = re.search(r'Product ID:\s*(\S+)', product_id_text)
                    if id_match:
                        vendor_model = id_match.group(1).strip()
                
                if not vendor_model:
                    # If we couldn't find the Product ID, try alternative selector
                    alt_sku = await page.query_selector('.product.attribute.sku .value')
                    if alt_sku:
                        vendor_model = await alt_sku.inner_text()
                        vendor_model = vendor_model.strip()
                
                if not vendor_model:
                    result["error"] = "Product ID not found on detail page"
                    await browser.close()
                    return result
                
                # Check if the model number from the detail page matches what we searched for
                if model_number.upper() not in vendor_model.upper():
                    result["error"] = f"Model number mismatch: Expected {model_number}, found {vendor_model}"
                    await browser.close()
                    return result
                
                # Try to get price only if the model number matches
                try:
                    # Check for special price
                    special_price_element = await page.query_selector('.special-price .price')
                    if special_price_element:
                        price_text = await special_price_element.inner_text()
                    else:
                        # Get regular price
                        price_element = await page.query_selector('[data-price-amount]')
                        if price_element:
                            # Prefer using data-price-amount attribute
                            price_amount = await price_element.get_attribute('data-price-amount')
                            if price_amount:
                                price = float(price_amount)
                            else:
                                # If attribute not available, try getting from content
                                price_wrapper = await page.query_selector('.price-wrapper .price')
                                if price_wrapper:
                                    price_text = await price_wrapper.inner_text()
                                else:
                                    raise ValueError("Could not find price element")
                        else:
                            raise ValueError("Could not find price element")
                    
                    # Extract number from price text
                    if 'price_text' in locals():
                        price_match = re.search(r'[\d,.]+', price_text.replace(',', ''))
                        if price_match:
                            price = float(price_match.group(0))
                        else:
                            raise ValueError("Could not parse price from text")
                    
                    # Set the price in the result
                    result["price"] = price
                
                except Exception as e:
                    result["error"] = f"Price extraction error: {str(e)}"
                
                await browser.close()
                
        except TimeoutError as e:
            result["error"] = f"Timeout: {str(e)}"
        except Exception as e:
            result["error"] = str(e)
        
        return result

async def main():
    # Test case
    products = [
        "Samsung 75\" 4K CRYSTAL UHD LED HDR PUR COLOR SMART TV - UN75DU7100FXZC"
    ]
    
    scraper = TeppermansScraper()
    
    for product in products:
        result = await scraper.scrape_product(product)
        
        if result["price"]:
            print(f"Found at TepperMan's: ${result['price']}")
            print(f"URL: {result['url']}")
        else:
            print(f"Error: {result['error']}")
            print(f"Search URL: {result['url']}")

if __name__ == "__main__":
    asyncio.run(main())