import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

class ProductAnalyzer:
    def __init__(self, data):
        self.data = data
    
    def calculate_price_differences(self):
        """Calculate price differences with competitors"""
        platforms = ['amazon', 'blinkit', 'zepto']
        for platform in platforms:
            price_col = f"{platform}_sale_price"
            diff_col = f"{platform}_price_diff"
            
            if price_col in self.data.columns:
                self.data[diff_col] = self.data.apply(
                    lambda row: self._calc_diff(row['instamart_sale_price'], row[price_col]), 
                    axis=1
                )
        return self.data
    
    def _calc_diff(self, price1, price2):
        try:
            return float(price1) - float(price2)
        except (ValueError, TypeError):
            return None
    
    def find_best_deals(self):
        """Find products with largest price differences"""
        platforms = ['amazon', 'blinkit', 'zepto']
        best_deals = []
        
        for platform in platforms:
            diff_col = f"{platform}_price_diff"
            if diff_col in self.data.columns:
                platform_deals = self.data.sort_values(by=diff_col, ascending=False).head(5)
                for _, row in platform_deals.iterrows():
                    best_deals.append({
                        'item_name': row['item_name'],
                        'platform': platform,
                        'instamart_price': row['instamart_sale_price'],
                        'competitor_price': row[f"{platform}_sale_price"],
                        'price_diff': row[diff_col]
                    })
        
        return pd.DataFrame(best_deals)
    
    def generate_availability_stats(self):
        """Generate availability statistics across platforms"""
        platforms = ['amazon', 'blinkit', 'zepto']
        availability = {}
        
        for platform in platforms:
            url_col = f"{platform}_url"
            if url_col in self.data.columns:
                # available = self.data[url_col].notna().sum()
                available = self.data[url_col].astype(str).str.strip().ne('').sum()
                availability[platform] = {
                    'available': available,
                    'not_available': len(self.data) - available,
                    'percentage': (available / len(self.data)) * 100
                }
        
        return availability
    
    def generate_category_analysis(self):
        """Generate analysis by product category"""
        category_analysis = {}
        
        for category in self.data['l1_classification'].unique():
            category_data = self.data[self.data['l1_classification'] == category]
            
            category_analysis[category] = {
                'count': len(category_data),
                'avg_price_diff': {}
            }
            
            # Calculate average price differences by platform
            platforms = ['amazon', 'blinkit', 'zepto']
            for platform in platforms:
                diff_col = f"{platform}_price_diff"
                if diff_col in category_data.columns:
                    avg_diff = category_data[diff_col].mean()
                    category_analysis[category]['avg_price_diff'][platform] = avg_diff
        
        return category_analysis
    
    def plot_price_comparison(self, output_path='price_comparison.png'):
        """Generate price comparison chart"""
        # platforms = ['instamart', 'amazon', 'blinkit', 'zepto']
        platforms = ['amazon', 'blinkit', 'zepto']
        price_data = []
        
        for platform in platforms:
            price_col = f"{platform}_sale_price"
            if platform == 'instamart' or price_col in self.data.columns:
                prices = self.data[price_col].dropna().astype(float).tolist()
                price_data.extend([{'platform': platform, 'price': price} for price in prices])
        
        df = pd.DataFrame(price_data)
        
        plt.figure(figsize=(10, 6))
        sns.boxplot(x='platform', y='price', data=df)
        plt.title('Price Distribution Across Platforms')
        plt.ylabel('Price (INR)')
        plt.xlabel('Platform')
        plt.savefig(output_path)
        
        return output_path