"""
Generates a realistic synthetic e-commerce dataset and loads it into
retail.db (SQLite), using schema.sql.

Design choices that make the queries in queries.sql actually interesting:
- Customers signup across a 2-year window, so cohort analysis has substance.
- Order volume has monthly seasonality + a growth trend (not flat random).
- ~70% of customers are one-time buyers, ~30% are repeat buyers (power-law-ish),
  so repeat-purchase-rate and RFM queries produce a real spread.
- A small share of orders are cancelled/returned, so filtering on status matters.
"""

import sqlite3
import random
from datetime import date, timedelta

random.seed(42)

DB_PATH = "retail.db"
SCHEMA_PATH = "schema.sql"

CITIES = [
    ("Bhubaneswar", "Odisha"), ("Bengaluru", "Karnataka"), ("Mumbai", "Maharashtra"),
    ("Delhi", "Delhi"), ("Chennai", "Tamil Nadu"), ("Hyderabad", "Telangana"),
    ("Pune", "Maharashtra"), ("Kolkata", "West Bengal"), ("Ahmedabad", "Gujarat"),
    ("Jaipur", "Rajasthan"),
]

FIRST_NAMES = ["Aarav", "Vivaan", "Aditi", "Diya", "Kabir", "Ishaan", "Ananya", "Meera",
               "Rohan", "Sanya", "Arjun", "Priya", "Karan", "Neha", "Aman", "Riya",
               "Yash", "Tanvi", "Dev", "Simran"]
LAST_NAMES = ["Sharma", "Patel", "Nayak", "Reddy", "Iyer", "Gupta", "Das", "Mishra",
              "Rao", "Kulkarni", "Verma", "Nair", "Joshi", "Menon", "Singh"]

PRODUCTS = [
    ("Wireless Earbuds", "Electronics", 1999),
    ("Bluetooth Speaker", "Electronics", 2499),
    ("Smart Watch", "Electronics", 4999),
    ("USB-C Charger 65W", "Electronics", 1299),
    ("Laptop Sleeve 15in", "Accessories", 799),
    ("Mechanical Keyboard", "Electronics", 3499),
    ("Wireless Mouse", "Electronics", 899),
    ("Yoga Mat", "Fitness", 999),
    ("Resistance Bands Set", "Fitness", 599),
    ("Running Shoes", "Fitness", 3299),
    ("Water Bottle 1L", "Fitness", 449),
    ("Cotton T-Shirt", "Apparel", 599),
    ("Denim Jacket", "Apparel", 2199),
    ("Backpack 30L", "Accessories", 1899),
    ("Desk Lamp LED", "Home", 999),
    ("Ceramic Mug Set", "Home", 549),
    ("Notebook Set (3-pack)", "Stationery", 299),
    ("Fountain Pen", "Stationery", 799),
    ("Air Fryer 4L", "Home", 4499),
    ("Non-stick Pan Set", "Home", 1799),
]

N_CUSTOMERS = 400
START_DATE = date(2024, 1, 1)
END_DATE = date(2025, 12, 31)


def random_date(start, end):
    delta_days = (end - start).days
    return start + timedelta(days=random.randint(0, delta_days))


def seasonal_weight(d: date) -> float:
    """Rough seasonality: festive-season bump (Oct-Nov), New Year dip in Feb, mild trend up over time."""
    month_weight = {1: 1.0, 2: 0.75, 3: 0.85, 4: 0.9, 5: 0.95, 6: 0.9,
                    7: 0.95, 8: 1.0, 9: 1.1, 10: 1.4, 11: 1.5, 12: 1.2}[d.month]
    # mild growth trend across the 2-year window
    trend = 1.0 + ((d - START_DATE).days / (END_DATE - START_DATE).days) * 0.5
    return month_weight * trend


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    with open(SCHEMA_PATH) as f:
        cur.executescript(f.read())

    # ---- customers ----
    customers = []
    for cid in range(1, N_CUSTOMERS + 1):
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        city, state = random.choice(CITIES)
        signup = random_date(START_DATE, END_DATE - timedelta(days=30))
        customers.append((cid, name, city, state, signup.isoformat()))
    cur.executemany(
        "INSERT INTO customers VALUES (?, ?, ?, ?, ?)", customers
    )

    # ---- products ----
    products = []
    for pid, (name, cat, price) in enumerate(PRODUCTS, start=1):
        products.append((pid, name, cat, price))
    cur.executemany(
        "INSERT INTO products VALUES (?, ?, ?, ?)", products
    )

    # ---- orders + order_items ----
    # Assign each customer a "purchase frequency class" so the data has a
    # realistic repeat-buyer distribution instead of uniform randomness.
    order_id = 1
    order_item_id = 1
    orders_rows = []
    order_items_rows = []

    for cid, _, _, _, signup in customers:
        signup_date = date.fromisoformat(signup)
        roll = random.random()
        if roll < 0.55:
            n_orders = 1                     # one-time buyers
        elif roll < 0.80:
            n_orders = random.randint(2, 3)   # light repeat
        elif roll < 0.95:
            n_orders = random.randint(4, 7)   # regular repeat
        else:
            n_orders = random.randint(8, 15)  # power buyers

        # weighted candidate dates using seasonality, sampled after signup
        candidate_dates = []
        d = signup_date
        while d <= END_DATE:
            candidate_dates.append(d)
            d += timedelta(days=1)
        if not candidate_dates:
            continue
        weights = [seasonal_weight(d) for d in candidate_dates]

        order_dates = random.choices(candidate_dates, weights=weights, k=n_orders)
        order_dates.sort()

        for od in order_dates:
            status = random.choices(
                ["completed", "cancelled", "returned"], weights=[0.88, 0.06, 0.06]
            )[0]
            orders_rows.append((order_id, cid, od.isoformat(), status))

            n_items = random.randint(1, 4)
            chosen_products = random.sample(PRODUCTS, k=n_items)
            for name, cat, price in chosen_products:
                pid = next(p[0] for p in products if p[1] == name)
                qty = random.randint(1, 3)
                # small price jitter to simulate discounts/price changes over time
                sale_price = round(price * random.uniform(0.85, 1.0), 2)
                order_items_rows.append(
                    (order_item_id, order_id, pid, qty, sale_price)
                )
                order_item_id += 1

            order_id += 1

    cur.executemany(
        "INSERT INTO orders VALUES (?, ?, ?, ?)", orders_rows
    )
    cur.executemany(
        "INSERT INTO order_items VALUES (?, ?, ?, ?, ?)", order_items_rows
    )

    conn.commit()

    # quick sanity summary
    print(f"customers:   {len(customers)}")
    print(f"products:    {len(products)}")
    print(f"orders:      {len(orders_rows)}")
    print(f"order_items: {len(order_items_rows)}")

    conn.close()


if __name__ == "__main__":
    main()
