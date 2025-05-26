# This file was created by Aryaman Rastogi.

# If you have any questions, feel free to ask me on my phone number 647 679 9802

# if you wish to contirbute to this file, please add your name and phone number in the comments below

# from prodcuts import test_data
import asyncio
import json
from scrappers.amazon import AmazonScraper
from scrappers.bestBuy import BestBuyScraper
from scrappers.costco import CostcoScraper
from scrappers.dufresne_scraper import DufresneScraper
from scrappers.lg import LGScraper
from scrappers.london_drugs import LondonDrugsScraper
from scrappers.terpermans import TeppermansScraper
from scrappers.tanguay import TanguayScraper
from scrappers.staples import StaplesScraper
from scrappers.samsung import SamsungScraper
from scrappers.vision import VisionsScraper

from testdata import test_data # The test data is a list of dicts with only 'name'


SCRAPERS = {
    "Amazon": AmazonScraper,
    "Best_Buy": BestBuyScraper,
    "Costco": CostcoScraper,
    "Dufresne": DufresneScraper,
    "LG": LGScraper,
    "LondonDrugs": LondonDrugsScraper,
    "Terpermans": TeppermansScraper,
    "Tanguay": TanguayScraper,
    "Staples": StaplesScraper,
    "Samsung": SamsungScraper,
    "Vision": VisionsScraper,
}

# async def get_market_prices(products):
#     product = []
#     comparisions = {}
    
#     def append_product_in_results(status, retailer_name, comparisions, product_name, result):
#         if not status:
#             comparisions[product_name]['results'][retailer_name] = {
#                     'found': False,
#                     'result': {}
#                 }
#         else:
#             body = {
#                 'name': result['product_name'],
#                 'price': result['price'],
#                 'url': result['url'],
#                 'price_validity': ""
#             }
#             comparisions[product_name]['results'][retailer_name] = {
#                 'found': True,
#                 'result': body
#             }

#     for product in products:
#         product_name = product['name']
#         product_price = product['price']
#         product_url = product['link']
#         comparisions = comparisions | {
#                             product['name']: {
#                                 "productInfo": {
#                                     "name": product['name'],
#                                     "price": product['price'],
#                                     "url": product['link']                        
#                                 },
#                                 "results": {                                                                        
#                                 }
#                             }
#         }               
        
#         # get the market price
#         # dict output:
    
#         # '''
#         # product: {},
#         # results: [
#                 # Amazon: {
#                 #     found: true,
#                 #     result: {
#                 #         'name': product_name,
#                 #         'price': product_price,
#                 #         'url': product_url,
#                 #         'price_validity': market_price
#                 #     }
#                 # },
#                 # Bestbuy: {
#                 #     found: true,
#                 #     result: {
#                 #         'name': product_name,
#                 #         'price': product_price,
#                 #         'url': product_url,
#                 #         'price_validity': market_price
#                 #     }
#                 # },
#                 # Walmart: {
#                 #     found: true,
#                 #     result: {
#                 #         'name': product_name,
#                 #         'price': product_price,
#                 #         'url': product_url,
#                 #         'price_validity': market_price
#                 #     }
#                 # }
#         #     ]
        
#         # '''
        
#         # amazon = AmazonScraper()
#         # amazon_result = await amazon.scrape_product(product_name)

#         # check if the product is found
#         # if amazon_result['error']:
#         #     print(f"Amazon: {amazon_result['error']}")
#         #     # comparisions[product_name]['results']['Amazon'] = {
#         #     #     'found': False,
#         #     #     'result': {}
#         #     # }
#         #     append_product_in_results(False, 'Amazon', comparisions, product_name, amazon_result)
#         # else:
#         #     print(f"Amazon: {amazon_result['price']}")
#         #     # amazon = {
#         #     #     'name': amazon_result['product_name'],
#         #     #     'price': amazon_result['price'],
#         #     #     'url': amazon_result['url'],
#         #     #     'price_validity': ""
#         #     # }
#         #     # comparisions[product_name]['results']['Amazon'] = {
#         #     #     'found': True,
#         #     #     'result': amazon
#         #     # }
#         #     append_product_in_results(True, 'Amazon', comparisions, product_name, amazon_result)


#         # best_buy = BestBuyScraper()
#         # best_buy_result = await best_buy.scrape_product(product_name)
        
#         # if best_buy_result['error']:
#         #     print(f"Best Buy: {best_buy_result['error']}")            
#         #     append_product_in_results(False, 'Best_Buy', comparisions, product_name, best_buy_result)
#         # else:
#         #     print(f"Best Buy: {best_buy_result['price']}")
#         #     append_product_in_results(True, 'Best_Buy', comparisions, product_name, best_buy_result)
        
#         costCo = CostcoScraper()
#         costCo_result = await costCo.scrape_product(product_name)

#         if costCo_result['error']:
#             print(f"Costco: {costCo_result['error']}")
#             append_product_in_results(False, 'Costco', comparisions, product_name, costCo_result)
#         else:
#             print(f"Costco: {costCo_result['price']}")
#             append_product_in_results(True, 'Costco', comparisions, product_name, costCo_result)

#     return comparisions
# async def main():
#     print(await get_market_prices(test_data))

async def get_market_prices(products):
    comparisons = {}

    for product in products:
        name = product["name"]
        comparisons[name] = {
            "productInfo": {
                "name": name,
                "price": "",   # No original price provided
                "url": ""      # No product URL provided
            },
            "results": {}
        }

        for retailer, ScraperClass in SCRAPERS.items():
            print(f"Checking {retailer} for '{name}'...")
            try:
                scraper = ScraperClass()
                result = await scraper.scrape_product(name)
                if result.get("error") or result.get("price") is None:
                    print(f"{retailer}: {result.get('error')}")
                    comparisons[name]["results"][retailer] = {"found": False, "result": {}}
                else:
                    print(f"{retailer}: ${result['price']}")
                    comparisons[name]["results"][retailer] = {
                        "found": True,
                        "result": {
                            "name": result.get("product_name"),
                            "price": result.get("price"),
                            "url": result.get("url"),
                            "price_validity": result.get("sale_end_date", "")
                        }
                    }
            except Exception as e:
                print(f"{retailer} crashed: {e}")
                comparisons[name]["results"][retailer] = {
                    "found": False,
                    "result": {},
                    "error": str(e)
                }

    # Compute best price
    for product, info in comparisons.items():
        lowest = None
        for retailer, result in info["results"].items():
            if result["found"]:
                price = result["result"]["price"]
                if lowest is None or price < lowest["price"]:
                    lowest = {
                        "retailer": retailer,
                        "price": price,
                        "url": result["result"]["url"]
                    }
        info["best_price"] = lowest if lowest else {"retailer": None, "price": None, "url": None}

    return comparisons


async def main():
    results = await get_market_prices(test_data)

    print("\n================ Final Summary ================\n")
    for product, data in results.items():
        print(f"{product}:")
        for retailer, r_data in data["results"].items():
            if r_data["found"]:
                print(f"  - {retailer}: ${r_data['result']['price']} ({r_data['result']['url']})")
            else:
                print(f"  - {retailer}: Not Found")
        if data.get("best_price") and data["best_price"]["retailer"]:
            print(f"Best Price: ${data['best_price']['price']} at {data['best_price']['retailer']}")
        else:
            print("No available price found")
        print()

    # Save to JSON
    output_path = f"price_comparison_output.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Results exported to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())