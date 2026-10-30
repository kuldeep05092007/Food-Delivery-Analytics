"""
generate_dataset.py
-------------------
Creates the SYNTHETIC (fake, computer-generated) food delivery dataset.

IMPORTANT: This is NOT real company data. Restaurant names are made up and
every number is generated randomly using rules that look realistic.

Run:  python generate_dataset.py
Output: data/food_delivery_orders.csv  (exactly 1,500 rows, intentionally messy)

The file is "messy on purpose" so students can practise data cleaning:
  - 30 duplicate rows
  - missing values in several columns
  - inconsistent text (delhi / DELHI / " Delhi ", Bangalore / Bengaluru ...)
  - outliers (very large order values and very long delivery times)
"""

import os
import numpy as np
import pandas as pd

# A fixed seed means you get the SAME dataset every time you run this file.
rng = np.random.default_rng(seed=42)

TOTAL_ROWS = 1500          # final number of rows in the raw CSV
DUPLICATE_ROWS = 30        # exact copies of some rows (added at the end)
UNIQUE_ROWS = TOTAL_ROWS - DUPLICATE_ROWS

# ----------------------------------------------------------------------
# 1. Lookup lists (all names are fictional)
# ----------------------------------------------------------------------
cities = ["Delhi", "Mumbai", "Bengaluru", "Hyderabad", "Pune",
          "Chennai", "Kolkata", "Noida", "Gurugram", "Jaipur"]
city_weights = [0.16, 0.15, 0.15, 0.10, 0.09, 0.08, 0.07, 0.08, 0.07, 0.05]

# Extra delivery minutes caused by traffic in some cities
city_traffic_delay = {"Delhi": 3, "Mumbai": 5, "Bengaluru": 6, "Hyderabad": 2,
                      "Pune": 2, "Chennai": 2, "Kolkata": 3, "Noida": 1,
                      "Gurugram": 4, "Jaipur": 0}

# restaurant: (cuisine, typical price per order in rupees, typical prep minutes, quality score)
restaurants = {
    "Punjabi Tadka":        ("North Indian", 420, 22, 0.80),
    "Dilli Darbar":         ("North Indian", 480, 24, 0.70),
    "Spice Route":          ("North Indian", 390, 20, 0.55),
    "Dosa Corner":          ("South Indian", 260, 15, 0.85),
    "South Spice":          ("South Indian", 300, 17, 0.65),
    "Biryani House":        ("Biryani",      450, 26, 0.85),
    "Hyderabadi Handi":     ("Biryani",      520, 28, 0.75),
    "Dragon Wok":           ("Chinese",      380, 21, 0.60),
    "Noodle Nation":        ("Chinese",      340, 18, 0.50),
    "Burger Barn":          ("Fast Food",    290, 14, 0.60),
    "Wrap It Up":           ("Fast Food",    240, 12, 0.55),
    "Pizza Junction":       ("Pizza",        550, 20, 0.70),
    "Slice Station":        ("Pizza",        480, 19, 0.50),
    "Chai & Chaat":         ("Street Food",  180, 10, 0.80),
    "Momo Magic":           ("Street Food",  210, 13, 0.75),
    "Sweet Tooth":          ("Desserts",     320, 12, 0.80),
    "Mithai Mahal":         ("Desserts",     400, 10, 0.65),
    "Healthy Bowl":         ("Healthy",      430, 16, 0.70),
    "Fresh Salad Co":       ("Healthy",      360, 12, 0.60),
    "Royal Kebab":          ("Mughlai",      560, 27, 0.75),
    "Tandoori Nights":      ("Mughlai",      520, 25, 0.60),
    "Bengal Bites":         ("Regional",     350, 20, 0.70),
    "Rajasthani Rasoi":     ("Regional",     470, 23, 0.65),
    "Kathi Roll Co.":       ("Street Food",  230, 13, 0.60),
}
restaurant_names = list(restaurants.keys())
# Some restaurants are more popular than others
popularity = rng.uniform(0.5, 1.5, size=len(restaurant_names))
restaurant_weights = popularity / popularity.sum()

payment_methods = ["UPI", "Cash on Delivery", "Credit Card", "Debit Card",
                   "Digital Wallet", "Net Banking"]
payment_weights = [0.45, 0.18, 0.12, 0.10, 0.11, 0.04]

# ----------------------------------------------------------------------
# 2. Order dates and times (about six months: 1 Apr 2026 to 30 Sep 2026)
# ----------------------------------------------------------------------
all_days = pd.date_range("2026-04-01", "2026-09-30", freq="D")

# Weekends get more orders; later months get slightly more orders (growth)
day_weights = []
for i, day in enumerate(all_days):
    weight = 1.0 + 0.4 * (day.dayofweek >= 5)     # Sat/Sun boost
    weight = weight * (1 + 0.003 * i)              # slow growth over time
    day_weights.append(weight)
day_weights = np.array(day_weights) / np.sum(day_weights)

order_days = rng.choice(all_days, size=UNIQUE_ROWS, p=day_weights)

# Hour of the day: lunch (12-14) and dinner (19-22) are busiest
hours = np.arange(10, 24)
hour_weights = np.array([2, 4, 9, 10, 6, 3, 3, 4, 6, 10, 12, 10, 6, 3], dtype=float)
hour_weights = hour_weights / hour_weights.sum()
order_hours = rng.choice(hours, size=UNIQUE_ROWS, p=hour_weights)
order_minutes = rng.integers(0, 60, size=UNIQUE_ROWS)

# ----------------------------------------------------------------------
# 3. Build each order
# ----------------------------------------------------------------------
rows = []
customer_pool = [f"CUST{n}" for n in range(1001, 1701)]   # 700 customers

for i in range(UNIQUE_ROWS):
    order_id = f"FD{100001 + i}"
    city = rng.choice(cities, p=city_weights)
    name = rng.choice(restaurant_names, p=restaurant_weights)
    cuisine, base_price, base_prep, quality = restaurants[name]
    payment = rng.choice(payment_methods, p=payment_weights)
    customer = rng.choice(customer_pool)
    hour = order_hours[i]
    is_peak = hour in (13, 14, 20, 21, 22)
    is_weekend = pd.Timestamp(order_days[i]).dayofweek >= 5

    # Order value (food price in rupees, before discount) - skewed to the right
    value = base_price * rng.lognormal(mean=0.0, sigma=0.35)
    value = int(round(max(80, min(value, 2500)) / 5) * 5)

    # Discount: about 40% of orders use a coupon (10-30% of value, capped at Rs 150)
    discount = 0
    if rng.random() < 0.40:
        discount = int(round(min(value * rng.uniform(0.10, 0.30), 150)))

    # Delivery fee: free for big orders, otherwise Rs 25 - 49
    if value >= 600:
        fee = 0
    else:
        fee = int(rng.choice([0, 25, 35, 49], p=[0.15, 0.30, 0.30, 0.25]))

    # Order status
    status_roll = rng.random()
    if status_roll < 0.865:
        status = "Delivered"
    elif status_roll < 0.945:
        status = "Cancelled"
    else:
        status = "Refunded"

    # Preparation and delivery time (minutes)
    prep = int(round(base_prep + rng.normal(0, 3) + (4 if is_peak else 0)))
    prep = max(5, prep)
    travel = rng.gamma(shape=4.0, scale=4.5)                # about 18 min on average
    traffic = city_traffic_delay[city] + (4 if is_peak else 0) + (2 if is_weekend else 0)
    delivery = int(round(prep + travel + traffic))

    # Expected delivery time promised to the customer (in steps of 5 minutes)
    expected = 5 * int(round((base_prep + 20 + city_traffic_delay[city] + 10) / 5))

    delay = delivery - expected

    # Customer rating (1-5): good quality + on time = higher rating
    rating_score = 1.5 + 3.0 * quality + rng.normal(0, 0.6) - 0.05 * max(delay, 0)
    rating = int(np.clip(round(rating_score), 1, 5))

    # Cancelled orders never reach the customer: no delivery time and no rating
    if status == "Cancelled":
        delivery = np.nan
        rating = np.nan
        prep = prep if rng.random() < 0.5 else np.nan   # kitchen may not have started
    elif status == "Refunded":
        rating = int(rng.choice([1, 2, 3], p=[0.5, 0.35, 0.15]))

    rows.append({
        "Order_ID": order_id,
        "Order_Date": pd.Timestamp(order_days[i]).strftime("%Y-%m-%d"),
        "Order_Time": f"{hour:02d}:{order_minutes[i]:02d}",
        "Customer_ID": customer,
        "City": city,
        "Restaurant_Name": name,
        "Cuisine_Type": cuisine,
        "Order_Value": value,
        "Discount": discount,
        "Delivery_Fee": fee,
        "Payment_Method": payment,
        "Order_Status": status,
        "Preparation_Time_Min": prep,
        "Delivery_Time_Min": delivery,
        "Expected_Delivery_Time_Min": expected,
        "Customer_Rating": rating,
    })

df = pd.DataFrame(rows)

# Not every customer leaves a rating: remove about 30% of ratings of delivered orders
delivered_index = df[df["Order_Status"] == "Delivered"].index
no_rating = rng.choice(delivered_index, size=int(0.30 * len(delivered_index)), replace=False)
df.loc[no_rating, "Customer_Rating"] = np.nan

# ----------------------------------------------------------------------
# 4. Add "dirty data" on purpose (for cleaning practice)
# ----------------------------------------------------------------------
def pick(n):
    """Pick n random row positions."""
    return rng.choice(df.index, size=n, replace=False)

# (a) Missing values
df.loc[pick(14), "City"] = np.nan
df.loc[pick(18), "Payment_Method"] = np.nan
df.loc[pick(22), "Preparation_Time_Min"] = np.nan
df.loc[pick(16), "Delivery_Time_Min"] = np.nan       # some delivered orders lost this value
df.loc[pick(12), "Discount"] = np.nan
df.loc[pick(8), "Order_Value"] = np.nan

# (b) Inconsistent text formatting
def mess_up_text(column, replacements, how_many):
    """Randomly change the text style of some rows in a column."""
    for position in pick(how_many):
        original = df.at[position, column]
        if isinstance(original, str):
            if original in replacements and rng.random() < 0.5:
                df.at[position, column] = replacements[original]
            else:
                style = rng.integers(0, 4)
                if style == 0:
                    df.at[position, column] = original.lower()
                elif style == 1:
                    df.at[position, column] = original.upper()
                elif style == 2:
                    df.at[position, column] = "  " + original + " "
                else:
                    df.at[position, column] = original.replace(" ", "  ")

mess_up_text("City", {"Bengaluru": "Bangalore", "Gurugram": "Gurgaon"}, 120)
mess_up_text("Restaurant_Name", {}, 90)
mess_up_text("Cuisine_Type", {}, 90)
mess_up_text("Payment_Method", {"Cash on Delivery": "COD", "UPI": "Upi"}, 110)
mess_up_text("Order_Status", {"Cancelled": "Canceled"}, 70)

# (c) Outliers
# Valid but unusual: big party orders (these are REAL behaviour, keep them)
party_rows = pick(6)
for position in party_rows:
    df.at[position, "Order_Value"] = int(rng.integers(3500, 6000))
# Data-entry mistakes (impossible values, should be corrected / excluded)
bad_value_rows = pick(3)
for position, wrong_value in zip(bad_value_rows, [45000, 99999, 25000]):
    df.at[position, "Order_Value"] = wrong_value
bad_time_rows = df[df["Delivery_Time_Min"].notna()].sample(4, random_state=7).index
for position, wrong_time in zip(bad_time_rows, [310, 480, 245, 520]):
    df.at[position, "Delivery_Time_Min"] = wrong_time
# Valid but slow deliveries (heavy rain, traffic jam): keep
slow_rows = df[df["Delivery_Time_Min"].notna() & (df["Delivery_Time_Min"] < 100)].sample(6, random_state=11).index
for position in slow_rows:
    df.at[position, "Delivery_Time_Min"] = int(rng.integers(95, 130))

# (d) Duplicate records: copy 30 rows. Some copies get different text style so that
#     students learn "standardize text FIRST, then remove duplicates".
duplicates = df.sample(DUPLICATE_ROWS, random_state=5).copy()
for position in duplicates.index[:10]:
    if isinstance(duplicates.at[position, "City"], str):          # skip missing cities
        duplicates.at[position, "City"] = duplicates.at[position, "City"].lower()
    if isinstance(duplicates.at[position, "Restaurant_Name"], str):
        duplicates.at[position, "Restaurant_Name"] = duplicates.at[position, "Restaurant_Name"].upper()
df = pd.concat([df, duplicates], ignore_index=True)

# Shuffle rows so duplicates are not all at the bottom
df = df.sample(frac=1, random_state=3).reset_index(drop=True)

# Whole numbers should look like whole numbers in the CSV
for column in ["Order_Value", "Discount", "Delivery_Fee", "Preparation_Time_Min",
               "Delivery_Time_Min", "Expected_Delivery_Time_Min", "Customer_Rating"]:
    df[column] = df[column].astype("Int64")

# ----------------------------------------------------------------------
# 5. Save
# ----------------------------------------------------------------------
os.makedirs("data", exist_ok=True)
df.to_csv("data/food_delivery_orders.csv", index=False)

print("Synthetic dataset created: data/food_delivery_orders.csv")
print("Rows:", len(df), "| Columns:", len(df.columns))
assert len(df) == TOTAL_ROWS, "Row count must be exactly 1500"
