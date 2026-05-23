"""Run once to generate sample_data/ecommerce_sales.csv (650 rows)."""
import os
import random
from datetime import date, timedelta

import pandas as pd

random.seed(42)

CATEGORIES = ["Electronics", "Clothing", "Home & Garden", "Sports", "Books", "Beauty", "Toys"]
REGIONS = ["North", "South", "East", "West", "Central"]
PRODUCTS = {
    "Electronics": ["Laptop Pro", "Wireless Earbuds", "Smart Watch", "Tablet 10", "USB Hub", "Webcam HD"],
    "Clothing": ["Running Shoes", "Winter Jacket", "Casual T-Shirt", "Jeans Classic", "Dress Formal", "Sneakers"],
    "Home & Garden": ["Coffee Maker", "Air Purifier", "Garden Hose", "Throw Pillow", "LED Lamp", "Storage Bin"],
    "Sports": ["Yoga Mat", "Dumbbell Set", "Resistance Bands", "Water Bottle", "Cycling Helmet", "Jump Rope"],
    "Books": ["Python Deep Dive", "Data Science 101", "Fiction Bestseller", "History Atlas", "Cook Book", "Self Help"],
    "Beauty": ["Moisturizer SPF", "Hair Serum", "Lip Palette", "Face Wash", "Perfume Set", "Nail Kit"],
    "Toys": ["LEGO Set", "Board Game", "Action Figure", "Stuffed Bear", "Puzzle 1000", "Remote Car"],
}
UNIT_PRICES = {
    "Laptop Pro": 999.99, "Wireless Earbuds": 79.99, "Smart Watch": 249.99, "Tablet 10": 449.99,
    "USB Hub": 29.99, "Webcam HD": 59.99, "Running Shoes": 89.99, "Winter Jacket": 129.99,
    "Casual T-Shirt": 19.99, "Jeans Classic": 49.99, "Dress Formal": 79.99, "Sneakers": 69.99,
    "Coffee Maker": 49.99, "Air Purifier": 119.99, "Garden Hose": 34.99, "Throw Pillow": 24.99,
    "LED Lamp": 39.99, "Storage Bin": 14.99, "Yoga Mat": 29.99, "Dumbbell Set": 59.99,
    "Resistance Bands": 19.99, "Water Bottle": 24.99, "Cycling Helmet": 69.99, "Jump Rope": 12.99,
    "Python Deep Dive": 39.99, "Data Science 101": 34.99, "Fiction Bestseller": 14.99,
    "History Atlas": 29.99, "Cook Book": 24.99, "Self Help": 19.99, "Moisturizer SPF": 29.99,
    "Hair Serum": 24.99, "Lip Palette": 19.99, "Face Wash": 14.99, "Perfume Set": 59.99,
    "Nail Kit": 12.99, "LEGO Set": 49.99, "Board Game": 34.99, "Action Figure": 19.99,
    "Stuffed Bear": 14.99, "Puzzle 1000": 24.99, "Remote Car": 39.99,
}

rows = []
start_date = date(2023, 1, 1)
end_date = date(2024, 12, 31)
delta = end_date - start_date

for i in range(650):
    order_date = start_date + timedelta(days=random.randint(0, delta.days))
    category = random.choice(CATEGORIES)
    product = random.choice(PRODUCTS[category])
    quantity = random.randint(1, 10)
    unit_price = UNIT_PRICES[product]
    discount_pct = random.choice([0, 0, 0, 5, 10, 15, 20, 25])
    revenue = round(quantity * unit_price * (1 - discount_pct / 100), 2)
    region = random.choice(REGIONS)
    customer_id = f"CUST{random.randint(1000, 9999)}"

    rows.append({
        "order_id": f"ORD{10000 + i}",
        "date": order_date.isoformat(),
        "product_name": product,
        "category": category,
        "region": region,
        "quantity": quantity,
        "unit_price": unit_price,
        "discount_pct": discount_pct,
        "revenue": revenue,
        "customer_id": customer_id,
    })

df = pd.DataFrame(rows)
os.makedirs("sample_data", exist_ok=True)
df.to_csv("sample_data/ecommerce_sales.csv", index=False)
print(f"Generated {len(df)} rows → sample_data/ecommerce_sales.csv")
