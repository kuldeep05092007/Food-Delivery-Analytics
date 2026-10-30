# Project Report: Food Delivery & Restaurant Performance

> All data is **synthetic**. Findings below describe this generated dataset and demonstrate analysis method. They are not facts about any real company.

## 1. Business problem

A food delivery platform wants to know how its restaurants, cities and delivery operations are performing. The manager asks: which restaurants and cuisines are strongest, where do orders come from, how fast are deliveries, how many orders fail, and when is demand highest?

## 2. Dataset

* 1,500 orders (1 April to 30 September 2026), 16 columns, 24 fictional restaurants, 11 cuisines, 10 Indian cities.
* Raw file `food_delivery_orders.csv` is **messy on purpose**: 30 duplicates, missing values, inconsistent text and outliers.

## 3. Cleaning decisions

| Issue | Count | Decision | Why |
|---|---|---|---|
| Inconsistent text (`delhi`, `DELHI`, `  Delhi `, `Bangalore`, `COD`, `Canceled`) | many | **Corrected** | Same thing must be counted once |
| Duplicate rows | 30 | **Removed** (after text was corrected) | Avoid double counting |
| Missing City / Payment_Method | 14 / 18 | **Kept**, set to `Unknown` | Order is still valid |
| Missing Discount | 11 | **Kept**, set to 0 | No discount recorded means no discount |
| Missing Preparation_Time_Min | 79 | 18 **filled** with restaurant median; 61 left empty | Cancelled orders may never have reached the kitchen |
| Missing Delivery_Time_Min | 140 | **Kept as missing** | Mostly cancelled orders; guessing would distort averages |
| Missing Customer_Rating | 498 | **Kept as missing** | Many customers do not rate |
| Missing Order_Value | 8 | **Excluded** | Money cannot be calculated |
| Order_Value above Rs 20,000 | 3 | **Excluded** | Data-entry error (e.g. 99,999 for one meal) |
| Delivery time above 180 min | 4 | **Time set to missing, order kept** | Order is real, the time is not |
| IQR outliers (41 order values, 18 delivery times) | 59 | **Kept and flagged** | Party orders and rainy-day delays are real |

Rows: 1,500 raw - 30 duplicates - 3 impossible values - 8 missing values = **1,459 cleaned rows**.

## 4. How calculated columns and cancelled orders are handled

* `Net_Order_Value = Order_Value - Discount`; `Total_Order_Amount = Net_Order_Value + Delivery_Fee`.
* `Order_Value` is a food bill, **not company revenue**.
* Cancelled and refunded orders are **excluded from all money and delivery-time calculations**. Example: total order value is Rs 6,37,003 if every order is counted, but only **Rs 5,45,766** for delivered orders. The Rs 91,237 difference was never a completed sale.

## 5. Findings

**Orders and status**
* 1,459 orders; 1,263 delivered = **86.6% completion rate**. 8.3% cancelled, 5.1% refunded.

**Cities**
* Delhi (235), Mumbai (219) and Bengaluru (213) generate the most orders. Delhi also has the highest delivered order value (Rs 88,352). Jaipur has the fewest orders (76).

**Restaurants and cuisines**
* Top restaurants by delivered orders: Pizza Junction (86), Biryani House (83), Dragon Wok (68), Dosa Corner (66), Spice Route (66).
* Top cuisines by delivered orders: North Indian (161), Street Food (158), Pizza (144), Biryani (137), Mughlai (120).
* Popular is not the same as best. Biryani House (4.05) and Dosa Corner (4.04) have the best average ratings among the top restaurants, while Pizza Junction (3.55) is the most ordered. Mughlai (Rs 637) and Pizza (Rs 592) have the highest average order values.

**Order value**
* Average delivered order Rs 432, median Rs 385. The mean is higher because a few large orders pull it up. 90% of delivered orders are below Rs 689.

**Delivery performance**
* Average delivery time **45.4 minutes** (promised average 52.0). **22.7%** of delivered orders are late; when late they are about 9.7 minutes late.
* Peak hours (13, 14, 20, 21, 22) are slower: 49.5 minutes and 66.0% on time, compared with 41.2 minutes and 88.8% on time at other hours.
* Mumbai is slowest (49.3 min, 69.4% on time); Jaipur is fastest (39.5 min).

**Payment methods**
* UPI is used for 44.6% of orders, then Cash on Delivery (18.6%) and Credit Card (12.1%).

**Time patterns**
* Orders grew every month, from 205 in April to 284 in September.
* Sunday (279) and Saturday (248) are the busiest days. The busiest hour is 20:00 (191 orders). Dinner (19-23) gets 607 orders and lunch (12-16) gets 466.

**Discounts**
* 38.9% of delivered orders used a discount. Orders with a discount average Rs 449 versus Rs 421 without. This is a relationship only: the discount is calculated from the order value, so it cannot prove that discounts cause bigger orders.

**Ratings**
* 961 of 1,459 orders have a rating; the average is 3.33. Fast Food has the lowest cuisine rating (2.9).

## 6. Suggested actions (for discussion)

1. Add delivery partners or adjust promised times during lunch and dinner peaks.
2. Look at Mumbai and Bengaluru delivery operations first.
3. Review low-rated, high-volume restaurants (for example Slice Station, Spice Route).
4. Promote UPI-friendly offers since it is the main payment method.
5. Run a proper A/B test before deciding that discounts increase order size.

## 7. Limitations

* Synthetic data with patterns built in by the generator.
* No commission, cost or profit data, so no company revenue or profit can be calculated.
* Six months only; ratings missing for about a third of orders; restaurants appear in every city.
