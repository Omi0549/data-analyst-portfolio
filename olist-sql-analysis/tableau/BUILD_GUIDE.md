# Build guide: Olist dashboard in Tableau Public

**Goal:** one interactive dashboard, "Olist Marketplace: Revenue and Delivery Performance", published on Tableau Public so you can link it from your portfolio, GitHub README and resume.

**Time:** about 2-3 hours the first time.

**Data file:** `olist_orders_for_tableau.csv` (in this folder). One row per delivered order, Jan 2017 to Aug 2018.

| Column | Meaning |
|---|---|
| order_id | Order ID (unique) |
| purchase_date | Date of purchase |
| state, state_code | Customer state (full name, 2-letter code) |
| category | Category of the most expensive item in the order |
| payment_type | Main payment type |
| items | Number of items in the order |
| revenue | Sum of item prices (BRL, freight excluded) |
| freight | Freight cost (BRL) |
| review_score | 1-5 stars (latest review; 643 orders have none) |
| days_to_deliver | Days from purchase to delivery |
| days_vs_estimate | Negative = early, positive = late |
| delivery_timing | Five buckets from "7+ days early" to "8+ days late" |
| is_late | 1 if delivered after the estimated date, else 0 |

## The numbers your dashboard must match

Use these to check you built it correctly (no filters on):

| KPI | Value |
|---|---|
| Orders | 96,203 |
| Revenue | 13,179,778 BRL (about 13.2M) |
| Avg order value | 137.00 BRL |
| % late | 8.1% |
| Avg review score | 4.16 |

If a number is different, something is filtered or aggregated wrongly; stop and fix that before going on.

## Step 0: Install and sign up (10 min)

1. Go to **public.tableau.com** and create a free account (needed to publish).
2. Download and install **Tableau Public** (the desktop app, free). It is separate from Tableau Desktop.
3. Everything you publish on Tableau Public is **public**. This dataset is fine to publish (it is anonymized), but keep the source credit on the dashboard (see Step 7).

## Step 1: Connect the data (5 min)

1. Open Tableau Public. On the left under **Connect**, choose **Text file**.
2. Pick `olist_orders_for_tableau.csv`.
3. In the data preview, check that `purchase_date` shows a calendar icon (Date). If it shows "Abc", click the icon and set the type to **Date**.
4. Click **Sheet 1** at the bottom to start building.

## Step 2: Create calculated fields (10 min)

Right-click in the Data pane (left side) > **Create Calculated Field**. Make these:

| Name | Formula | Number format |
|---|---|---|
| Orders | `COUNTD([order_id])` | Number, 0 decimals |
| Avg Order Value | `SUM([revenue]) / COUNTD([order_id])` | Number, 2 decimals |
| % Late | `SUM([is_late]) / COUNT([order_id])` | Percentage, 1 decimal |
| Avg Review | `AVG([review_score])` | Number, 2 decimals |
| Country | `"Brazil"` | (used for the map) |

Set formats: right-click the field > **Default Properties** > **Number Format**.

## Step 3: Build 6 sheets

Rename each sheet by double-clicking its tab. Use these colors everywhere: **blue `#2a78d6`** for normal, **orange `#eb6834`** for late/bad. Change a color via **Color** card > **Edit Colors**; type the hex code under "More Colors".

### Sheet "KPI Revenue", "KPI Orders", "KPI AOV", "KPI Late", "KPI Review" (5 tiny sheets)
For each: drag the matching measure to **Text** on the Marks card. Set the font to bold, size 24, and format the numbers as in Step 2. For revenue, use `SUM(revenue)` and format as Number (Custom) with units in millions: right-click > Format > Numbers > Custom `#,##0.0,,"M"`.
Check each against the table above.

### Sheet "Monthly Revenue" (line chart)
1. Drag **purchase_date** to Columns, then click the drop-down on the pill and choose **Month** (the continuous one, the second "Month", shows a full date like "May 2017").
2. Drag **revenue** to Rows (SUM).
3. Marks type: **Line**. Color: blue. Turn on **Circle** markers: Marks card > Color > Effects, or add a dual mark; skip this if it fights you.
4. Right-click the title > Edit title: "Monthly revenue (BRL)".
5. **Check:** Nov 2017 should be about 988k (987,648), the peak. Jan 2017 about 112k.
6. Optional: add an annotation on Nov 2017: right-click the point > **Annotate** > Point, "Black Friday: 1,176 orders on 24 Nov".

### Sheet "Review by Delivery" (bar chart)
1. Drag **delivery_timing** to Columns.
2. Drag **Avg Review** to Rows.
3. Marks > **Color**: drag **delivery_timing** onto Color, then edit colors: the two "early" buckets blue, the three "late" buckets orange.
4. Put **Avg Review** on **Label** so the values show.
5. **Check:** 4.32, 4.20, 3.75, 2.30, 1.73 from left to right. (These differ by about 0.02 from the SQL README because this file only covers Jan 2017 to Aug 2018.)
6. Title: "Reviews fall sharply when orders arrive late".

### Sheet "Late Rate by State" (map)
1. Right-click **state** in the Data pane > **Geographic Role** > **State/Province**.
2. Right-click **Country** > **Geographic Role** > **Country/Region**.
3. Double-click **state**; Tableau draws a map. If it asks, add **Country** to Detail.
4. Drag **% Late** to **Color** (use a single-hue palette, light to dark orange; choose **Edit Colors** > Orange-type sequential) and to **Label** if the labels fit.
5. **Check:** Ceará about 15.4%, Bahia 14.0%, Rio de Janeiro 13.5%, São Paulo 5.9%.
6. **If the map fails** (states do not recognize), use a horizontal bar chart instead: **state** on Rows, **% Late** on Columns, sort descending. The message is the same.

### Sheet "Top Categories" (bar chart)
1. Drag **category** to Rows and **revenue** (SUM) to Columns.
2. Click the sort icon on the toolbar (descending).
3. Drag **category** to **Filters** > **Top** tab > By field > Top **10** by Sum of revenue.
4. Color: blue. Add revenue as Label.
5. **Check:** health_beauty is first with about 1.23M, then watches_gifts at about 1.16M.

### Sheet "Revenue by Payment" (optional extra)
**payment_type** on Rows, **Orders** on Columns. Skip if you want a smaller dashboard.

## Step 4: Assemble the dashboard (20 min)

1. Click the **New Dashboard** icon (the second icon at the bottom).
2. Size (bottom left): **Fixed size**, 1200 x 900.
3. Drag a **Horizontal** container to the top and put the 5 KPI sheets inside it, evenly spaced.
4. Below: left "Monthly Revenue", right "Review by Delivery".
5. Below that: left "Late Rate by State", right "Top Categories".
6. Add a **Text** object at the top for the title: "Olist Marketplace: Revenue and Delivery Performance". Under it, a smaller line: "Delivered orders, Jan 2017 to Aug 2018. Revenue in Brazilian reals (BRL), freight excluded."
7. Hide extra legends (click the legend > the arrow > **Remove**) except where color is not obvious.

## Step 5: Make it interactive (10 min)

1. On the dashboard, click the map sheet; at its top right click the **funnel icon** ("Use as Filter"). Do the same for "Top Categories".
   Now clicking Bahia or a category updates every chart and KPI.
2. Add filters: click a sheet > its drop-down arrow > **Filters** > **purchase_date** (use **Range of dates**) and **state**. Set them to **Apply to Worksheets > All Using This Data Source** so the KPIs also move.
   (If a filter is missing from the list, first drag the field to Filters on one sheet, right-click that pill, and choose **Apply to Worksheets > All Using This Data Source**.)
3. Test: click a state, a category, change the date range, then click an empty area to reset.

## Step 6: Review checklist

- [ ] KPIs match the table at the top with no filters.
- [ ] Every chart has a clear title, and axes have units (BRL).
- [ ] Blue = normal, orange = late; colors are consistent.
- [ ] No overlapping labels; readable at 100% zoom.
- [ ] Source credit and license note present (Step 7).

## Step 7: Add the source credit, then publish

1. Add a small Text object at the bottom: "Data: Olist, Brazilian E-Commerce Public Dataset (Kaggle), CC BY-NC-SA 4.0. Analysis by Om Biswal."
2. **File > Save to Tableau Public As...** and sign in. Name it "Olist Marketplace: Revenue and Delivery Performance".
3. Your browser opens the published page. Copy its **URL**.
4. Check it opens in a private/incognito window.
5. Take a full-dashboard screenshot and save it as `outputs/dashboard.png` in the project folder for the README.

## When something goes wrong

- Numbers look doubled: you used SUM on a calculated field that already aggregates; or the same field is on two sheets with different filters.
- Months show as "May" only: you picked the discrete Month instead of the continuous one.
- State names do not map: check the Geographic Role on **state** and that **Country** is on Detail.
- Send me a screenshot of the sheet or dashboard and the number that looks off; I will help find the cause.
