from src.scrapers.base_scraper import BaseScraper
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time

class ZeptoScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.zeptonow.com"
        self.search_url = f"{self.base_url}/search?q="
    
    def _init_selenium(self):
        """Initialize Selenium WebDriver and return driver"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument(f"user-agent={self.headers['User-Agent']}")
        chrome_options.add_argument("--window-size=1280,720")
        
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    
    def search_product(self, product_name, uom):
        """Search for a product on Zepto and return the matching product URL"""
        search_query = f"{product_name} {uom}".replace(" ", "%20")
        search_url = f"{self.search_url}{search_query}"
        
        driver = self._init_selenium()
        try:
            # Navigate to search page
            driver.get(search_url)
            
            # Wait for search results to load
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "search-item-card")))
            
            # First, check if we need to set a delivery location
            if "select your location" in driver.page_source.lower():
                # Handle location setting if needed
                try:
                    # Click on location input
                    location_selector = driver.find_element(By.CLASS_NAME, "location-selector")
                    location_selector.click()
                    
                    # Type a default location (e.g., Mumbai)
                    location_input = driver.find_element(By.CLASS_NAME, "location-input")
                    location_input.send_keys("Mumbai")
                    
                    # Select first suggestion
                    location_suggestion = driver.find_element(By.CLASS_NAME, "location-suggestion")
                    location_suggestion.click()
                    
                    # Wait for page to reload with products
                    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "search-item-card")))
                except (TimeoutException, NoSuchElementException):
                    print("Could not set location on Zepto")
                    return None
            
            # Extract product cards
            product_cards = driver.find_elements(By.CLASS_NAME, "search-item-card")
            
            if not product_cards:
                return None
            
            # Find most relevant product match
            for card in product_cards:
                try:
                    # Get product name
                    product_name_element = card.find_element(By.CLASS_NAME, "product-name")
                    card_product_name = product_name_element.text.strip()
                    
                    # Check for reasonable match
                    search_terms = product_name.lower().split()
                    if any(term in card_product_name.lower() for term in search_terms[:3]):
                        # Get product URL
                        link_element = card.find_element(By.TAG_NAME, "a")
                        href = link_element.get_attribute("href")
                        if href:
                            # Some links might be relative paths
                            if href.startswith("/"):
                                return f"{self.base_url}{href}"
                            else:
                                return href
                except (NoSuchElementException, Exception) as e:
                    continue
            
            return None
        finally:
            driver.quit()
    
    def extract_product_details(self, url):
        """Extract product details from Zepto product page"""
        if not url:
            return None
        
        driver = self._init_selenium()
        try:
            driver.get(url)
            
            # Wait for product details to load
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "product-detail-container")))
            
            # Extract MRP
            try:
                mrp_element = driver.find_element(By.CLASS_NAME, "strikethrough-price")
                mrp = mrp_element.text.strip()
                mrp = re.sub(r'[^\d.]', '', mrp) if mrp != "N/A" else mrp
            except NoSuchElementException:
                mrp = "N/A"
            
            # Extract Sale Price
            try:
                price_element = driver.find_element(By.CLASS_NAME, "actual-price")
                sale_price = price_element.text.strip()
                sale_price = re.sub(r'[^\d.]', '', sale_price) if sale_price != "N/A" else sale_price
            except NoSuchElementException:
                sale_price = "N/A"
            
            # Extract product title for quantity and UOM
            try:
                title_element = driver.find_element(By.CLASS_NAME, "product-title")
                product_title = title_element.text.strip()
                
                # Try to find quantity/UOM from the product details section as well
                try:
                    details_element = driver.find_element(By.CLASS_NAME, "product-weight")
                    product_details = details_element.text.strip()
                except NoSuchElementException:
                    product_details = ""
                
                # Combine title and details for better pattern matching
                combined_text = f"{product_title} {product_details}"
                quantity, uom = self._extract_quantity_uom(combined_text)
            except NoSuchElementException:
                quantity, uom = "N/A", "N/A"
            
            return {
                "url": url,
                "mrp": mrp,
                "sale_price": sale_price,
                "quantity": quantity,
                "uom": uom
            }
        except Exception as e:
            print(f"Error extracting details from Zepto: {str(e)}")
            return None
        finally:
            driver.quit()
    
    def _extract_quantity_uom(self, text):
        """Extract quantity and UOM from product text"""
        # Common UOM patterns in Zepto product descriptions
        quantity_pattern = r'(\d+(\.\d+)?)\s*(ml|g|kg|l|pcs|pack|gms)'
        match = re.search(quantity_pattern, text, re.IGNORECASE)
        
        if match:
            quantity = match.group(1)
            uom = match.group(3).lower()
            # Standardize UOMs
            if uom == 'gms':
                uom = 'g'
            elif uom == 'pack':
                uom = 'pcs'
            return quantity, uom
        
        # Try alternative patterns that Zepto might use
        alt_pattern = r'(\d+(\.\d+)?)(ml|g|kg|l)'
        match = re.search(alt_pattern, text, re.IGNORECASE)
        if match:
            quantity = match.group(1)
            uom = match.group(3).lower()
            return quantity, uom
            
        return "N/A", "N/A"