import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

def generate_sample_sales_data():
    """Generate sample sales data for testing"""
    
    # Sample products
    products = [
        {'sku': 'WH001', 'msku': 'WIRELESS_HEADPHONES', 'name': 'Wireless Headphones', 'category': 'Electronics', 'price': 29.99},
        {'sku': 'CM002', 'msku': 'COFFEE_MUG', 'name': 'Coffee Mug', 'category': 'Home & Kitchen', 'price': 12.99},
        {'sku': 'DL003', 'msku': 'DESK_LAMP', 'name': 'LED Desk Lamp', 'category': 'Office', 'price': 45.99},
        {'sku': 'BJ004', 'msku': 'BLUE_JEANS', 'name': 'Blue Jeans', 'category': 'Clothing', 'price': 39.99},
        {'sku': 'SR005', 'msku': 'SILVER_RING', 'name': 'Silver Ring', 'category': 'Jewelry', 'price': 89.99},
    ]
    
    marketplaces = ['Amazon', 'eBay', 'Shopify', 'Etsy', 'Walmart']
    
    sales_data = []
    for i in range(100):
        product = random.choice(products)
        marketplace = random.choice(marketplaces)
        quantity = random.randint(1, 5)
        
        date = datetime.now() - timedelta(days=random.randint(0, 30))
        
        order = {
            'order_id': f'ORD{i+1:04d}',
            'sku': product['sku'],
            'msku': product['msku'],
            'product_name': product['name'],
            'quantity': quantity,
            'price': product['price'],
            'total': product['price'] * quantity,
            'date': date.strftime('%Y-%m-%d'),
            'marketplace': marketplace,
            'category': product['category'],
            'status': random.choice(['completed', 'pending', 'shipped'])
        }
        sales_data.append(order)
    
    df = pd.DataFrame(sales_data)
    df.to_csv('data/sample_data/sample_sales.csv', index=False)
    print("Sample sales data generated!")
    
    return df

def generate_sample_mappings():
    """Generate sample SKU mappings"""
    mappings = {
        "WIRELESS_HEADPHONES": ["WH001", "HEADPHONE_BT", "WH_BLUETOOTH"],
        "COFFEE_MUG": ["CM002", "MUG_CERAMIC", "COFFEE_CUP"],
        "DESK_LAMP": ["DL003", "LAMP_LED", "DESK_LIGHT"],
        "BLUE_JEANS": ["BJ004", "JEANS_BLUE", "DENIM_BLUE"],
        "SILVER_RING": ["SR005", "RING_SILVER", "AG_RING"]
    }
    
    import json
    with open('data/sample_data/sample_mappings.json', 'w') as f:
        json.dump(mappings, f, indent=2)
    
    print("Sample mappings generated!")
    return mappings

if __name__ == "__main__":
    generate_sample_sales_data()
    generate_sample_mappings()