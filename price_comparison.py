# This file was created by Aryaman Rastogi.
# If you have any questions, feel free to ask me on my phone number 647 679 9802
# If you wish to contribute to this file, please add your name and phone number in the comments below

import asyncio
import json
import csv

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

from testdata import test_data  # The test data is a list of dicts with only 'name'

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
    json_output_path = "price_comparison_output.json"
    with open(json_output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"✅ JSON results exported to: {json_output_path}")

    # Save to CSV
    csv_output_path = "price_comparison_output.csv"
    with open(csv_output_path, mode="w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Product", "Retailer", "Price", "URL", "Best Price"])
        for product, info in results.items():
            best_retailer = info["best_price"]["retailer"] if info.get("best_price") else None
            for retailer, r_data in info["results"].items():
                if r_data["found"]:
                    is_best = "✅" if retailer == best_retailer else ""
                    writer.writerow([
                        product,
                        retailer,
                        r_data["result"]["price"],
                        r_data["result"]["url"],
                        is_best
                    ])
    print(f"✅ CSV results exported to: {csv_output_path}")


if __name__ == "__main__":
    asyncio.run(main())
