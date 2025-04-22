import streamlit as st
import pandas as pd
import io
import base64
from src.MAIN2 import ProductMatcher
from src.analyzer import ProductAnalyzer
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(page_title="Product Matcher", layout="wide")

def get_download_link(df, filename, text):
    """Generate a download link for a DataFrame"""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{text}</a>'
    return href

def main():
    st.title("E-commerce Product Matcher & Analyzer")
    
    st.write("""
    ## Upload Swiggy Instamart SKUs
    Upload a CSV containing Swiggy Instamart SKUs to find matching products on Amazon, Blinkit, and Zepto.
    """)
    
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
    
    if uploaded_file is not None:
        # Display uploaded data
        df = pd.read_csv(uploaded_file)
        st.write("### Uploaded Data Preview")
        st.dataframe(df.head())
        
        if st.button("Process SKUs"):
            # Show progress
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.text("Processing SKUs... This may take several minutes.")
            
            # Save temp file for processing
            temp_file = "temp_input.csv"
            df.to_csv(temp_file, index=False)
            
            # Process SKUs
            matcher = ProductMatcher()
            result_df = matcher.process_skus(temp_file)
            
            # Display results
            st.write("### Results")
            st.dataframe(result_df)
            
            # Analysis section
            st.write("## Data Analysis")
            
            analyzer = ProductAnalyzer(result_df)
            
            # Calculate price differences
            # analysis_df = analyzer.calculate_price_differences()
            
            # Platform availability
            st.write("### Product Availability Across Platforms")
            availability = analyzer.generate_availability_stats()
            
            # Create availability chart
            platforms = list(availability.keys())
            available = [availability[p]['available'] for p in platforms]
            not_available = [availability[p]['not_available'] for p in platforms]
            
            fig, ax = plt.subplots(figsize=(10, 6))
            
            x = range(len(platforms))
            width = 0.35
            
            ax.bar([i - width/2 for i in x], available, width, label='Available')
            ax.bar([i + width/2 for i in x], not_available, width, label='Not Available')
            
            ax.set_ylabel('Number of Products')
            ax.set_title('Product Availability Across Platforms')
            ax.set_xticks(x)
            ax.set_xticklabels(platforms)
            ax.legend()
            
            st.pyplot(fig)
            
            # Best deals
            st.write("### Best Deals (Largest Price Differences)")
            best_deals = analyzer.find_best_deals()
            st.dataframe(best_deals)
            
            # Price comparison
            st.write("### Price Distribution Comparison")
            price_chart = analyzer.plot_price_comparison()
            st.image(price_chart)
            
            # Category analysis
            st.write("### Category Analysis")
            category_analysis = analyzer.generate_category_analysis()
            
            for category, data in category_analysis.items():
                st.write(f"**{category}** (Products: {data['count']})")
                
                avg_diffs = data['avg_price_diff']
                if avg_diffs:
                    st.write("Average price differences:")
                    for platform, diff in avg_diffs.items():
                        if diff is not None:
                            st.write(f"- {platform.capitalize()}: ₹{diff:.2f}")
            
            # Download links
            st.markdown("### Download Results")
            st.markdown(get_download_link(result_df, "product_matches.csv", "Download Matching Results (CSV)"), unsafe_allow_html=True)
            # st.markdown(get_download_link(analysis_df, "price_analysis.csv", "Download Price Analysis (CSV)"), unsafe_allow_html=True)
            
            status_text.text("Processing complete!")
            progress_bar.progress(100)

if __name__ == "__main__":
    main()