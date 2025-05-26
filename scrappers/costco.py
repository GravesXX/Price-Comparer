# This file was created by Aryaman Rastogi.

# If you have any questions, feel free to ask me on my phone number 647 679 9802

# if you wish to contirbute to this file, please add your name and phone number in the comments below

# this file probably does not work anymore

import asyncio
import re
# import os
from playwright.async_api import async_playwright, TimeoutError
from urllib.parse import quote_plus
import time
import random
from utils.extract_model_number import extract_model_number
import shutil

class CostcoScraper:

    def __init__(self):

        self.base_url = "https://www.costco.ca/CatalogSearch?dept=All&keyword={}"

        self.alt_base_url = "https://www.costco.ca/search?q={}"

        self.alt_base_url2 = "https://www.costco.ca/crs-render/merchandisingsearch?q={}&offset=0&count=24"
    
    async def handle_dialogs(self, page):
        print("Handling possible dialogs...")

        try:

            location_dialog = await page.query_selector('div[role="dialog"] button')
            if location_dialog:
                print("Found location dialog, clicking decline...")
                await location_dialog.click()
                await page.wait_for_timeout(1000)  
        except Exception as e:
            print(f"No location dialog or error handling it: {e}")
        
        try:
            cookie_selectors = [
                '#onetrust-accept-btn-handler',
                '.cookie-banner .close-button',
                '#privacy-banner button',
                'button[aria-label="Close"]',
                '.modal-dialog .close'
            ]
            
            for selector in cookie_selectors:
                cookie_btn = await page.query_selector(selector)
                if cookie_btn:
                    print(f"Found dialog with selector '{selector}', closing it...")
                    try:
                        await cookie_btn.click(timeout=5000)
                        await page.wait_for_timeout(1000)  
                        break
                    except Exception as e:
                        print(f"Error clicking dialog button: {e}")
        except Exception as e:
            print(f"Error handling dialogs: {e}")
    
    async def try_navigate(self, page, url, max_retries=3):

        for attempt in range(max_retries):
            try:
                print(f"Navigation attempt {attempt+1} to {url}")
                

                response = await page.goto(
                    url, 
                    wait_until="domcontentloaded", 
                    timeout=20000
                )
                
                print(f"Navigation successful, status: {response.status if response else 'unknown'}")
                return True
            except Exception as e:
                print(f"Navigation attempt {attempt+1} failed: {e}")
                if attempt < max_retries - 1:

                    wait_time = 1 + random.random() * 2
                    print(f"Waiting {wait_time:.1f} seconds before retry...")
                    await asyncio.sleep(wait_time)
        
        return False
    
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
        print(f"Extracted model number: {model_number}")
        
        try:
            async with async_playwright() as p:

                browser = await p.chromium.launch(headless=False)  
                
                
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    viewport={"width": 1366, "height": 768}
                )
                

                page = await context.new_page()
                

                urls_to_try = [
                    (self.base_url.format(quote_plus(model_number))),
                    (self.alt_base_url.format(quote_plus(model_number))),
                    (self.alt_base_url2.format(quote_plus(model_number))),
                    (f"https://www.costco.ca/search?text={quote_plus(model_number)}")
                ]
                
                navigation_success = False
                
                for url in urls_to_try:
                    result["url"] = url  
                    
                    navigation_success = await self.try_navigate(page, url)
                    if navigation_success:
                        break
                    
                    await asyncio.sleep(2)
                
                if not navigation_success:
                    result["error"] = "none of the urls worked"

                    await browser.close()
                    return result
                

                await self.handle_dialogs(page)
                

                await page.wait_for_timeout(3000)
                

                # os.makedirs("debug", exist_ok=True)
                # await page.screenshot(path=f"debug/costco_{model_number}_page.png", full_page=True)
                # print(f"Screenshot saved to debug/costco_{model_number}_page.png")
                
                # content = await page.content()
                # with open(f"debug/costco_{model_number}_page.html", "w", encoding="utf-8") as f:
                #     f.write(content)
                # print(f"HTML content saved to debug/costco_{model_number}_page.html")
                

                current_url = page.url
                title = await page.title()
                print(f"Current URL: {current_url}")
                print(f"Page title: {title}")
                

                no_results_selectors = [
                    '.no-results',
                    '.empty-results',
                    'div:has-text("No results found")',
                    'div:has-text("We found 0 results")'
                ]
                
                for selector in no_results_selectors:
                    no_results = await page.query_selector(selector)
                    if no_results:
                        result["error"] = "No results found"
                        print("No results found message detected")
                        await browser.close()
                        return result
                

                product_selectors = [
                    '.product-list .product',
                    '.product-tile',
                    '.product-card',
                    '.co-product-detail',
                    '.product-display',
                    '.product-list-item',
                    '.co-product', 
                    '[data-id="product"]'
                ]
                
                found_products = []
                used_selector = None
                
                for selector in product_selectors:
                    products = await page.query_selector_all(selector)
                    print(f"Selector '{selector}' found {len(products)} elements")
                    if products:
                        found_products = products
                        used_selector = selector
                        break
                
                if not found_products:

                    product_detail_indicators = [
                        '.product-page',
                        '.product-detail',
                        '.product-info',
                        '#product-page',
                        '#product-body'
                    ]
                    
                    is_product_page = False
                    for selector in product_detail_indicators:
                        if await page.query_selector(selector):
                            is_product_page = True
                            print("Detected product detail page")
                            break
                    
                    if is_product_page:

                        return await self.extract_from_product_page(page, model_number, result)
                    else:

                        price_element = await page.query_selector('.product-price, .price-value, .your-price')
                        if price_element:
                            print("Found price element, might be on product page")
                            return await self.extract_from_product_page(page, model_number, result)
                        else:
                            result["error"] = "No product items found with any known selector"
                            print("ERROR: No product items found")
                            await browser.close()
                            return result
                
                print(f"Found {len(found_products)} products with selector '{used_selector}'")
                

                for product in found_products:

                    product_html = await product.inner_html()
                    
                    if model_number.upper() in product_html.upper():
                        print(f"Found product containing model number {model_number}")
                        

                        price_selectors = [
                            '.price',
                            '.price-value',
                            '.price-format',
                            '.product-price',
                            '.product-price-amount',
                            '[data-automation="price"]'
                        ]
                        
                        for price_selector in price_selectors:
                            price_element = await product.query_selector(price_selector)
                            if price_element:
                                price_text = await price_element.inner_text()
                                print(f"Found price text: {price_text}")
                                

                                price_match = re.search(r'[\d,]+\.?\d*', price_text)
                                if price_match:
                                    price = float(price_match.group(0).replace(',', ''))
                                    result["price"] = price
                                    print(f"Extracted price: ${price}")
                                    

                                    link_selectors = [
                                        'a.product-image',
                                        'a.product-link',
                                        'a.product',
                                        'a[href]'
                                    ]
                                    
                                    for link_selector in link_selectors:
                                        link_element = await product.query_selector(link_selector)
                                        if link_element:
                                            href = await link_element.get_attribute('href')
                                            if href:
                                                if href.startswith('/'):
                                                    result["url"] = f"https://www.costco.ca{href}"
                                                else:
                                                    result["url"] = href
                                                print(f"Found product URL: {result['url']}")
                                                break
                                    

                                    break
                        

                        if result["price"]:
                            break
                
                if not result["price"]:
                    result["error"] = "Could not find or extract price for matching product"
                
                await browser.close()
        
        except Exception as e:
            result["error"] = str(e)
            print(f"Exception occurred: {e}")
        print("this code definately runs")
        directory = 'price_comparision/scrappers/debug'
        shutil.rmtree(directory)

        return result
    
    async def extract_from_product_page(self, page, model_number, result):
        print("Extracting information from product detail page...")

        page_content = await page.content()
        if model_number.upper() not in page_content.upper():
            result["error"] = f"Model number {model_number} not found on product page"
            print(f"ERROR: Model number {model_number} not found on page")
            return result
        
        print(f"Model number {model_number} found on page")
        
        price_selectors = [
            '.your-price .value',
            '.product-price',
            '.price-value',
            '.product-price-amount',
            '.product-price-value',
            '.price',
            '[data-automation="price"]'
        ]
        
        for selector in price_selectors:
            price_element = await page.query_selector(selector)
            if price_element:
                price_text = await price_element.inner_text()
                print(f"Found price text: {price_text}")
                

                price_match = re.search(r'[\d,]+\.?\d*', price_text)
                if price_match:
                    price = float(price_match.group(0).replace(',', ''))
                    result["price"] = price
                    result["url"] = page.url  
                    print(f"Extracted price: ${price}")
                    break
        
        if not result["price"]:
            result["error"] = "Could not find or extract price on product page"
            print("ERROR: Could not find or extract price")
            
        return result

async def main():
    products = [
        "Hisense 32\" Smart HD Android TV - 32A4KV"
    ]
    
    scraper = CostcoScraper()
    
    for product in products:
        print(f"\n{'='*50}")
        print(f"Scraping for: {product}")
        print(f"{'='*50}\n")
        result = await scraper.scrape_product(product)
        
        if result["price"]:
            print(f"Found at Costco: ${result['price']}")
            print(f"URL: {result['url']}")
        else:
            print(f"Error: {result['error']}")
            print(f"Search URL: {result['url']}")

if __name__ == "__main__":
    asyncio.run(main())