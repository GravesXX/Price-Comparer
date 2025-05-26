# 🇨🇦 Canadian Retail Price Comparison Tool

This Python project allows you to compare the prices of consumer electronics (primarily TVs) across major Canadian retailers like **Amazon.ca**, **BestBuy.ca**, **Costco.ca**, and others.

The project uses **Playwright** for dynamic web scraping and supports a growing number of retailers.

---

## 🛒 Supported Retailers

- Amazon Canada
- Best Buy Canada
- Costco Canada
- Dufresne
- LG Canada
- London Drugs
- Terpermans
- Tanguay
- Staples Canada
- Samsung Canada
- Vision

---

## 📦 Features

- Scrapes live product pricing from Canadian websites
- Compares prices across multiple retailers
- Identifies the **best price** per product
- Outputs results to both terminal and `price_comparison_output.json`

---

## 🔧 Installation

### 1. Clone the Repository

```bash
git https://github.com/GravesXX/Price-Comparer.git
cd price-comparer
```

### 2. Install Python Dependencies
```bash
pip install playwright
playwright install
```

## 🚀 Usage
Run the main script:
```bash
python price_comparison.py
```

It will:

1. Load the product list from testdata.py

2. Scrape price info from all supported retailers

3. Print the lowest price per product

4. Save a full report to price_comparison_output.json

## 🧩 File Structure
├── price_comparison.py        # Main script  <br>
├── testdata.py                # Input product list <br>
├── scrappers/                 # All retailer-specific scrapers <br>
│   ├── amazon.py <br>
│   ├── bestBuy.py<br> 
│   ├── costco.py<br>
│   └── ... <br>
├── utils/                     # Utilities like model number extractor <br>
│   └── extract_model_number.py <br>
├── price_comparison_output.json  # Output file (auto-generated) <br>

## 🛠 Future Improvements
1. Retry failed scrapes
2. Add unit tests

