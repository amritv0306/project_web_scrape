from scrapers.base_scraper import BaseScraper
import re
import time
import gc
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

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
        """Initialize and return a new webdriver instance with improved memory management"""
        try:
            # Add memory optimization options
            self.chrome_options.add_argument("--disable-extensions")
            self.chrome_options.add_argument("--disable-gpu")
            self.chrome_options.add_argument("--disable-features=NetworkService")
            self.chrome_options.add_argument("--window-size=1280,720")
            self.chrome_options.add_argument("--disable-browser-side-navigation")
            self.chrome_options.add_argument("--disable-infobars")
            
            # Limit the browser cache size
            self.chrome_options.add_argument("--disk-cache-size=1")
            self.chrome_options.add_argument("--media-cache-size=1")
            self.chrome_options.add_argument("--disable-application-cache")
            self.chrome_options.add_argument("--disable-cache")
            
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=self.chrome_options)
            
            driver.execute_cdp_cmd('Network.clearBrowserCache', {})
            driver.delete_all_cookies()

            # Set page load timeout
            driver.set_page_load_timeout(30)
            driver.set_script_timeout(30)
            
            return driver
        except Exception as e:
            print(f"Error initializing Chrome driver: {str(e)}")
            # Try with minimal options as fallback
            try:
                minimal_options = Options()
                minimal_options.add_argument("--headless")
                minimal_options.add_argument("--no-sandbox")
                minimal_options.add_argument("--disable-dev-shm-usage")
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=minimal_options)
                return driver
            except Exception as e2:
                print(f"Fallback driver initialization also failed: {str(e2)}")
                raise

    def _extract_key_terms(self, product_name):
        """Extract key terms from product name for better matching"""
        # Remove common words that don't help with matching
        common_words = ['with', 'and', 'for', 'the', 'a', 'an', 'in', 'on', 'by', 'to', 'of']
        
        # Split the product name into words
        words = product_name.lower().split()
        
        # Filter out common words and very short words
        key_terms = [word for word in words if word not in common_words and len(word) > 2]
        
        # Extract brand name (usually the first word)
        brand = words[0] if words else ""
        
        # Find product type (oil, shampoo, etc.)
        product_types = ['oil', 'shampoo', 'conditioner', 'soap', 'lotion', 'cream', 'powder', 'gel']
        product_type = next((word for word in words if word.lower() in product_types), "")
        
        return {
            'all_terms': key_terms,
            'brand': brand,
            'product_type': product_type,
            'important_terms': key_terms[:3]  # First few terms are usually most important
        }

    def search_product(self, product_name, uom):
        """Search for a product on Blinkit with improved fuzzy matching"""
        print(f"Searching for {product_name} {uom} on Blinkit")
        
        # Extract key terms for better searching
        key_terms = self._extract_key_terms(product_name)
        
        # Create a simpler search query using just the brand and product type
        # This increases chances of finding similar products
        if key_terms['product_type']:
            search_query = f"{key_terms['brand']} {key_terms['product_type']}"
        else:
            # Use first 2-3 important terms if product type not found
            search_query = " ".join(key_terms['important_terms'][:3])
        
        # Add UOM only if it's significant (like 1kg vs 500g)
        if uom and len(uom) > 1:
            search_query += f" {uom}"
            
        # Replace spaces with + for URL encoding
        search_query = search_query.replace(" ", "+")
        search_url = f"{self.search_url}{search_query}"
        print(f"Simplified search URL: {search_url}")
        
        driver = None
        try:
            driver = self._init_driver()
            
            # Navigate to search page with retry mechanism
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    driver.get(search_url)
                    break
                except WebDriverException as e:
                    if attempt < max_retries - 1:
                        print(f"Attempt {attempt+1} failed, retrying... Error: {str(e)}")
                        time.sleep(2)
                    else:
                        print(f"Failed to load page after {max_retries} attempts")
                        return None
            
            # Wait for page to load with better error handling
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 
                        ".product-card, .no-results, .empty-state"))
                )
            except TimeoutException:
                print(f"No products found for {search_query} on Blinkit")
                return None
                
            # Check for no results message
            if any(text in driver.page_source.lower() for text in ["no results", "no products found", "couldn't find"]):
                print(f"No products found for {search_query} on Blinkit")
                return None
                
            # Try different product card selectors
            product_card_selectors = [
                ".product-card", 
                "[data-testid='product-card']", 
                ".plp-product", 
                ".product-item"
            ]
            
            product_cards = []
            for selector in product_card_selectors:
                try:
                    cards = driver.find_elements(By.CSS_SELECTOR, selector)
                    if cards:
                        product_cards = cards
                        print(f"Found {len(cards)} product cards using selector: {selector}")
                        break
                except Exception as e:
                    print(f"Error finding product cards with selector {selector}: {str(e)}")
                    continue
                    
            if not product_cards:
                print(f"No product cards found for {search_query} on Blinkit")
                return None
                
            # Try different product name selectors
            name_selectors = [
                ".Product__ProductName-sc-11dk8zk-3",
                ".product-name",
                "[data-testid='product-name']",
                ".item-title",
                "h3.name",
                ".product-title"
            ]
            
            # Store all products with their match scores
            matched_products = []
            
            # Find most relevant product match using fuzzy matching
            for card in product_cards:
                try:
                    card_product_name = None
                    
                    # Try different selectors for product name
                    for selector in name_selectors:
                        try:
                            product_name_element = card.find_element(By.CSS_SELECTOR, selector)
                            card_product_name = product_name_element.text.strip()
                            if card_product_name:
                                print(f"Found product: {card_product_name}")
                                break
                        except NoSuchElementException:
                            continue
                            
                    if not card_product_name:
                        continue
                        
                    # Calculate match score based on key terms
                    match_score = 0
                    card_name_lower = card_product_name.lower()
                    
                    # Brand match is important (higher weight)
                    if key_terms['brand'] in card_name_lower:
                        match_score += 3
                        
                    # Product type match is important
                    if key_terms['product_type'] and key_terms['product_type'] in card_name_lower:
                        match_score += 2
                        
                    # Count how many key terms match
                    for term in key_terms['all_terms']:
                        if term in card_name_lower:
                            match_score += 1
                            
                    # Check for UOM match if provided
                    if uom and uom.lower() in card_name_lower:
                        match_score += 1
                        
                    # Only consider products with a minimum match score
                    if match_score >= 2:
                        # Get product URL
                        try:
                            link_element = card.find_element(By.TAG_NAME, "a")
                            product_url = link_element.get_attribute("href")
                            
                            if product_url:
                                matched_products.append({
                                    'name': card_product_name,
                                    'url': product_url,
                                    'score': match_score
                                })
                        except NoSuchElementException:
                            continue
                except Exception as e:
                    print(f"Error processing card: {str(e)}")
                    continue
            
            # Sort products by match score (highest first)
            matched_products.sort(key=lambda x: x['score'], reverse=True)
            
            # Return the URL of the best match if any found
            if matched_products:
                best_match = matched_products[0]
                print(f"Best match: {best_match['name']} (Score: {best_match['score']})")
                return best_match['url']
                    
            print(f"No matching products found for {product_name} on Blinkit")
            return None
        except Exception as e:
            print(f"Error in Blinkit search: {str(e)}")
            return None
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass  # Ignore errors during driver cleanup
            
            # Force garbage collection to free memory
            gc.collect()

    def extract_product_details(self, url):
        """Extract product details from Blinkit product page"""
        if not url:
            return None
            
        driver = None
        try:
            driver = self._init_driver()
            
            # Navigate to product page with retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    driver.get(url)
                    break
                except WebDriverException as e:
                    if attempt < max_retries - 1:
                        print(f"Attempt {attempt+1} failed, retrying... Error: {str(e)}")
                        time.sleep(2)
                    else:
                        print(f"Failed to load product page after {max_retries} attempts")
                        return None
            
            # Wait for page to load
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 
                        ".product-detail, .pdp-container, .product-info"))
                )
            except TimeoutException:
                print(f"Timed out waiting for product details page to load")
                return None

            # Extract MRP with multiple selector attempts
            mrp_selectors = [
                ".ProductInfo__OriginalPrice-sc-urkcd7-4",
                ".original-price",
                ".mrp",
                ".strike-price",
                "[data-testid='original-price']"
            ]
            
            mrp = "N/A"
            for selector in mrp_selectors:
                try:
                    mrp_element = driver.find_element(By.CSS_SELECTOR, selector)
                    mrp = mrp_element.text.strip()
                    mrp = re.sub(r'[^\d.]', '', mrp)
                    if mrp:
                        break
                except NoSuchElementException:
                    continue

            # Extract Sale Price with multiple selector attempts
            price_selectors = [
                ".ProductInfo__DiscountedPrice-sc-urkcd7-3",
                ".discounted-price",
                ".sale-price",
                ".current-price",
                "[data-testid='current-price']"
            ]
            
            sale_price = "N/A"
            for selector in price_selectors:
                try:
                    price_element = driver.find_element(By.CSS_SELECTOR, selector)
                    sale_price = price_element.text.strip()
                    sale_price = re.sub(r'[^\d.]', '', sale_price)
                    if sale_price:
                        break
                except NoSuchElementException:
                    continue

            # Extract product title with multiple selector attempts
            title_selectors = [
                ".ProductHeader__StyledProductHeader-sc-4rfq5f-0 h1",
                ".product-title",
                ".pdp-title",
                "h1.title",
                "[data-testid='product-title']"
            ]
            
            product_title = ""
            for selector in title_selectors:
                try:
                    title_element = driver.find_element(By.CSS_SELECTOR, selector)
                    product_title = title_element.text.strip()
                    if product_title:
                        break
                except NoSuchElementException:
                    continue
                    
            quantity, uom = self._extract_quantity_uom(product_title)

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
            if driver:
                try:
                    driver.quit()
                except:
                    pass  # Ignore errors during driver cleanup
                
            # Force garbage collection to free memory
            gc.collect()

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
            
        # Try alternative patterns
        alt_pattern = r'(\d+(\.\d+)?)(ml|g|kg|l)'
        match = re.search(alt_pattern, title, re.IGNORECASE)
        
        if match:
            quantity = match.group(1)
            uom = match.group(3).lower()
            return quantity, uom
            
        return "N/A", "N/A"