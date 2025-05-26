# This file was created by Aryaman Rastogi.

# If you have any questions, feel free to ask me on my phone number 647 679 9802

# if you wish to contirbute to this file, please add your name and phone number in the comments below

import asyncio
import re
import os
from playwright.async_api import async_playwright, TimeoutError
from utils.extract_model_number import extract_model_number

class AmazonScraper:
    
    def __init__(self):
        self.base_url = "https://www.amazon.ca/s?k={}"
     
    async def handle_dialogs(self, page):
        """Handle various dialogs that might appear"""
        # Handle cookie dialogs
        try:
            cookie_selectors = [
                '#sp-cc-accept',
                '.a-button-input[name="accept"]',
                '#a-autoid-0'
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
        """Scrape Amazon price information based on product name"""
        result = {
            "retailer": "Amazon",
            "product_name": product_name,
            "model_number": None,
            "price": None,
            "url": None,
            "error": None
        }
        
        # Extract model number
        model_number = extract_model_number(product_name)
        result["model_number"] = model_number
        print(f"Searching for model number: {model_number}")
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
                no_results = await page.query_selector('div.s-no-outline span:has-text("No results for")')
                if no_results:
                    result["error"] = "No search results found"
                    await browser.close()
                    return result
                
                # Get first search result link and click it to go to product details page
                # Try multiple possible selectors for the product link
                product_link = None
                selectors = [
                    '.s-result-item h2.a-size-base-plus a',
                    '.s-result-item h2 a',
                    '.s-result-item .a-link-normal.s-faceout-link',
                    '.s-result-item .a-size-small a',
                    'h2 .a-link-normal[href*="/dp/"]'
                ]
                
                for selector in selectors:
                    product_link = await page.query_selector(selector)
                    if product_link:
                        break
                        
                if not product_link:
                    # If still not found, try direct navigation to product if we can extract ASIN
                    asin_match = re.search(r'data-asin="([A-Z0-9]+)"', await page.content())
                    if asin_match:
                        asin = asin_match.group(1)
                        await page.goto(f"https://www.amazon.ca/dp/{asin}", wait_until="domcontentloaded")
                    else:
                        result["error"] = "No product link found"
                        await browser.close()
                        return result
                else:
                    # Navigate to product details page
                    await product_link.click()
                
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_timeout(2000)
                
                # Handle dialogs on the product page
                await self.handle_dialogs(page)
                
                # Update the URL to the actual product page
                result["url"] = page.url
                
                try:
                    # Check for model name in product details
                    model_name_element = await page.query_selector('#productDetails_techSpec_section_1 tr:has-text("Model Name") .prodDetAttrValue')
                    
                    if not model_name_element:
                        # Try alternative selector methods if the first one fails
                        model_name_element = await page.query_selector('th:has-text("Model Name") + td')
                    
                    page_model_number = None
                    if model_name_element:
                        page_model_text = await model_name_element.inner_text()
                        # Clean up the model text (removing non-breaking spaces and other characters)
                        page_model_number = page_model_text.strip().replace('‎', '')
                    
                    # Get price
                    price_element = await page.query_selector('.a-price .a-offscreen')
                    if price_element:
                        price_text = await price_element.inner_text()
                        # Extract price number
                        price_match = re.search(r'[\d,.]+\d+', price_text.replace(',', ''))
                        if price_match:
                            price = float(price_match.group(0))
                        else:
                            raise ValueError("Could not parse price from text")
                    else:
                        raise ValueError("Could not find price element")
                    
                    # Verify if the actual model number matches the expected one
                    if page_model_number and model_number.upper() in page_model_number.upper():
                        result["price"] = price
                    else:
                        # If model name not found in details, fall back to title check
                        product_title_element = await page.query_selector('#productTitle')
                        if product_title_element:
                            product_title = await product_title_element.inner_text()
                            if model_number.upper() in product_title.upper():
                                result["price"] = price
                            else:
                                result["error"] = f"Model not found in product details or title"
                        else:
                            result["error"] = f"Model not found and couldn't check title"
                
                except Exception as e:
                    result["error"] = f"Data extraction error: {str(e)}"
                
                await browser.close()
                
        except TimeoutError as e:
            result["error"] = f"Timeout: {str(e)}"
        except Exception as e:
            result["error"] = str(e)
        
        return result

async def main():
    # Test case
    products = [
        "Hisense 50\" 4K Google TV - 50A68N"
    ]
    
    scraper = AmazonScraper()
    
    for product in products:
        result = await scraper.scrape_product(product)
        
        if result["price"]:
            print(f"Found at Amazon: ${result['price']}")
            print(f"URL: {result['url']}")
        else:
            print(f"Error: {result['error']}")
            print(f"Search URL: {result['url']}")

if __name__ == "__main__":
    asyncio.run(main())


