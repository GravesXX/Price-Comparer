# This file was originally created by Aryaman Rastogi.

# If you have any questions, feel free to ask me on my phone number 647 679 9802

# if you wish to contirbute to this file, please add your name and phone number in the comments below


import asyncio
import re
import os
from playwright.async_api import async_playwright, TimeoutError

class SamsungScraper:
    """Specialized scraper for Samsung official website price information (Canada)""" 
    
    def __init__(self):
        self.base_url = "https://www.samsung.com/ca/aisearch/?searchvalue={}"
    
    def extract_model_number(self, product_name: str) -> str:
        """Extract model number from product name"""
        # trying to match content after hyphen as model number
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
        """Check if the first word of the product name is Samsung"""
        first_word = product_name.strip().split(' ')[0].lower()
        return first_word == "samsung"
    
    async def handle_dialogs(self, page):
        """Handle various dialogs that might appear"""
        # Handle cookie dialog and other possible popups
        try:
            cookie_selectors = [
                '#truste-consent-button',
                '.cookie-banner__close',
                '.cookie-notification__button',
                '.cookie-banner__accept-button'
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
        """Scrape Samsung website price information based on product name"""
        result = {
            "retailer": "Samsung",
            "product_name": product_name,
            "model_number": None,
            "price": None,
            "url": None,
            "error": None
        }
        
        # Check if brand is Samsung
        if not self.check_brand(product_name):
            result["error"] = "Product is not Samsung brand"
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
                no_results = await page.query_selector('.aisearch-result__noword')
                if no_results:
                    result["error"] = "No search results found"
                    await browser.close()
                    return result
                
                # Find the product link to the detail page
                product_link_selectors = [
                    '.aisearch-product__image',
                    '.aisearch-product__name',
                    'a[data-modelcode]',
                    '.aisearch__item a'
                ]
                
                product_link = None
                product_url = None
                
                for selector in product_link_selectors:
                    links = await page.query_selector_all(selector)
                    if links and len(links) > 0:
                        # Check if we can find a link with matching model code
                        for link in links:
                            model_code = await link.get_attribute('data-modelcode')
                            if model_code and model_number.upper() in model_code.upper():
                                product_link = link
                                break
                        
                        # If no specific match found, just use the first link
                        if not product_link:
                            product_link = links[0]
                        
                        # Extract the URL
                        href = await product_link.get_attribute('href')
                        if href:
                            # Handle relative URLs
                            if href.startswith('/'):
                                product_url = f"https://www.samsung.com{href}"
                            else:
                                product_url = href
                            break
                
                if not product_url:
                    result["error"] = "No product link found"
                    await browser.close()
                    return result
                
                # Navigate to the product detail page
                await page.goto(product_url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(2000)
                
                # Handle possible dialogs on the detail page
                await self.handle_dialogs(page)
                
                # Get the model number from the detail page
                sku_element = await page.query_selector('.pd-info__sku-code')
                product_sku = None
                if sku_element:
                    sku_text = await sku_element.inner_text()
                    product_sku = sku_text.strip()
                else:
                    # Try alternative selectors for model number
                    alt_sku_selectors = [
                        '.pd-info__sku span',
                        '[data-modelcode]',
                        '.model-code',
                        '.product-sku span'
                    ]
                    
                    for selector in alt_sku_selectors:
                        alt_element = await page.query_selector(selector)
                        if alt_element:
                            sku_text = await alt_element.inner_text()
                            if sku_text:
                                product_sku = sku_text.strip()
                                break
                            
                            # If inner text is empty, try getting attribute
                            model_attr = await alt_element.get_attribute('data-modelcode')
                            if model_attr:
                                product_sku = model_attr.strip()
                                break
                
                if not product_sku:
                    result["error"] = "Could not find model number on product page"
                    await browser.close()
                    return result
                
                # Check if the model number on the detail page matches our search
                if model_number.upper() not in product_sku.upper():
                    result["error"] = f"Model number mismatch: Expected {model_number}, found {product_sku}"
                    await browser.close()
                    return result
            
                
                # Try to get price
                try:
                    price_element_selectors = [
                        '.pd-buying-price__price .pd-buying-price__new-price',
                        '.pd-buying-price__price',
                        '.price-wrap .price',
                        '.product-card__price-current',
                        '.product-details__highlight-price'
                    ]
                    
                    price = None
                    
                    for selector in price_element_selectors:
                        price_element = await page.query_selector(selector)
                        if price_element:
                            price_text = await price_element.inner_text()
                            # Extract price number
                            price_match = re.search(r'\$[\d,]+\.?\d*', price_text)
                            if price_match:
                                price_str = price_match.group(0).replace('$', '').replace(',', '')
                                price = float(price_str)
                                break
                    
                    if price is None:
                        raise ValueError("Could not extract price")
                    
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
        "Samsung 75\"  QLED 4K Smart TV - UN43DUX1EAFXZC",
    ]
    
    scraper = SamsungScraper()
    
    for product in products:
        result = await scraper.scrape_product(product)
        
        if result["price"]:
            print(f"Found at Samsung: ${result['price']}")
            print(f"URL: {result['url']}")
        else:
            print(f"Error: {result['error']}")
            if result["url"]:
                print(f"Search URL: {result['url']}")

if __name__ == "__main__":
    asyncio.run(main())