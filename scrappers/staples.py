# This file was created by Aryaman Rastogi.

# If you have any questions, feel free to ask me on my phone number 647 679 9802

# if you wish to contirbute to this file, please add your name and phone number in the comments below

# this file probably does not work anymore

import asyncio

import re
import os
from playwright.async_api import async_playwright, TimeoutError
import random
import aiohttp

class StaplesScraper:
    """Specialized scraper for Staples Canada website price information"""
    
    def __init__(self):
        self.base_url = "https://www.staples.ca/search?query={}"
    
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
        try:
            cookie_selectors = [
                '#consent_prompt_submit',
                '#onetrust-accept-btn-handler',
                'button.privacy-policy-accept',
                '.accept-cookies',
                '.cookie-consent-accept'
            ]
            
            for selector in cookie_selectors:
                cookie_btn = await page.query_selector(selector)
                if cookie_btn:
                    try:
                        await cookie_btn.click(timeout=5000)
                        await page.wait_for_timeout(1000)
                        break
                    except Exception as e:
                        pass
        except Exception as e:
            pass
    
    async def save_debug_screenshot(self, page, name):
        """Save debug screenshot"""
        try:
            os.makedirs("debug_screenshots", exist_ok=True)
            screenshot_path = f"debug_screenshots/staples_{name}.png"
            await page.screenshot(path=screenshot_path)
            
            # Save HTML for analysis
            html_path = f"debug_screenshots/staples_{name}.html"
            html_content = await page.content()
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
        except Exception as e:
            pass
    
    async def scrape_product(self, product_name: str) -> dict:
        """Scrape Staples price information based on product name"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                result = {
                    "retailer": "Staples",
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
                
                async with async_playwright() as p:
                    # Configure browser to appear more human-like
                    browser = await p.chromium.launch(
                        headless=True, 
                        args=[
                            "--disable-blink-features=AutomationControlled",
                            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
                        ]
                    )
                    
                    context = await browser.new_context(

                        viewport={"width": 1920, "height": 1080},
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                        java_script_enabled=True,
                    )
                    
                    await context.add_init_script("""
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        });
                        Object.defineProperty(navigator, 'plugins', {
                            get: () => [1, 2, 3, 4, 5]
                        });
                    """)
                    
                    page = await context.new_page()
                    
                    # Add random delays to make behavior more human-like
                    await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
                    
                    # Wait for Cloudflare check to complete (may need user interaction)
                    try:
                        # Check if Cloudflare challenge is present
                        cloudflare_challenge = await page.query_selector('.cf-error-details')
                        if cloudflare_challenge:
                            # Save debug information
                            await self.save_debug_screenshot(page, f"{model_number}_cloudflare_blocked")
                            result["error"] = "Blocked by Cloudflare protection"
                            
                            # Wait for manual interaction if not headless
                            if not browser.is_headless:
                                print("Cloudflare challenge detected. Please solve the challenge manually.")
                                print("Waiting 30 seconds for manual intervention...")
                                await page.wait_for_timeout(30000)
                                
                                # Save debug information again after wait
                                await self.save_debug_screenshot(page, f"{model_number}_after_waiting")
                        
                        # Add random human-like delays
                        await page.wait_for_timeout(2000 + (1000 * (3 * random.random())))
                        
                        # Simulate human-like scrolling
                        await page.evaluate("""
                            () => {
                                const scrollHeight = Math.floor(document.body.scrollHeight / 4);
                                window.scrollTo(0, scrollHeight);
                            }
                        """)
                        await page.wait_for_timeout(1000 + (1000 * random.random()))
                        
                        # Handle possible dialogs
                        await self.handle_dialogs(page)
                        
                        # Wait for content to load
                        await page.wait_for_timeout(3000)
                        
                    except Exception as e:
                        await self.save_debug_screenshot(page, f"{model_number}_error")
                        result["error"] = f"Navigation error: {str(e)}"
                        await browser.close()
                        return result
                    
                    # Check if there are search results
                    no_results = await page.query_selector('.search-no-results-container')
                    if no_results:
                        result["error"] = "No search results found"
                        await browser.close()
                        return result
                    
                    # Wait extra time for dynamic content to load
                    await page.wait_for_timeout(5000)
                    
                    # Get first product title for model verification
                    title_selectors = [
                        'a.product-thumbnail__title.product-link',
                        '.product-title a',
                        '.product-thumbnail h3 a',
                        '.product-link'
                    ]
                    
                    product_title = None
                    product_link_element = None
                    
                    for selector in title_selectors:
                        link_element = await page.query_selector(selector)
                        if link_element:
                            product_title = await link_element.inner_text()
                            product_link_element = link_element
                            break
                    
                    if not product_title:
                        result["error"] = "Product title not found"
                        await browser.close()
                        return result
                    
                    # Extract model part from product title (usually the second part)
                    title_parts = product_title.split()
                    model_part = None
                    if len(title_parts) >= 2:
                        # Look for possible model part (like DU8000)
                        for part in title_parts:
                            # Model part usually contains letter and number combinations
                            if re.search(r'[A-Z]+\d+', part):
                                model_part = part
                                break
                        
                        if not model_part:
                            # If no typical pattern found, try using the second element
                            model_part = title_parts[1]
                    
                    # Verify if model part is contained in the input model number
                    model_match = False
                    if model_part and model_number:
                        if model_part.upper() in model_number.upper():
                            model_match = True
                        else:
                            result["error"] = f"Model mismatch: '{model_part}' not found in '{model_number}'"
                    
                    if not model_match:
                        await browser.close()
                        return result
                    
                    # Model matches, continue to get price
                    # Try multiple possible selectors
                    price_selectors = [
                        '.money.pre-money',
                        '.product-thumbnail__price-value',
                        '.product-price',
                        '[data-product-id] .money',
                        '.product-thumbnail__price',
                        '.price',
                        '.current-price',
                        '.price-value'
                    ]
                    
                    price_element = None
                    for selector in price_selectors:
                        price_element = await page.query_selector(selector)
                        if price_element:
                            break
                    
                    if price_element:
                        price_text = await price_element.inner_text()
                        
                        # Extract price number
                        price_match = re.search(r'[\d,]+\.\d+', price_text)
                        if price_match:
                            price = float(price_match.group(0).replace(',', ''))
                            
                            # Get product URL
                            if product_link_element:
                                product_url = await product_link_element.get_attribute('href')
                                if product_url.startswith('/'):
                                    product_url = f"https://www.staples.ca{product_url}"
                                
                                result["url"] = product_url
                            
                            # Set price result
                            result["price"] = price
                        else:
                            result["error"] = "Price extraction failed"
                    else:
                        # Try extracting price directly from page
                        try:
                            page_text = await page.evaluate('() => document.body.innerText')
                            price_matches = re.findall(r'\$\s*([\d,]+\.\d+)', page_text)
                            if price_matches:
                                # Find first price pattern match
                                price = float(price_matches[0].replace(',', ''))
                                result["price"] = price
                            else:
                                result["error"] = "Price element not found"
                        except Exception as e:
                            result["error"] = "Price element not found"
                    
                    await browser.close()
                    
                    await page.wait_for_load_state('networkidle')
                    
                    if await page.query_selector('.cf-error-details'):
                        retry_count += 1
                        await page.wait_for_timeout(5000) 
                        continue
                    
                    return result
                
            except Exception as e:
                retry_count += 1
                if retry_count == max_retries:
                    return {
                        "retailer": "Staples",
                        "product_name": product_name,
                        "price": None,
                        "error": f"Failed after {max_retries} retries: {str(e)}"
                    }
                await page.wait_for_timeout(5000) 
        
        return result

    async def get_product_api(self, model_number: str) -> dict:
        api_url = f"https://www.staples.ca/api/v1/products/search?q={model_number}"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(api_url, headers={
                    'Accept': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
            except Exception as e:
                return None

async def main():
    # Test case
    products = [
        "Samsung 75\" 4K Smart TV - UN75DU8000FXZC"
    ]
    
    scraper = StaplesScraper()
    
    for product in products:
        result = await scraper.scrape_product(product)
        
        if result["price"]:
            print(f"Found at Staples: ${result['price']}")
            print(f"URL: {result['url']}")
        else:
            print(f"Error: {result['error']}")
            print(f"Search URL: {result['url']}")

if __name__ == "__main__":
    asyncio.run(main())