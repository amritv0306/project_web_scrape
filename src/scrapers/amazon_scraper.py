from src.scrapers.base_scraper import BaseScraper
import re

class AmazonScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.amazon.in"
        self.search_url = f"{self.base_url}/s?k="
    
    def search_product(self, product_name, uom):
        search_query = f"{product_name} {uom}".replace(" ", "+")
        search_url = f"{self.search_url}{search_query}"
        # print("------------------")
        print(search_url)
        soup = self.get_soup(search_url)
        # print("------------------")
        print(soup.title)
        # print("------------------")
        # Find the first product result
        product_link = soup.select_one("a.a-link-normal.s-no-outline")
        if product_link:
            return f"{self.base_url}{product_link['href']}"
        return None
    
    def extract_product_details(self, url):
        if not url:
            return None
            
        soup = self.get_soup(url)
        
        # Extract MRP
        mrp_element = soup.select_one(".a-text-strike")
        mrp = mrp_element.text.strip() if mrp_element else "N/A"
        mrp = re.sub(r'[^\d.]', '', mrp) if mrp != "N/A" else mrp
        
        # Extract Sale Price
        price_element = soup.select_one(".a-price-whole")
        sale_price = price_element.text.strip() if price_element else "N/A"
        sale_price = re.sub(r'[^\d.]', '', sale_price) if sale_price != "N/A" else sale_price
        
        # Extract Quantity and UOM
        product_title = soup.select_one("#productTitle").text.strip() if soup.select_one("#productTitle") else ""
        quantity, uom = self._extract_quantity_uom(product_title)
        
        return {
            "url": url,
            "mrp": mrp,
            "sale_price": sale_price,
            "quantity": quantity,
            "uom": uom
        }
    
    def _extract_quantity_uom(self, title):
        # Use regex patterns to extract quantity and UOM from title
        quantity_pattern = r'(\d+(\.\d+)?)\s*(ml|g|kg|l|pcs)'
        match = re.search(quantity_pattern, title, re.IGNORECASE)
        
        if match:
            quantity = match.group(1)
            uom = match.group(3).lower()
            return quantity, uom
            
        return "N/A", "N/A"