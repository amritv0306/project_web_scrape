import requests
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
import random

session = requests.Session()

user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
]

# proxies = [
#     {'http': 'http://proxy1.example.com:8080', 'https': 'https://proxy1.example.com:8080'},
#     {'http': 'http://proxy2.example.com:8080', 'https': 'https://proxy2.example.com:8080'},
# ]
# proxy = random.choice(proxies)

class BaseScraper(ABC):
    def __init__(self):
        # self.headers = {
        #     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        # }
        self.headers = {'User-Agent': random.choice(user_agents)}
    
    @abstractmethod
    def search_product(self, product_name, uom):
        """Search for a product and return matching product URL"""
        pass
    
    @abstractmethod
    def extract_product_details(self, url):
        """Extract product details from product page"""
        pass
    
    def get_soup(self, url):
        """Get BeautifulSoup object from URL"""
        # response = session.get(url, headers=self.headers, proxies=proxy)
        response = session.get(url, headers=self.headers)
        return BeautifulSoup(response.content, 'html.parser')