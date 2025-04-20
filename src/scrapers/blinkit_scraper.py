from scrapers.base_scraper import BaseScraper
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

class BlinkatScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://blinkit.com"
        self.search_url = f"{self.base_url}/search/"
        
        # Set up Chrome options for headless browsing
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument(f"user-agent={self.headers['User-Agent']}")
        
    def _init_driver(self):
        """Initialize and return a new webdriver instance"""
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=self.chrome_options)
        return driver
    
    def search_product(self, product_name, uom):
        """Search for a product on Blinkit and return the matching product URL"""
        search_query = f"{product_name} {uom}".replace(" ", "%20")
        search_url = f"{self.search_url}{search_query}"
        
        driver = self._init_driver()
        try:
            driver.get(search_url)
            # Wait for products to load
            time.sleep(3)
            
            # Look for product cards
            product_cards = driver.find_elements(By.CSS_SELECTOR, ".product-card")
            
            if not product_cards:
                return None
            
            # Find most relevant product match
            for card in product_cards:
                try:
                    # Get product name
                    product_name_element = card.find_element(By.CSS_SELECTOR, ".Product__ProductName-sc-11dk8zk-3")
                    card_product_name = product_name_element.text.strip()
                    
                    # Check for reasonable match (product name contains searched terms)
                    search_terms = product_name.lower().split()
                    if all(term in card_product_name.lower() for term in search_terms[:2]):
                        # Get product URL
                        link_element = card.find_element(By.TAG_NAME, "a")
                        product_url = link_element.get_attribute("href")
                        return product_url
                except Exception as e:
                    continue
            
            return None
        finally:
            driver.quit()
    
    def extract_product_details(self, url):
        """Extract product details from Blinkit product page"""
        if not url:
            return None
            
        driver = self._init_driver()
        try:
            driver.get(url)
            # Wait for page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".product-detail"))
            )
            
            # Extract MRP
            try:
                mrp_element = driver.find_element(By.CSS_SELECTOR, ".ProductInfo__OriginalPrice-sc-urkcd7-4")
                mrp = mrp_element.text.strip()
                mrp = re.sub(r'[^\d.]', '', mrp)
            except:
                mrp = "N/A"
            
            # Extract Sale Price
            try:
                price_element = driver.find_element(By.CSS_SELECTOR, ".ProductInfo__DiscountedPrice-sc-urkcd7-3")
                sale_price = price_element.text.strip()
                sale_price = re.sub(r'[^\d.]', '', sale_price)
            except:
                sale_price = "N/A"
            
            # Extract product title to get quantity and UOM
            try:
                title_element = driver.find_element(By.CSS_SELECTOR, ".ProductHeader__StyledProductHeader-sc-4rfq5f-0 h1")
                product_title = title_element.text.strip()
                quantity, uom = self._extract_quantity_uom(product_title)
            except:
                quantity, uom = "N/A", "N/A"
            
            return {
                "url": url,
                "mrp": mrp,
                "sale_price": sale_price,
                "quantity": quantity,
                "uom": uom
            }
        except Exception as e:
            print(f"Error extracting details from Blinkit: {str(e)}")
            return None
        finally:
            driver.quit()
    
    def _extract_quantity_uom(self, title):
        """Extract quantity and UOM from product title"""
        # Common UOM patterns in Blinkit product titles
        quantity_pattern = r'(\d+(\.\d+)?)\s*(ml|g|kg|l|pcs|gm)'
        match = re.search(quantity_pattern, title, re.IGNORECASE)
        
        if match:
            quantity = match.group(1)
            uom = match.group(3).lower()
            # Standardize some common UOMs
            if uom == 'gm':
                uom = 'g'
            return quantity, uom
            
        return "N/A", "N/A"