import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import time
import random
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

from scrapers.amazon_scraper import AmazonScraper
from scrapers.blinkit_scraper import BlinkatScraper
# from scrapers.Blinkit import BlinkatScraper
from scrapers.zepto_scraper import ZeptoScraper
# from scrapers.Zepto import ZeptoScraper
from utils import load_data, save_data

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("product_matcher.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ProductMatcher")

@dataclass
class ScraperResult:
    url: Optional[str] = None
    mrp: Optional[float] = None
    sale_price: Optional[float] = None
    quantity: Optional[str] = None
    uom: Optional[str] = None

class ProductMatcher:
    # Constants
    PLATFORMS = ['amazon', 'blinkit', 'zepto']
    # PLATFORMS = ['amazon']
    FIELDS = ['url', 'mrp', 'sale_price', 'quantity', 'uom']
    MAX_WORKERS = 10
    MIN_DELAY = 2
    MAX_DELAY = 5
    
    def __init__(self, max_retries: int = 3, retry_delay: int = 5):
        """
        Initialize the ProductMatcher with scrapers and configuration.
        
        Args:
            max_retries: Maximum number of retries for failed requests
            retry_delay: Delay between retries in seconds
        """
        self.amazon_scraper = AmazonScraper()
        self.blinkit_scraper = BlinkatScraper()
        self.zepto_scraper = ZeptoScraper()
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def process_skus(self, input_file: str) -> pd.DataFrame:
        """
        Process SKUs from input file and collect data from multiple platforms.
        
        Args:
            input_file: Path to the input CSV file
            
        Returns:
            DataFrame with collected data from all platforms
        """
        logger.info(f"Starting to process SKUs from {input_file}")
        
        try:
            # Load SKUs data
            df = load_data(input_file)
            
            # Initialize result columns
            self._initialize_result_columns(df)
            
            # Process SKUs in parallel
            results = self._process_skus_in_parallel(df)
            
            # Update DataFrame with results
            self._update_dataframe_with_results(df, results)
            
            logger.info(f"Successfully processed {len(df)} SKUs")
            return df
            
        except Exception as e:
            logger.error(f"Failed to process SKUs: {str(e)}", exc_info=True)
            raise
    
    def _initialize_result_columns(self, df: pd.DataFrame) -> None:
        """Initialize result columns in the DataFrame."""
        for platform in self.PLATFORMS:
            for field in self.FIELDS:
                df[f"{platform}_{field}"] = ""
    
    def _process_skus_in_parallel(self, df: pd.DataFrame) -> List[Tuple[int, Dict[str, Any]]]:
        """Process SKUs in parallel using ThreadPoolExecutor."""
        results = []
        
        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            futures = []
            
            for index, row in df.iterrows():
                # Submit task to executor
                future = executor.submit(self._process_single_sku_with_retry, row, index)
                futures.append((future, index))
                
                # Add jitter to prevent rate limiting
                time.sleep(random.uniform(self.MIN_DELAY, self.MAX_DELAY))
            
            # Collect results
            for future, index in futures:
                try:
                    result = future.result()
                    results.append((index, result))
                except Exception as e:
                    logger.error(f"Failed to get result for index {index}: {str(e)}")
                    results.append((index, {platform: None for platform in self.PLATFORMS}))
        
        return results
    
    def _update_dataframe_with_results(self, df: pd.DataFrame, results: List[Tuple[int, Dict[str, Any]]]) -> None:
        """Update DataFrame with collected results."""
        for index, result in results:
            for platform in self.PLATFORMS:
                platform_result = result.get(platform)
                if platform_result:
                    for field in self.FIELDS:
                        df.at[index, f"{platform}_{field}"] = platform_result.get(field, "N/A")
    
    def _process_single_sku_with_retry(self, row: pd.Series, index: int) -> Dict[str, Any]:
        """Process a single SKU with retry mechanism."""
        retries = 0
        while retries <= self.max_retries:
            try:
                return self._process_single_sku(row, index)
            except Exception as e:
                retries += 1
                logger.warning(f"Retry {retries}/{self.max_retries} for {row['Item Name']}: {str(e)}")
                if retries <= self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"Failed to process {row['Item Name']} after {self.max_retries} retries")
                    raise
    
    def _process_single_sku(self, row: pd.Series, index: int) -> Dict[str, Dict[str, Any]]:
        """
        Process a single SKU by searching on all platforms.
        
        Args:
            row: DataFrame row containing product information
            index: Row index for logging purposes
            
        Returns:
            Dictionary with results from all platforms
        """
        logger.info(f"Processing {index}: {row['Item Name']}")
        product_name = row['Item Name']
        uom = row['UOM']
        
        result = {platform: None for platform in self.PLATFORMS}
        
        # Process each platform in sequence
        self._search_on_amazon(product_name, uom, result)
        self._search_on_blinkit(product_name, uom, result)
        self._search_on_zepto(product_name, uom, result)
        
        return result
    
    def _search_on_amazon(self, product_name: str, uom: str, result: Dict[str, Any]) -> None:
        """Search for product on Amazon and update result."""
        try:
            amazon_url = self.amazon_scraper.search_product(product_name, uom)
            if amazon_url:
                result['amazon'] = self.amazon_scraper.extract_product_details(amazon_url)
                logger.info(f"Found product on Amazon: {amazon_url}")
            else:
                logger.info("URL not found on amazon")
        except Exception as e:
            logger.error(f"Error with Amazon for {product_name}: {str(e)}")
    
    def _search_on_blinkit(self, product_name: str, uom: str, result: Dict[str, Any]) -> None:
        """Search for product on Blinkit and update result."""
        try:
            blinkit_url = self.blinkit_scraper.search_product(product_name, uom)
            if blinkit_url:
                result['blinkit'] = self.blinkit_scraper.extract_product_details(blinkit_url)
                logger.info(f"Found product on Blinkit: {blinkit_url}")
            else:
                logger.info("URL not found on blinkit")
        except Exception as e:
            logger.error(f"Error with Blinkit for {product_name}: {str(e)}")
    
    def _search_on_zepto(self, product_name: str, uom: str, result: Dict[str, Any]) -> None:
        """Search for product on Zepto and update result."""
        try:
            zepto_url = self.zepto_scraper.search_product(product_name, uom)
            if zepto_url:
                result['zepto'] = self.zepto_scraper.extract_product_details(zepto_url)
                logger.info(f"Found product on Zepto: {zepto_url}")
            else:
                logger.info("URL not found on zepto")
        except Exception as e:
            logger.error(f"Error with Zepto for {product_name}: {str(e)}")


if __name__ == "__main__":
    try:
        input_file = "data/sample_input.csv"
        output_file = "data/result.csv"
        
        matcher = ProductMatcher(max_retries=3, retry_delay=5)
        result_df = matcher.process_skus(input_file)
        save_data(result_df, output_file)
        
        logger.info(f"Processing complete. Results saved to {output_file}")
    except Exception as e:
        logger.critical(f"Program failed: {str(e)}", exc_info=True)
