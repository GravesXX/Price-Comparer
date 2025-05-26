# This file was created by Aryaman Rastogi.

# If you have any questions, feel free to ask me on my phone number 647 679 9802

# if you wish to contirbute to this file, please add your name and phone number in the comments below

import asyncio
import re
import os
from playwright.async_api import async_playwright, TimeoutError

class TanguayScraper:
    """Specialized scraper for Tanguay Canada website price information"""
    
    def __init__(self):
        self.base_url = "https://www.tanguay.ca/en/search/?tanguay_prod_en%5Bquery%5D={}"
    
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
                '.cookie-accept',
                '.js-cookie-consent-agree',
                '#consent-button',
                '.cookie-consent-button',
                '#onetrust-accept-btn-handler'
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
        """Scrape Tanguay price information based on product name"""
        result = {
            "retailer": "Tanguay",
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
        
        async with async_playwright() as playwright:
            try:
                browser = await playwright.chromium.launch(headless=True)
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"
                )
                page = await context.new_page()
                
                # Set longer timeout
                page.set_default_timeout(60000)  # 60 seconds
                
                await page.goto(search_url, wait_until="networkidle")
                
                # Handle possible dialog boxes
                await self.handle_dialogs(page)
                
                # Wait for content to load
                await page.wait_for_timeout(5000)
                
                # Use XPath selector for more precision
                product_link_element = await page.query_selector('.CoveoResultLink')
                
                if not product_link_element:
                    result["error"] = "No product results found"
                    await browser.close()
                    return result
                
                # Get the product detail URL
                detail_url = await product_link_element.get_attribute('href')
                if not detail_url:
                    result["error"] = "Product URL not found"
                    await browser.close()
                    return result
                
                # Make the URL absolute if it's relative
                if detail_url.startswith('/'):
                    detail_url = f"https://www.tanguay.ca{detail_url}"
                
                # Update the URL in the result
                result["url"] = detail_url
                
                # Navigate to the product detail page
                await page.goto(detail_url, wait_until="networkidle")
                await page.wait_for_timeout(3000)
                
                # Extract the MPN (Model Number) from the detail page
                mpn_element = await page.query_selector('span.pdp-info-mpn[itemprop="mpn"]')
                
                if mpn_element:
                    # Get the model number text
                    vendor_model = await mpn_element.inner_text()
                    vendor_model = vendor_model.strip()
                    
                    # Check if the model number from the detail page matches what we searched for
                    if model_number.upper() not in vendor_model.upper():
                        result["error"] = f"Model number mismatch: Expected {model_number}, found {vendor_model}"
                        await browser.close()
                        return result
                    
                    # Get the product name as well
                    product_title_element = await page.query_selector('h1.product-title')
                    if product_title_element:
                        product_title = await product_title_element.inner_text()
                        result["product_name"] = product_title.strip()
                    
                    # Get price element - look for span with itemprop="price"
                    price_element = await page.query_selector('span[itemprop="price"]')
                    
                    if price_element:
                        try:
                            # Get the inner text (this is the displayed price including tax)
                            price_text = await price_element.inner_text()
                            price_text = price_text.strip().replace(' ', '').replace(',', '.')
                            
                            try:
                                # Try to parse the inner text first (priority)
                                if price_text:
                                    price = float(price_text)
                                    result["price"] = price
                                else:
                                    # If inner text is empty, fall back to content attribute
                                    price_content = await price_element.get_attribute('content')
                                    if price_content and price_content.strip():
                                        price = float(price_content.strip())
                                        result["price"] = price
                                    else:
                                        result["error"] = "No price text found"
                            except ValueError:
                                result["error"] = "Failed to parse price text"
                        
                        except Exception as e:
                            result["error"] = f"Price extraction error: {str(e)}"
                    else:
                        # Try other possible price selectors as fallback
                        alternative_selectors = [
                            '.bigprice.promo strong',
                            '.price_ecofrais',
                            '.v2box_reg_price',
                            '.ucc-main-container.etat span',
                            '#product-price',
                            '.price-container'
                        ]
                        
                        for selector in alternative_selectors:
                            alt_price_element = await page.query_selector(selector)
                            if alt_price_element:
                                price_text = await alt_price_element.inner_text()
                                
                                # Try to extract price
                                price_match = re.search(r'(\d+(?:[\s,]\d+)*(?:\.\d+)?)', price_text.replace(',', '.'))
                                if price_match:
                                    price_str = price_match.group(1).replace(' ', '')
                                    try:
                                        price = float(price_str)
                                        result["price"] = price
                                        break
                                    except ValueError:
                                        continue
                        
                        if not result["price"]:
                            result["error"] = "Price element not found"
                else:
                    result["error"] = "Model number element not found on product page"
                
                await browser.close()
                
            except TimeoutError as e:
                result["error"] = f"Timeout: {str(e)}"
            except Exception as e:
                result["error"] = str(e)
        
        return result

async def main():
    # Test case
    products = [
        "Samsung 75\" 4K Smart TV - UN75DU7100FXZC"
    ]
    
    scraper = TanguayScraper()
    
    for product in products:
        result = await scraper.scrape_product(product)
        
        if result["price"]:
            print(f"Found at Tanguay: ${result['price']}")
            print(f"URL: {result['url']}")
        else:
            print(f"Error: {result['error']}")
            print(f"Search URL: {result['url']}")

if __name__ == "__main__":
    asyncio.run(main()) 