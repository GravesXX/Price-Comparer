# This file was created by Aryaman Rastogi.

# If you have any questions, feel free to ask me on my phone number 647 679 9802

# if you wish to contirbute to this file, please add your name and phone number in the comments below

# from prodcuts import test_data
import asyncio
from scrappers.amazon import AmazonScraper
from scrappers.bestBuy import BestBuyScraper
from scrappers.costco import CostcoScraper


async def get_market_prices(products):
    product = []
    comparisions = {}
    
    def append_product_in_results(status, retailer_name, comparisions, product_name, result):
        if not status:
            comparisions[product_name]['results'][retailer_name] = {
                    'found': False,
                    'result': {}
                }
        else:
            body = {
                'name': result['product_name'],
                'price': result['price'],
                'url': result['url'],
                'price_validity': ""
            }
            comparisions[product_name]['results'][retailer_name] = {
                'found': True,
                'result': body
            }

    for product in products:
        product_name = product['name']
        product_price = product['price']
        product_url = product['link']
        comparisions = comparisions | {
                            product['name']: {
                                "productInfo": {
                                    "name": product['name'],
                                    "price": product['price'],
                                    "url": product['link']                        
                                },
                                "results": {                                                                        
                                }
                            }
        }               
        
        # get the market price
        # dict output:
    
        # '''
        # product: {},
        # results: [
                # Amazon: {
                #     found: true,
                #     result: {
                #         'name': product_name,
                #         'price': product_price,
                #         'url': product_url,
                #         'price_validity': market_price
                #     }
                # },
                # Bestbuy: {
                #     found: true,
                #     result: {
                #         'name': product_name,
                #         'price': product_price,
                #         'url': product_url,
                #         'price_validity': market_price
                #     }
                # },
                # Walmart: {
                #     found: true,
                #     result: {
                #         'name': product_name,
                #         'price': product_price,
                #         'url': product_url,
                #         'price_validity': market_price
                #     }
                # }
        #     ]
        
        # '''
        
        # amazon = AmazonScraper()
        # amazon_result = await amazon.scrape_product(product_name)

        # check if the product is found
        # if amazon_result['error']:
        #     print(f"Amazon: {amazon_result['error']}")
        #     # comparisions[product_name]['results']['Amazon'] = {
        #     #     'found': False,
        #     #     'result': {}
        #     # }
        #     append_product_in_results(False, 'Amazon', comparisions, product_name, amazon_result)
        # else:
        #     print(f"Amazon: {amazon_result['price']}")
        #     # amazon = {
        #     #     'name': amazon_result['product_name'],
        #     #     'price': amazon_result['price'],
        #     #     'url': amazon_result['url'],
        #     #     'price_validity': ""
        #     # }
        #     # comparisions[product_name]['results']['Amazon'] = {
        #     #     'found': True,
        #     #     'result': amazon
        #     # }
        #     append_product_in_results(True, 'Amazon', comparisions, product_name, amazon_result)


        # best_buy = BestBuyScraper()
        # best_buy_result = await best_buy.scrape_product(product_name)
        
        # if best_buy_result['error']:
        #     print(f"Best Buy: {best_buy_result['error']}")            
        #     append_product_in_results(False, 'Best_Buy', comparisions, product_name, best_buy_result)
        # else:
        #     print(f"Best Buy: {best_buy_result['price']}")
        #     append_product_in_results(True, 'Best_Buy', comparisions, product_name, best_buy_result)
        
        costCo = CostcoScraper()
        costCo_result = await costCo.scrape_product(product_name)

        if costCo_result['error']:
            print(f"Costco: {costCo_result['error']}")
            append_product_in_results(False, 'Costco', comparisions, product_name, costCo_result)
        else:
            print(f"Costco: {costCo_result['price']}")
            append_product_in_results(True, 'Costco', comparisions, product_name, costCo_result)

    return comparisions
async def main():
    print(await get_market_prices(test_data))

if __name__ == "__main__":
    asyncio.run(main())