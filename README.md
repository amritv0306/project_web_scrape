# E-commerce Product Matcher & Analyzer

This tool matches products from Swiggy Instamart with corresponding products on Amazon, Blinkit, and Zepto, and provides competitive analysis.

## Features

- Product matching across multiple e-commerce platforms
- Extracts product details including MRP, Sale Price, Quantity, and UOM
- Handles website restrictions and dynamic content
- Comprehensive data analysis with visualizations
- User-friendly web interface

## Live Demo

[Click here to access the deployed application](https://your-deployed-app-url.com)

## Setup Instructions

### Prerequisites

- Python 3.8+
- pip or poetry

### Installation

1. Clone the repository:
2. Install dependencies:
3. Run the application:
4. Open your browser and go to `http://localhost:8501`

## Usage

1. Upload a CSV file containing Swiggy Instamart SKUs
2. Click "Process SKUs" to start the matching process
3. View the results and analysis
4. Download the results as CSV

## Input Format

The input CSV should contain the following columns:
- SPIN ID: Unique identifier for Swiggy Instamart products
- Item Name: Product name
- L1 Classification: Product category
- UOM: Unit of measurement
- Instamart URL: Product URL on Swiggy Instamart

## Architecture

The solution consists of:
- Web scrapers for Amazon, Blinkit, and Zepto
- Data processing pipeline
- Analysis engine
- Streamlit web interface

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -m 'Add some feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request