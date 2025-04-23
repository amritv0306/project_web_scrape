import pandas as pd
import re
from urllib.parse import quote

def load_data(file_path):
    """Load data from CSV file"""
    print("Processing first 100 rows")
    return pd.read_csv(file_path) # file size limited to only top 100 rows
    # return pd.read_csv(file_path)

def save_data(data, file_path):
    """Save data to CSV file"""
    data.to_csv(file_path, index=False)

def clean_product_name(name):
    """Clean product name for better matching"""
    # Remove special characters and extra spaces
    name = re.sub(r'[^\w\s]', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def generate_search_query(product_name, uom):
    """Generate search query for product"""
    query = f"{clean_product_name(product_name)} {uom}"
    return quote(query)

def calculate_price_difference(row):
    """Calculate price difference between Instamart and competitor"""
    try:
        instamart_price = float(row['instamart_price'])
        competitor_price = float(row['sale_price'])
        return instamart_price - competitor_price
    except (ValueError, TypeError):
        return None