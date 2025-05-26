# This file was created by Aryaman Rastogi.

# If you have any questions, feel free to ask me on my phone number 647 679 9802

# if you wish to contirbute to this file, please add your name and phone number in the comments below

import asyncio
import re
import json
import os
from urllib.parse import quote_plus
from playwright.async_api import async_playwright, TimeoutError
from utils.extract_model_number import extract_model_number

class BestBuyScraper:
    """Specialized scraper for BestBuy Canada website price information"""
    
    def __init__(self):
        self.base_url = "https://www.bestbuy.ca/en-ca/search?path=custom0productcondition%253ABrand%2BNew&search={}"
    

    async def handle_dialogs(self, page):
        """Handle various dialogs that might appear"""
        # Try multiple selectors for location/cookie/newsletter dialogs
        dialog_selectors = [
            'div[role="dialog"] button',
            'div[data-automation="overlay"] button',
            'div.locationModal button',
            'div.cookie-consent button[data-action="accept"]',
            'div.privacy-policy-banner button',
            '.modal-dialog button.close',
            '.modal-dialog button.btn-primary',
            '.popup-container button',
            '.location-selector button',
            '.consent-popup button',
            '#consent-tracking button.primary',
            '.cookie-banner button',
            '.regionModal button',
            '.region-modal button'
        ]
        
        for selector in dialog_selectors:
            try:
                dialog_element = await page.query_selector(selector)
                if dialog_element:
                    await dialog_element.click()
                    await page.wait_for_timeout(1000)
                    print(f"Closed dialog with selector: {selector}")
            except Exception as e:
                print(f"Failed to handle dialog with selector {selector}: {str(e)}")
                continue
                
        # Also try to press Escape key which often closes dialogs
        try:
            await page.keyboard.press('Escape')
            await page.wait_for_timeout(500)
        except Exception:
            pass
    
    async def scrape_product(self, product_name: str) -> dict:
        """Scrape BestBuy price information based on product name"""
        result = {
            "retailer": "BestBuy",
            "product_name": product_name,
            "model_number": None,
            "exact_model": None,
            "price": None,
            "url": None,
            "error": None,
            "sale_end_date": None
        }
        
        # Extract model number
        model_number = extract_model_number(product_name)
        result["model_number"] = model_number
        
        # Build search URL
        search_url = self.base_url.format(quote_plus(model_number))
        result["url"] = search_url
        
        try:
            async with async_playwright() as p:
                # Use more browser configurations to avoid detection
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 800},
                    locale="en-CA",
                    geolocation={"latitude": 43.6532, "longitude": -79.3832},  # Toronto coordinates
                    permissions=["geolocation"],
                )
                
                # Add browser disguise
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => false,
                    });
                """)
                
                page = await context.new_page()
                
                # Listen and automatically close dialogs
                page.on("dialog", lambda dialog: asyncio.create_task(dialog.dismiss()))
                
                # Navigate to search page
                await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                
                # Handle possible dialogs
                await self.handle_dialogs(page)
                
                # Wait for more content to load
                await page.wait_for_timeout(5000)
                
                # Handle possible delayed dialogs
                await self.handle_dialogs(page)
                
                # Wait for product list to load
                try:
                    await page.wait_for_selector('div[data-automation="productGridItem"], .productItemContainer_3Y0r7, .x-productListItem, li.sku-item', timeout=10000)
                except TimeoutError:
                    result["error"] = "Timeout waiting for product grid"
                    await browser.close()
                    return result
                
                # Check if there are no search results
                no_results = await page.query_selector('.no-results-found')
                if no_results:
                    result["error"] = "No results found"
                    await browser.close()
                    return result
                
                # Try multiple product list selectors
                selectors = [
                    'div[data-automation="productGridItem"]',
                    '.productItemContainer_3Y0r7',
                    '.x-productListItem',
                    'li.sku-item',
                    '.product-list li'
                ]
                
                first_product = None
                
                for selector in selectors:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        first_product = elements[0]
                        break
                
                if not first_product:
                    result["error"] = "No product items found with any known selector"
                    await browser.close()
                    return result
                
                # Try different title selectors
                title_selectors = [
                    'div[data-automation="productItemName"]',
                    '.productItemName_3IZ3c',
                    'a[data-automation="productItemLink"]',
                    '.x-productListItem_title',
                    '.sku-title',
                    '.product-title',
                    'h4'
                ]
                
                title = None
                for selector in title_selectors:
                    title_element = await first_product.query_selector(selector)
                    if title_element:
                        title = await title_element.inner_text()
                        break
                
                # If title selectors fail, try getting title from link element
                if not title:
                    link_element = await first_product.query_selector('a')
                    if link_element:
                        title_attr = await link_element.get_attribute('title')
                        if title_attr:
                            title = title_attr
                
                if not title:
                    result["error"] = "Could not find product title with any known selector"
                    await browser.close()
                    return result
                
                # Try different price selectors
                price_selectors = [
                    'div[data-automation="product-price"]',
                    '.currentPrice_2ioYO',
                    '.price_FHDfG',
                    '.product-price',
                    '.price-regular',
                    '.priceContainer_IgF7 span',
                    'div[class*="price"]'
                ]
                
                for selector in price_selectors:
                    price_element = await first_product.query_selector(selector)
                    if price_element:
                        price_text = await price_element.inner_text()
                        # Extract price number
                        price_match = re.search(r'[\d,]+\.\d+', price_text)
                        if price_match:
                            price = float(price_match.group(0).replace(',', ''))
                            result["price"] = price
                            break
                
                if not result["price"]:
                    result["error"] = "Could not find or extract price"
                
                # Try different link selectors
                link_selectors = [
                    'a[data-automation="productItemLink"]',
                    'a.link_3hcyN',
                    'a.product-link',
                    'a.sku-link',
                    'a'
                ]
                
                product_url = None
                for selector in link_selectors:
                    link_element = await first_product.query_selector(selector)
                    if link_element:
                        href = await link_element.get_attribute('href')
                        if href:
                            if href.startswith('/'):
                                product_url = f"https://www.bestbuy.ca{href}"
                            else:
                                product_url = href
                            result["url"] = product_url
                            break
                
                # If we found a product URL, navigate to it and extract sale end date
                if product_url:
                    # Navigate to product detail page
                    await page.goto(product_url, wait_until="domcontentloaded", timeout=30000)
                    
                    # Handle possible dialogs again
                    await self.handle_dialogs(page)
                    
                    # Wait for content to load
                    await page.wait_for_timeout(3000)
                    
                    try:
                        model_element = await page.query_selector('div[data-automation="MODEL_NUMBER_ID"]')
                        if model_element:
                            model_text = await model_element.inner_text()

                            model_match = re.search(r'Model:\s*(\S+)', model_text)
                            if model_match:
                                exact_model = model_match.group(1).strip()
                                result["exact_model"] = exact_model
                                

                                if model_number.lower() in exact_model.lower() or exact_model.lower() in model_number.lower():

                                    pass
                                else:
                                    result["error"] = f"Exact model from details page ({exact_model}) does not match expected model ({model_number})"
                                    await browser.close()
                                    return result
                    except Exception as e:
                        print(f"Error extracting exact model: {str(e)}")
                    
                    # Try to find sale end date
                    try:
                        sale_date_element = await page.query_selector('time[itemprop="priceValidUntil"]')
                        if sale_date_element:
                            sale_end_date = await sale_date_element.inner_text()
                            result["sale_end_date"] = sale_end_date.strip()
                        else:
                            # Also try alternative selectors
                            alt_selectors = [
                                'p.text-micro-lg span time',
                                'span.text-v2-value-red time',
                                'p:has(span:contains("Sale ends")) time'
                            ]
                            
                            for alt_selector in alt_selectors:
                                try:
                                    alt_element = await page.query_selector(alt_selector)
                                    if alt_element:
                                        sale_end_date = await alt_element.inner_text()
                                        result["sale_end_date"] = sale_end_date.strip()
                                        break
                                except Exception:
                                    continue
                    except Exception as e:
                        print(f"Error extracting sale end date: {str(e)}")
                        # Continue without sale end date
                
                await browser.close()
                
        except Exception as e:
            result["error"] = str(e)
        
        return result

async def main():
    # Test case
    products = [
        "Hisense 32\" HD Smart VIDAA LED TV - 32A4KV"
    ]
    
    scraper = BestBuyScraper()
    
    for product in products:
        result = await scraper.scrape_product(product)
        
        if result["price"]:
            print(f"Found at BestBuy: ${result['price']}")
            print(f"URL: {result['url']}")
            if result["sale_end_date"]:
                print(f"Sale ends: {result['sale_end_date']}")
            else:
                print("No sale end date found")
        else:
            print(f"Error: {result['error']}")
            print(f"Search URL: {result['url']}")

if __name__ == "__main__":
    asyncio.run(main())