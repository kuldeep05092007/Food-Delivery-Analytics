"""
clean_data.py
-------------
Cleans the raw synthetic dataset and creates the cleaned CSV used by the dashboard.

Run:  python generate_dataset.py     (only once, creates the raw file)
      python clean_data.py           (creates data/cleaned_food_delivery_orders.csv)

Input : data/food_delivery_orders.csv
Output: data/cleaned_food_delivery_orders.csv

The notebook (notebooks/food_delivery_analysis.ipynb) performs the same steps one
by one with explanations. This script is the "run everything at once" version.
"""

import os
import sys
import numpy as np
import pandas as pd

RAW_FILE = os.path.join("data", "food_delivery_orders.csv")
CLEAN_FILE = os.path.join("data", "cleaned_food_delivery_orders.csv")

# ----------------------------------------------------------------------
# Correct spellings. Keys are lowercase versions of what may appear in the raw file.
# ----------------------------------------------------------------------
CITY_NAMES = ["Delhi", "Mumbai", "Bengaluru", "Hyderabad", "Pune",
              "Chennai", "Kolkata", "Noida", "Gurugram", "Jaipur"]
CITY_FIXES = {"bangalore": "Bengaluru", "gurgaon": "Gurugram"}

CUISINE_NAMES = ["North Indian", "South Indian", "Biryani", "Chinese", "Fast Food",
                 "Pizza", "Street Food", "Desserts", "Healthy", "Mughlai", "Regional"]

RESTAURANT_NAMES = ["Punjabi Tadka", "Dilli Darbar", "Spice Route", "Dosa Corner",
                    "South Spice", "Biryani House", "Hyderabadi Handi", "Dragon Wok",
                    "Noodle Nation", "Burger Barn", "Wrap It Up", "Pizza Junction",
                    "Slice Station", "Chai & Chaat", "Momo Magic", "Sweet Tooth",
                    "Mithai Mahal", "Healthy Bowl", "Fresh Salad Co", "Royal Kebab",
                    "Tandoori Nights", "Bengal Bites", "Rajasthani Rasoi", "Kathi Roll Co."]

PAYMENT_NAMES = ["UPI", "Cash on Delivery", "Credit Card", "Debit Card",
                 "Digital Wallet", "Net Banking"]
PAYMENT_FIXES = {"cod": "Cash on Delivery"}

STATUS_NAMES = ["Delivered", "Cancelled", "Refunded"]
STATUS_FIXES = {"canceled": "Cancelled"}

# Limits used to decide that a value is impossible (a data-entry mistake)
MAX_REALISTIC_ORDER_VALUE = 20000      # rupees
MAX_REALISTIC_DELIVERY_TIME = 180      # minutes


def standardize_text(series, correct_names, extra_fixes=None):
    """Remove extra spaces, ignore upper/lower case and map to the correct spelling."""
    # Step 1: strip spaces at both ends and turn double spaces into single spaces
    cleaned = series.astype("string").str.strip().str.replace(r"\s+", " ", regex=True)
    # Step 2: build a dictionary like {"delhi": "Delhi", "mumbai": "Mumbai", ...}
    lookup = {name.lower(): name for name in correct_names}
    if extra_fixes:
        lookup.update(extra_fixes)
    # Step 3: look up the lowercase text; if not found, keep the cleaned text as it is
    lowered = cleaned.str.lower()
    fixed = lowered.map(lookup)
    return fixed.fillna(cleaned).astype(object)


def get_time_period(hour):
    """Return the part of the day for an hour number (0-23)."""
    if hour < 12:
        return "Morning (10-12)"
    elif hour < 16:
        return "Lunch (12-16)"
    elif hour < 19:
        return "Evening Snacks (16-19)"
    elif hour < 23:
        return "Dinner (19-23)"
    else:
        return "Late Night (23+)"


def clean_orders(raw_df):
    """Clean the raw DataFrame. Returns (cleaned_df, log) where log is a dictionary of counts."""
    df = raw_df.copy()
    log = {"raw_rows": len(df)}

    # ---------------- 1. Standardize text ----------------
    df["City"] = standardize_text(df["City"], CITY_NAMES, CITY_FIXES)
    df["Restaurant_Name"] = standardize_text(df["Restaurant_Name"], RESTAURANT_NAMES)
    df["Cuisine_Type"] = standardize_text(df["Cuisine_Type"], CUISINE_NAMES)
    df["Payment_Method"] = standardize_text(df["Payment_Method"], PAYMENT_NAMES, PAYMENT_FIXES)
    df["Order_Status"] = standardize_text(df["Order_Status"], STATUS_NAMES, STATUS_FIXES)

    # ---------------- 2. Convert data types ----------------
    df["Order_Date"] = pd.to_datetime(df["Order_Date"], errors="coerce")
    numeric_columns = ["Order_Value", "Discount", "Delivery_Fee", "Preparation_Time_Min",
                       "Delivery_Time_Min", "Expected_Delivery_Time_Min", "Customer_Rating"]
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    # ---------------- 3. Remove duplicates (AFTER standardizing text) ----------------
    log["duplicates_removed"] = int(df.duplicated().sum())
    df = df.drop_duplicates().reset_index(drop=True)
    # Safety check: every Order_ID must now appear only once
    log["repeated_order_ids_left"] = int(df["Order_ID"].duplicated().sum())

    # ---------------- 4. Impossible values (data-entry mistakes) ----------------
    # Delivery time above 180 minutes is unrealistic: remove the wrong time, keep the order
    too_long = df["Delivery_Time_Min"] > MAX_REALISTIC_DELIVERY_TIME
    log["impossible_delivery_times_set_to_missing"] = int(too_long.sum())
    df.loc[too_long, "Delivery_Time_Min"] = np.nan

    # Order value above Rs 20,000 for one meal is unrealistic: the money amount cannot be trusted,
    # so these rows are excluded together with rows where Order_Value is missing.
    wrong_value = df["Order_Value"] > MAX_REALISTIC_ORDER_VALUE
    missing_value = df["Order_Value"].isna()
    log["impossible_order_values_excluded"] = int(wrong_value.sum())
    log["missing_order_value_excluded"] = int(missing_value.sum())
    df = df[~(wrong_value | missing_value)].reset_index(drop=True)

    # ---------------- 5. Missing values ----------------
    log["missing_before_filling"] = df.isna().sum()[lambda s: s > 0].to_dict()

    df["City"] = df["City"].fillna("Unknown")
    df["Payment_Method"] = df["Payment_Method"].fillna("Unknown")
    df["Discount"] = df["Discount"].fillna(0)           # no discount recorded = no discount

    # Preparation time: fill with the median of the same restaurant,
    # but NOT for cancelled orders (the kitchen may never have started).
    restaurant_median_prep = df.groupby("Restaurant_Name")["Preparation_Time_Min"].transform("median")
    need_fill = df["Preparation_Time_Min"].isna() & (df["Order_Status"] != "Cancelled")
    df.loc[need_fill, "Preparation_Time_Min"] = restaurant_median_prep[need_fill].round()
    log["prep_time_filled"] = int(need_fill.sum())

    # Delivery_Time_Min and Customer_Rating stay missing on purpose:
    #   cancelled orders were never delivered, and many customers do not rate.

    # ---------------- 6. Date and time features ----------------
    df["Order_Time"] = df["Order_Time"].astype(str).str.strip()
    df["Hour"] = df["Order_Time"].str.slice(0, 2).astype(int)
    df["Order_Month"] = df["Order_Date"].dt.strftime("%Y-%m")
    df["Day_of_Week"] = df["Order_Date"].dt.day_name()
    df["Time_Period"] = df["Hour"].apply(get_time_period)

    # ---------------- 7. Money columns ----------------
    # Net_Order_Value    = Order_Value - Discount              (food bill after discount)
    # Total_Order_Amount = Net_Order_Value + Delivery_Fee      (what the customer is charged)
    df["Net_Order_Value"] = df["Order_Value"] - df["Discount"]
    df["Total_Order_Amount"] = df["Net_Order_Value"] + df["Delivery_Fee"]

    # ---------------- 8. Delivery performance columns ----------------
    # Delivery_Delay_Min = actual time - promised time (positive = late). Only for delivered orders.
    df["Delivery_Delay_Min"] = df["Delivery_Time_Min"] - df["Expected_Delivery_Time_Min"]
    df.loc[df["Order_Status"] != "Delivered", "Delivery_Delay_Min"] = np.nan
    df["Is_Late_Delivery"] = np.where(df["Delivery_Delay_Min"].isna(), np.nan,
                                      (df["Delivery_Delay_Min"] > 0).astype(float))

    # ---------------- 9. Outlier flags using the IQR method (flag only, do not delete) ----------------
    for source, flag in [("Order_Value", "Is_Order_Value_Outlier"),
                         ("Delivery_Time_Min", "Is_Delivery_Time_Outlier")]:
        q1 = df[source].quantile(0.25)
        q3 = df[source].quantile(0.75)
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        df[flag] = ((df[source] < lower) | (df[source] > upper)).astype(int)
        log[flag + "_count"] = int(df[flag].sum())

    # Whole-number columns look nicer without ".0"
    for column in ["Order_Value", "Discount", "Delivery_Fee", "Net_Order_Value",
                   "Total_Order_Amount", "Preparation_Time_Min", "Delivery_Time_Min",
                   "Expected_Delivery_Time_Min", "Delivery_Delay_Min", "Customer_Rating"]:
        df[column] = df[column].round().astype("Int64")

    log["clean_rows"] = len(df)
    return df, log


def main():
    if not os.path.exists(RAW_FILE):
        print(f"ERROR: '{RAW_FILE}' not found. Run 'python generate_dataset.py' first "
              "(and run commands from inside the food_delivery_analytics folder).")
        sys.exit(1)

    raw_df = pd.read_csv(RAW_FILE)
    cleaned_df, log = clean_orders(raw_df)
    cleaned_df.to_csv(CLEAN_FILE, index=False, date_format="%Y-%m-%d")

    print("Cleaning finished.")
    for key, value in log.items():
        print(f"  {key}: {value}")
    print(f"Saved: {CLEAN_FILE}  ({cleaned_df.shape[0]} rows, {cleaned_df.shape[1]} columns)")


if __name__ == "__main__":
    main()
