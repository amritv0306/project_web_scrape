import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import time
import random
from scrapers.amazon_scraper import AmazonScraper
from scrapers.blinkit_scraper import BlinkatScraper
from scrapers.zepto_scraper import ZeptoScraper
from utils import load_data, save_data

class ProductMatcher:
    def __init__(self):
        self.amazon_scraper = AmazonScraper()
        self.blinkit_scraper = BlinkatScraper()
        self.zepto_scraper = ZeptoScraper()
    
    def process_skus(self, input_file):
        """Process SKUs from input file"""
        # Load SKUs data
        df = load_data(input_file)
        
        # Add columns for competitor data
        platforms = ['amazon', 'blinkit', 'zepto']
        fields = ['url', 'mrp', 'sale_price', 'quantity', 'uom']
        
        for platform in platforms:
            for field in fields:
                df[f"{platform}_{field}"] = None
        
        # Process each SKU
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for index, row in df.iterrows():
                future = executor.submit(
                    self.process_single_sku, row, index
                )
                futures.append((future, index))
                time.sleep(random.uniform(2, 5))  # Prevent rate limiting
            
            # Collect results
            for future, index in futures:
                result = future.result()
                for platform in platforms:
                    if result[platform]:
                        for field in fields:
                            df.at[index, f"{platform}_{field}"] = result[platform].get(field, "N/A")
        
        return df
    
    def process_single_sku(self, row, index):
        """Process a single SKU"""
        print(f"Processing {index}: {row['Item Name']}")
        product_name = row['Item Name']
        uom = row['UOM']
        
        result = {
            'amazon': None,
            'blinkit': None,
            'zepto': None
        }
        
        # Search on Amazon
        try:
            amazon_url = self.amazon_scraper.search_product(product_name, uom)
            if amazon_url:
                result['amazon'] = self.amazon_scraper.extract_product_details(amazon_url)
        except Exception as e:
            print(f"Error with Amazon for {product_name}: {str(e)}")
        
        # Search on Blinkit
        try:
            blinkit_url = self.blinkit_scraper.search_product(product_name, uom)
            if blinkit_url:
                result['blinkit'] = self.blinkit_scraper.extract_product_details(blinkit_url)
        except Exception as e:
            print(f"Error with Blinkit for {product_name}: {str(e)}")
        
        # Search on Zepto
        try:
            zepto_url = self.zepto_scraper.search_product(product_name, uom)
            if zepto_url:
                result['zepto'] = self.zepto_scraper.extract_product_details(zepto_url)
        except Exception as e:
            print(f"Error with Zepto for {product_name}: {str(e)}")
        
        return result

if __name__ == "__main__":
    matcher = ProductMatcher()
    # test_df = pd.read_csv("data/sample_input.csv").head()
    result_df = matcher.process_skus("data/sample_input.csv")
    save_data(result_df, "data/result.csv")
    print("Processing complete. Results saved to data/result.csv")