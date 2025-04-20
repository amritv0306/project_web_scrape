from scrapers.base_scraper import BaseScraper
import re
from playwright.sync_api import sync_playwright
import time

class ZeptoScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.zeptonow.com"
        self.search_url = f"{self.base_url}/search?q="
    
    def _init_playwright(self):
        """Initialize playwright and return browser and context"""
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=self.headers['User-Agent'],
            viewport={"width": 1280, "height": 720}
        )
        return playwright, browser, context
    
    def search_product(self, product_name, uom):
        """Search for a product on Zepto and return the matching product URL"""
        search_query = f"{product_name} {uom}".replace(" ", "%20")
        search_url = f"{self.search_url}{search_query}"
        
        playwright, browser, context = self._init_playwright()
        try:
            page = context.new_page()
            
            # Navigate to search page
            page.goto(search_url)
            
            # Wait for search results to load
            page.wait_for_selector(".search-item-card", timeout=10000)
            
            # First, check if we need to set a delivery location
            if "select your location" in page.content().lower():
                # Handle location setting if needed
                # This is a placeholder - actual implementation would depend on Zepto's UI
                try:
                    # Click on location input
                    page.click(".location-selector")
                    # Type a default location (e.g., Mumbai)
                    page.fill(".location-input", "Mumbai")
                    # Select first suggestion
                    page.click(".location-suggestion")
                    # Wait for page to reload with products
                    page.wait_for_selector(".search-item-card", timeout=10000)
                except:
                    print("Could not set location on Zepto")
                    return None
            
            # Extract product cards
            product_cards = page.query_selector_all(".search-item-card")
            
            if not product_cards:
                return None
            
            # Find most relevant product match
            for card in product_cards:
                try:
                    # Get product name
                    product_name_element = card.query_selector(".product-name")
                    if not product_name_element:
                        continue
                    
                    card_product_name = product_name_element.inner_text().strip()
                    
                    # Check for reasonable match
                    search_terms = product_name.lower().split()
                    if any(term in card_product_name.lower() for term in search_terms[:3]):
                        # Get product URL
                        link_element = card.query_selector("a")
                        if link_element:
                            href = link_element.get_attribute("href")
                            if href:
                                # Some links might be relative paths
                                if href.startswith("/"):
                                    return f"{self.base_url}{href}"
                                else:
                                    return href
                except Exception as e:
                    continue
            
            return None
        finally:
            browser.close()
            playwright.stop()
    
    def extract_product_details(self, url):
        """Extract product details from Zepto product page"""
        if not url:
            return None
        
        playwright, browser, context = self._init_playwright()
        try:
            page = context.new_page()
            page.goto(url)
            
            # Wait for product details to load
            page.wait_for_selector(".product-detail-container", timeout=10000)
            
            # Extract MRP
            try:
                mrp_element = page.query_selector(".strikethrough-price")
                mrp = mrp_element.inner_text().strip() if mrp_element else "N/A"
                mrp = re.sub(r'[^\d.]', '', mrp) if mrp != "N/A" else mrp
            except:
                mrp = "N/A"
            
            # Extract Sale Price
            try:
                price_element = page.query_selector(".actual-price")
                sale_price = price_element.inner_text().strip() if price_element else "N/A"
                sale_price = re.sub(r'[^\d.]', '', sale_price) if sale_price != "N/A" else sale_price
            except:
                sale_price = "N/A"
            
            # Extract product title for quantity and UOM
            try:
                title_element = page.query_selector(".product-title")
                product_title = title_element.inner_text().strip() if title_element else ""
                
                # Try to find quantity/UOM from the product details section as well
                details_element = page.query_selector(".product-weight")
                product_details = details_element.inner_text().strip() if details_element else ""
                
                # Combine title and details for better pattern matching
                combined_text = f"{product_title} {product_details}"
                quantity, uom = self._extract_quantity_uom(combined_text)
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
            print(f"Error extracting details from Zepto: {str(e)}")
            return None
        finally:
            browser.close()
            playwright.stop()
    
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
            quantity