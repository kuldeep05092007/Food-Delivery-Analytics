"""
app.py  -  Food Delivery & Restaurant Performance Dashboard
-----------------------------------------------------------
Run with:   streamlit run app.py

The dashboard reads data/cleaned_food_delivery_orders.csv (created by clean_data.py).
DATA NOTE: the data is SYNTHETIC (computer-generated), not real company data.

How the page is built (simple version):
  1. Load the cleaned CSV.
  2. Read the filters chosen in the sidebar.
  3. Filter the DataFrame.
  4. Calculate KPIs from the filtered DataFrame.
  5. Draw charts from the filtered DataFrame.
  6. Show the filtered table and a CSV download button.
"""

import os
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

DATA_FILE = os.path.join("data", "cleaned_food_delivery_orders.csv")
DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

REQUIRED_COLUMNS = [
    "Order_ID", "Order_Date", "Order_Time", "Customer_ID", "City", "Restaurant_Name",
    "Cuisine_Type", "Order_Value", "Discount", "Delivery_Fee", "Payment_Method",
    "Order_Status", "Preparation_Time_Min", "Delivery_Time_Min",
    "Expected_Delivery_Time_Min", "Customer_Rating", "Order_Month", "Day_of_Week",
    "Hour", "Net_Order_Value", "Total_Order_Amount", "Delivery_Delay_Min",
    "Is_Late_Delivery",
]

st.set_page_config(page_title="Food Delivery Dashboard", page_icon="🍽️", layout="wide")


# ----------------------------------------------------------------------
# Step 1: Load data (with error handling)
# ----------------------------------------------------------------------
@st.cache_data
def load_data(file_path):
    """Read the cleaned CSV file and return a DataFrame."""
    data = pd.read_csv(file_path, parse_dates=["Order_Date"])
    return data


def load_data_safely():
    """Load the data, or show a friendly message and stop the app if something is wrong."""
    if not os.path.exists(DATA_FILE):
        st.error(f"Data file not found: {DATA_FILE}")
        st.info("Run these commands in the project folder, then refresh this page:\n\n"
                "python generate_dataset.py\n\npython clean_data.py")
        st.stop()
    try:
        data = load_data(DATA_FILE)
    except Exception as error:
        st.error(f"The data file could not be read: {error}")
        st.stop()

    missing_columns = [col for col in REQUIRED_COLUMNS if col not in data.columns]
    if missing_columns:
        st.error(f"The data file is missing these columns: {missing_columns}")
        st.info("Run 'python clean_data.py' again to rebuild the cleaned file.")
        st.stop()
    if data.empty:
        st.error("The data file has no rows.")
        st.stop()
    return data


df = load_data_safely()

# ----------------------------------------------------------------------
# Title
# ----------------------------------------------------------------------
st.title("🍽️ Food Delivery & Restaurant Performance Dashboard")
st.caption("Synthetic dataset created for learning. It is NOT real company data. "
           "Amounts are in Indian rupees (₹).")

# ----------------------------------------------------------------------
# Step 2: Sidebar filters
# ----------------------------------------------------------------------
st.sidebar.header("Filters")

min_date = df["Order_Date"].min().date()
max_date = df["Order_Date"].max().date()
selected_dates = st.sidebar.date_input("Date range", value=(min_date, max_date),
                                       min_value=min_date, max_value=max_date)

city_options = sorted(df["City"].dropna().unique())
cuisine_options = sorted(df["Cuisine_Type"].dropna().unique())
status_options = sorted(df["Order_Status"].dropna().unique())
payment_options = sorted(df["Payment_Method"].dropna().unique())

selected_cities = st.sidebar.multiselect("City", city_options, default=city_options)
selected_cuisines = st.sidebar.multiselect("Cuisine", cuisine_options, default=cuisine_options)
selected_statuses = st.sidebar.multiselect("Order status", status_options, default=status_options)
selected_payments = st.sidebar.multiselect("Payment method", payment_options, default=payment_options)

# The date picker returns 2 dates when finished, but only 1 date while the user is still choosing
if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
    start_date, end_date = selected_dates
else:
    st.sidebar.warning("Please pick both a start date and an end date. Showing all dates for now.")
    start_date, end_date = min_date, max_date

# ----------------------------------------------------------------------
# Step 3: Apply the filters
# ----------------------------------------------------------------------
filtered = df[
    (df["Order_Date"] >= pd.Timestamp(start_date))
    & (df["Order_Date"] <= pd.Timestamp(end_date))
    & (df["City"].isin(selected_cities))
    & (df["Cuisine_Type"].isin(selected_cuisines))
    & (df["Order_Status"].isin(selected_statuses))
    & (df["Payment_Method"].isin(selected_payments))
].copy()

st.sidebar.markdown("---")
st.sidebar.write(f"**{len(filtered):,}** of {len(df):,} orders match the filters.")

# Empty result: show a message and stop (so nothing crashes below)
if filtered.empty:
    st.warning("No orders match the selected filters. Please widen your filters "
               "(for example select more cities or a longer date range).")
    st.stop()

# ----------------------------------------------------------------------
# Step 4: KPI calculations
# ----------------------------------------------------------------------
# Money and delivery-time KPIs use DELIVERED orders only. Cancelled and refunded
# orders did not become completed sales, so they are not counted as value.
delivered = filtered[filtered["Order_Status"] == "Delivered"]
delivered_with_time = delivered.dropna(subset=["Delivery_Time_Min"])

total_orders = len(filtered)
delivered_orders = len(delivered)
completion_rate = delivered_orders / total_orders * 100

if delivered_orders > 0:
    avg_order_value_text = f"₹{delivered['Order_Value'].mean():,.0f}"
else:
    avg_order_value_text = "N/A"

if len(delivered_with_time) > 0:
    avg_delivery_text = f"{delivered_with_time['Delivery_Time_Min'].mean():.1f} min"
    late_rate_text = f"{delivered_with_time['Is_Late_Delivery'].mean() * 100:.1f}%"
else:
    avg_delivery_text = "N/A"
    late_rate_text = "N/A"

col1, col2, col3 = st.columns(3)
col1.metric("Total Orders", f"{total_orders:,}")
col2.metric("Delivered Orders", f"{delivered_orders:,}")
col3.metric("Completion Rate", f"{completion_rate:.1f}%")

col4, col5, col6 = st.columns(3)
col4.metric("Average Order Value", avg_order_value_text, help="Average food value (before discount) of delivered orders")
col5.metric("Average Delivery Time", avg_delivery_text, help="Order placed to delivery, delivered orders only")
col6.metric("Late Delivery Rate", late_rate_text, help="Share of delivered orders that took longer than the promised time")


# ----------------------------------------------------------------------
# Step 5: Charts
# ----------------------------------------------------------------------
def show_chart(figure):
    """Draw a Plotly chart with a clean look."""
    figure.update_layout(template="plotly_white", margin=dict(l=10, r=10, t=50, b=10),
                         title_font_size=16)
    st.plotly_chart(figure, width="stretch")


# Chart 1 and 2
left, right = st.columns(2)

with left:
    monthly = filtered.groupby("Order_Month").size().reset_index(name="Orders")
    fig = px.line(monthly, x="Order_Month", y="Orders", markers=True,
                  title="1. Monthly Order Trend")
    fig.update_xaxes(title="Month")
    show_chart(fig)

with right:
    by_city = filtered.groupby("City").size().reset_index(name="Orders").sort_values("Orders", ascending=False)
    fig = px.bar(by_city, x="City", y="Orders", text="Orders", title="2. Orders by City")
    show_chart(fig)

# Chart 3 and 4
left, right = st.columns(2)

with left:
    by_cuisine = filtered.groupby("Cuisine_Type").size().reset_index(name="Orders").sort_values("Orders", ascending=False)
    fig = px.bar(by_cuisine, x="Cuisine_Type", y="Orders", text="Orders", title="3. Cuisine Popularity")
    fig.update_xaxes(title="Cuisine")
    show_chart(fig)

with right:
    by_status = filtered["Order_Status"].value_counts().reset_index()
    by_status.columns = ["Order_Status", "Orders"]
    fig = px.pie(by_status, names="Order_Status", values="Orders", hole=0.45,
                 title="4. Order Status Distribution")
    show_chart(fig)

# Chart 5 and 6
left, right = st.columns(2)

with left:
    if delivered_orders > 0:
        top_restaurants = (delivered.groupby("Restaurant_Name").size()
                           .reset_index(name="Delivered_Orders")
                           .sort_values("Delivered_Orders", ascending=False).head(10)
                           .sort_values("Delivered_Orders"))      # smallest first so biggest is on top
        fig = px.bar(top_restaurants, x="Delivered_Orders", y="Restaurant_Name", orientation="h",
                     text="Delivered_Orders", title="5. Top 10 Restaurants (Delivered Orders)")
        fig.update_yaxes(title="")
        show_chart(fig)
    else:
        st.info("5. Restaurant performance: no delivered orders in the current selection.")

with right:
    if len(delivered_with_time) > 0:
        compare = (delivered_with_time.groupby("City")[["Delivery_Time_Min", "Expected_Delivery_Time_Min"]]
                   .mean().round(1).reset_index())
        compare = compare.melt(id_vars="City", var_name="Measure", value_name="Minutes")
        compare["Measure"] = compare["Measure"].replace({"Delivery_Time_Min": "Actual delivery time",
                                                         "Expected_Delivery_Time_Min": "Expected delivery time"})
        fig = px.bar(compare, x="City", y="Minutes", color="Measure", barmode="group",
                     title="6. Actual vs Expected Delivery Time (by City)")
        show_chart(fig)
    else:
        st.info("6. Delivery time comparison: no delivery-time data in the current selection.")

# Chart 7 and 8
left, right = st.columns(2)

with left:
    by_hour = filtered.groupby("Hour").size().reindex(range(10, 24), fill_value=0).reset_index()
    by_hour.columns = ["Hour", "Orders"]
    fig = px.bar(by_hour, x="Hour", y="Orders", title="7. Orders by Hour of the Day")
    fig.update_xaxes(dtick=1, title="Hour (24-hour clock)")
    show_chart(fig)

with right:
    rated = filtered.dropna(subset=["Customer_Rating"])
    if len(rated) > 0:
        rating_counts = rated["Customer_Rating"].astype(int).value_counts().reindex([1, 2, 3, 4, 5], fill_value=0)
        rating_counts = rating_counts.reset_index()
        rating_counts.columns = ["Rating", "Orders"]
        fig = px.bar(rating_counts, x="Rating", y="Orders", text="Orders",
                     title="8. Customer Ratings Distribution")
        fig.update_xaxes(dtick=1)
        show_chart(fig)
    else:
        st.info("8. Ratings: no customer ratings in the current selection.")

# ----------------------------------------------------------------------
# More insights (extra analysis, hidden until opened)
# ----------------------------------------------------------------------
with st.expander("More insights: days, payment methods and discounts"):
    left, right = st.columns(2)

    with left:
        by_day = filtered.groupby("Day_of_Week").size().reindex(DAY_ORDER, fill_value=0).reset_index()
        by_day.columns = ["Day_of_Week", "Orders"]
        fig = px.bar(by_day, x="Day_of_Week", y="Orders", title="Orders by Day of the Week")
        fig.update_xaxes(title="")
        show_chart(fig)

    with right:
        by_payment = filtered["Payment_Method"].value_counts().reset_index()
        by_payment.columns = ["Payment_Method", "Orders"]
        fig = px.bar(by_payment, x="Payment_Method", y="Orders", title="Payment Method Usage")
        show_chart(fig)

    if delivered_orders > 0:
        discount_view = delivered.copy()
        discount_view["Discount_Used"] = np.where(discount_view["Discount"] > 0, "With discount", "No discount")
        discount_summary = discount_view.groupby("Discount_Used").agg(
            Orders=("Order_ID", "count"),
            Avg_Order_Value=("Order_Value", "mean"),
            Avg_Discount=("Discount", "mean"),
        ).round(1).reset_index()
        st.write("**Discount vs order value (delivered orders)**")
        st.dataframe(discount_summary, hide_index=True, width="stretch")
        st.caption("This shows a relationship, not a cause. The discount amount is calculated from the "
                   "order value, so a difference between the two groups does not prove that "
                   "discounts make customers order more.")

# ----------------------------------------------------------------------
# Step 6: Order table and CSV download
# ----------------------------------------------------------------------
st.subheader("Order Details")
search_text = st.text_input("Search the table by Order ID or restaurant name (optional)")

table_data = filtered.copy()
if search_text.strip():
    text = search_text.strip().lower()
    match = (table_data["Order_ID"].str.lower().str.contains(text, regex=False)
             | table_data["Restaurant_Name"].str.lower().str.contains(text, regex=False))
    table_data = table_data[match]

table_data["Order_Date"] = table_data["Order_Date"].dt.strftime("%Y-%m-%d")
table_columns = ["Order_ID", "Order_Date", "Order_Time", "City", "Restaurant_Name", "Cuisine_Type",
                 "Order_Value", "Discount", "Delivery_Fee", "Total_Order_Amount", "Payment_Method",
                 "Order_Status", "Delivery_Time_Min", "Expected_Delivery_Time_Min",
                 "Delivery_Delay_Min", "Customer_Rating"]

if table_data.empty:
    st.info("No orders match your search text.")
else:
    st.caption(f"Showing {len(table_data):,} orders. Click a column heading to sort.")
    st.dataframe(table_data[table_columns], hide_index=True, width="stretch")
    csv_bytes = table_data[table_columns].to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download filtered data as CSV", data=csv_bytes,
                       file_name="filtered_food_delivery_orders.csv", mime="text/csv")

st.caption("Definitions: Net Order Value = Order Value - Discount. "
           "Total Order Amount = Net Order Value + Delivery Fee. "
           "Order Value is the customer's food bill, not the company's revenue.")
