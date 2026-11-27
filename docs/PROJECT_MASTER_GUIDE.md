# Retail Data Pipeline & Customer Analytics Platform — Master Guide

A complete reference: what this project is, what's been built, every interview question that could
come from it, and every remaining step to finish it — written so you can follow it standalone,
without needing this conversation open.

---

## 1. Project Description

**What it is:** An end-to-end retail analytics project built on the UCI **Online Retail II**
dataset (real transaction data from a UK-based online retailer, Dec 2009–Dec 2010). The project
takes raw, messy transactional data and turns it into a governed data warehouse, SQL-based business
analysis, customer segmentation, and an interactive Power BI dashboard.

**Tools used:**
- **Python** (pandas, matplotlib, seaborn) — data cleaning and exploratory analysis
- **MySQL** — data warehouse (star schema: fact + dimension tables)
- **SQL** — business queries, CTEs, window functions, RFM segmentation
- **Power BI** — interactive dashboard connected live to MySQL
- **Git/GitHub** — version control and portfolio hosting

**What it solves (the business problem):** A retail business generates raw transaction logs that,
on their own, don't answer anything. This project answers three concrete business questions:
1. Which country generates the most revenue? (geographic focus for marketing/logistics)
2. Which products do customers actually buy most — and does "top-selling" even mean one thing? (inventory/stocking decisions)
3. Who are the most valuable customers, and which of them are at risk of churning? (retention strategy, via RFM segmentation)

**What makes it different from a typical portfolio project:**
- It doesn't stop at "I made some charts." It models the data properly into a **star schema
  warehouse** (a real data engineering practice), not just a flat CSV read into Power BI.
- Every cleaning decision was evidence-based, not assumption-based — e.g. an initial assumption
  that all-letter product codes were "non-products" was tested against real data and corrected
  before being trusted.
- It explicitly separates **revenue** from **profit** claims, since the dataset has no cost data —
  a precision most beginner projects get wrong.
- It catches a real data-completeness bug (partial December data) before it could become a false
  "sales collapsed" insight — and documents that catch rather than hiding it.
- RFM segmentation is computed with actual SQL window functions (`NTILE`), not simplified in pandas
  only, and is re-exposed as a MySQL **view** so Power BI can consume it without re-implementing
  the scoring logic in DAX.

---

## 2. What Has Been Done So Far (Full Recap)

### Day 1 — Setup & Business Framing
- Sourced the dataset (UCI Online Retail II, `Year 2009-2010` sheet).
- Set up project structure: `data/raw`, `data/processed`, `notebooks`, `SQL`, `docs`.
- Defined 3 business questions (see above), grounded in real business reasoning, not arbitrary.
- Loaded Excel into pandas, converted to CSV for faster reloads.
- Ran first inspection (`.shape`, `.info()`, `.isnull().sum()`) — found `Description` (2,928 missing)
  and `Customer ID` (107,927 missing) needed attention.

### Day 2 — Data Cleaning (`notebooks/01_data_loading_inspection.ipynb`)
- Removed 6,865 fully duplicate rows.
- Fixed mixed data types in `Invoice` and `StockCode` (silently mixed `int`/`str` inside `object`
  columns — diagnosed via `.apply(type).value_counts()` after `.str.startswith()` returned
  unexpected `NaN`s).
- Flagged cancelled orders (`IsCancelled` = Invoice starts with `"C"`) — kept, not dropped.
- Investigated non-product `StockCode`s using actual `Description` evidence (not just code
  pattern) — correctly excluded `POST`, `D`, `M`, `DOT`, `ADJUST`, `S`, `B`, `AMAZONFEE`, `GIFT`,
  while correctly *keeping* `PADS` and the `DCGS*` codes after discovering they were real products.
- Recovered ~2,563 missing `Description` values via StockCode lookup; filled the remaining 365
  unrecoverable ones with `"Unknown Product"`.
- Investigated `Price` anomalies (3 negative "bad debt" rows, ~3,681 zero-price rows); built a
  combined `IsValidSale` flag (not cancelled AND not non-product AND price > 0).
- Created `data_customers` — filtered subset excluding missing `Customer ID`, for customer-level
  analysis only.
- Added `TotalPrice` = `Quantity × Price`.
- Exported cleaned data to `data/processed/cleaned_online_retail.csv` and
  `cleaned_online_retail_customers.csv`.

### Day 3 — EDA (`notebooks/02_eda.ipynb`)
- Monthly revenue trend (line chart). Caught and correctly handled a data-completeness issue:
  December 2010 only has 9 of 31 days of data (verified via `InvoiceDate.max()`), annotated on the
  chart rather than hidden or misinterpreted as a real decline.
- Top 10 products by **quantity** vs. by **revenue** — different rankings; "Regency Cakestand 3
  Tier" is #1 by revenue but absent from the quantity top 10, showing "best-selling" is ambiguous.
- Top countries by revenue — UK dominates (as expected, UK retailer); built a second chart
  excluding UK to reveal the real international ranking (EIRE > Netherlands > Germany > France).

### Day 4 — MySQL Data Warehouse (`notebooks/03_load_warehouse.ipynb`, `SQL/01_schema.sql`)
- Designed a **star schema**: `dim_customer`, `dim_product`, `dim_date` (dimension tables) +
  `fact_sales` (fact table, one row per transaction line item, grain matches source data).
- Used surrogate auto-increment keys (`CustomerKey`, `ProductKey`) for dimensions; a
  human-readable `YYYYMMDD` integer key for `dim_date` (standard warehousing convention).
- Used `DECIMAL` (not `FLOAT`) for all money columns to avoid floating-point rounding errors.
- Loaded via Python (`sqlalchemy` + `pymysql`): `dim_customer` (4,383 rows), `dim_product` (4,632
  rows), `dim_date` (307 rows), `fact_sales` (518,596 rows — matches cleaned dataset exactly).
- Verified referential integrity: 0 orphaned foreign keys (LEFT JOIN + IS NULL check).

### Day 5 — SQL Analysis + RFM (`SQL/02_rfm_analysis.sql`, `SQL/03_create_rfm_view.sql`)
- Revenue-by-country query using `JOIN` + `GROUP BY`.
- **RFM segmentation** using CTEs (`WITH ... AS`) and the `NTILE(4)` window function to score
  4,286 customers (those with at least one valid sale) on Recency, Frequency, Monetary.
- Segment results: Champions (1,265 customers, avg spend ₤4,943.17), At Risk (524 customers, avg
  spend ₤2,341.57), New/Occasional (666), Others (1,831) — a concrete, quantified case for a
  targeted win-back campaign on the "At Risk" segment.
- Saved RFM logic as a MySQL **view** (`vw_customer_rfm`) so Power BI can import it directly.

### Day 6 (in progress) — Power BI
- Installed Power BI Desktop + MySQL Connector/NET (Power BI's MySQL connector needs this
  separately installed).
- Connected Power BI to the `retail_analytics` MySQL database, loaded all 5 tables/views
  (`dim_customer`, `dim_product`, `dim_date`, `fact_sales`, `vw_customer_rfm`).
- Fixed an auto-detected many-to-many relationship between `fact_sales` and `vw_customer_rfm`
  (deleted it) and replaced it with a correct one-to-one relationship between
  `dim_customer.CustomerKey` and `vw_customer_rfm.CustomerKey`.
- **Currently mid-step:** finalizing that last relationship's column mapping (making sure it's
  `CustomerKey` ↔ `CustomerKey`, not `CustomerID` ↔ `CustomerKey`) before saving it.

**Not done (intentionally skipped):** Apache Airflow orchestration — deliberately dropped given a
2-day timeline and zero prior Docker/Airflow/WSL experience, to protect time for a complete,
defensible core project. See the "Honest Airflow Talking Point" section below for how to handle
this in the DE interview.

---

## 3. Remaining Steps — Detailed, Start to Finish

### Step A — Finish the Power BI Model Relationships

1. In the "New relationship" / edit relationship dialog:
   - **From table:** `dim_customer` → click the **`CustomerKey`** column (not `CustomerID`).
   - **To table:** `vw_customer_rfm` → click the **`CustomerKey`** column.
   - **Cardinality:** One to one (1:1).
   - **Cross-filter direction:** Both.
   - Check **"Make this relationship active"**.
   - Click **Save**.
2. Go to **Model view** (left sidebar icon that looks like connected boxes) and visually confirm:
   - `dim_product` (1) ↔ (*) `fact_sales`
   - `dim_customer` (1) ↔ (*) `fact_sales`
   - `dim_date` (1) ↔ (*) `fact_sales` — if this line is missing, drag `DateKey` from `dim_date`
     onto `DateKey` in `fact_sales` to create it.
   - `dim_customer` (1) ↔ (1) `vw_customer_rfm`
   - **Nothing** should directly connect `vw_customer_rfm` to `fact_sales`.

### Step B — Create DAX Measures

Go to **Report view** (top bar-chart icon). Click on the `fact_sales` table in the Data pane, then
**Home → New measure** for each of these (type each formula exactly, press Enter):

```dax
Total Revenue = SUM(fact_sales[TotalPrice])
```
```dax
Total Quantity Sold = SUM(fact_sales[Quantity])
```
```dax
Total Orders = DISTINCTCOUNT(fact_sales[InvoiceNo])
```
```dax
Total Customers = DISTINCTCOUNT(fact_sales[CustomerKey])
```
```dax
Average Order Value = DIVIDE([Total Revenue], [Total Orders])
```

**Why measures instead of just dragging raw columns into visuals:** measures are reusable,
named calculations that respect whatever filters/slicers are applied on a report page — dragging
a raw column in only works for simple sums and doesn't give you controlled, well-named KPIs you
can reuse across multiple visuals.

### Step C — Build Report Page 1: "Sales Overview"

1. Rename "Page 1" (double-click the tab at the bottom) to **"Sales Overview"**.
2. Add **4 Card visuals** (Visualizations pane → the "Card" icon) across the top: drag
   `Total Revenue`, `Total Orders`, `Total Customers`, `Average Order Value` into 4 separate cards.
3. Add a **Line chart**: X-axis = `dim_date[Month]` (or better, drag `dim_date[Year]` and
   `dim_date[Month]` together, or use `dim_date[MonthName]` sorted correctly — see note below),
   Y-axis = `Total Revenue`. Title it "Monthly Revenue Trend".
   - **Sorting note:** `MonthName` sorts alphabetically by default (April before January) — fix by
     clicking the visual's "..." menu → **Sort by column**, or set `dim_date[MonthName]` to sort by
     `dim_date[Month]` via **Modeling tab → Sort by Column** in the Data pane.
4. Add a **Bar chart (horizontal)**: Axis = `dim_product[Description]`, Value = `Total Revenue`.
   Use the visual's filter pane to show **Top N = 10** (right-click the field well → "Top N", or
   use a visual-level filter). Title: "Top 10 Products by Revenue".
5. Add another **Bar chart**: Axis = `dim_customer[Country]`, Value = `Total Revenue`, Top N = 10.
   Title: "Top 10 Countries by Revenue". Add a **slicer** for `dim_customer[Country]` nearby so a
   viewer can exclude/include UK interactively (solves the "UK dominates the chart" problem you
   already handled in Python, this time interactively).

### Step D — Build Report Page 2: "Customer Segmentation (RFM)"

1. Add a new page, rename it **"Customer Segmentation"**.
2. Add a **Bar chart**: Axis = `vw_customer_rfm[Segment]`, Value = Count of `CustomerKey` (drag
   `CustomerKey` into Values, set it to "Count" via the field's dropdown, not "Sum"). Title:
   "Customers per Segment".
3. Add a **Bar or Card visual** showing **average Monetary per segment**: Axis = `Segment`, Value
   = Average of `vw_customer_rfm[Monetary]` (again, set the aggregation via the field dropdown).
4. Add a **Table visual** listing `CustomerID`, `Recency`, `Frequency`, `Monetary`, `Segment` —
   sorted by `Monetary` descending, so a viewer can drill into individual customers.
5. Add a **Slicer** on `Segment` so a viewer can filter the table to just "At Risk" customers, for
   example — directly demonstrating the "who should we target for a win-back campaign" business
   question.

### Step E — Formatting & Polish

1. **View tab → Themes** — pick a clean built-in theme (avoid default if it looks too plain).
2. Add a **Text box** at the top of each page with a clear title ("Retail Sales & Customer
   Analytics Dashboard") and your name/date.
3. Make sure every visual has a clear, human title (not the default field name) — click each
   visual → Format pane → General/Title → edit text.
4. Check both pages at a reasonable window size — nothing overlapping or cut off.

### Step F — Save

**File → Save As** → save into your project folder as
`D:\retail-analytics-project\powerbi\retail_analytics_dashboard.pbix` (create the `powerbi` folder
first if it doesn't exist).

### Step G — GitHub Upload

1. Create the `.gitignore` file in your project root with at least:
   ```
   .venv/
   __pycache__/
   *.pyc
   ```
   (Do **not** ignore your CSVs/notebooks/SQL/pbix — those are the point of the portfolio. Only
   ignore environment/cache files.)
2. In your terminal, from the project root:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: retail analytics pipeline, warehouse, RFM, dashboard"
   ```
3. Create a new **empty** repository on GitHub (no README/license auto-generated, to avoid merge
   conflicts), copy its remote URL, then:
   ```bash
   git remote add origin <your-repo-url>
   git branch -M main
   git push -u origin main
   ```
4. Write a proper `README.md` at the project root (not inside `docs/`) covering: project title,
   one-paragraph description, tools used, folder structure, how to reproduce (brief), key
   business insights, and a link/screenshot of the Power BI dashboard.

### Step H — Final CV Bullet Check

Rewrite your CV bullets to be **100% accurate** to what you built. Suggested honest version:

> **Retail Data Pipeline and Customer Analytics Platform — UCI Online Retail II | Python | MySQL | Power BI**
> - Cleaned and validated 525K+ raw retail transactions using Python/Pandas, resolving duplicate
>   records, mixed data types, invalid prices, and non-product entries through evidence-based
>   investigation rather than pattern assumptions.
> - Designed and built a MySQL star-schema data warehouse (fact and dimension tables) with
>   referential integrity checks, and implemented SQL-based RFM customer segmentation using CTEs
>   and window functions.
> - Built an interactive Power BI dashboard covering sales KPIs, product and country trends, and
>   RFM-based customer segmentation, connected live to the MySQL warehouse.

(Notice: **Apache Airflow removed** — do not claim it. If asked, use the honest talking point
below.)

---

## 4. Honest Talking Point: Apache Airflow (Since It's Not Implemented)

If an interviewer asks about orchestration/Airflow (since it may still be mentioned in an earlier
version of your CV, or you want to bring it up proactively):

> "I structured the pipeline in discrete, well-defined stages — extract from source, clean and
> validate in Python, load into a modeled MySQL warehouse, then transform via SQL. Given my
> timeline, I prioritized building a complete, correct, and verified analytics solution over
> adding an orchestration layer I hadn't used before and couldn't yet defend in depth. I understand
> Airflow's role — DAGs, task dependencies, scheduling, retries, and monitoring — and the next
> step I'd take is wrapping these existing stages as Airflow tasks rather than running them
> manually."

This is a mature, honest, and — importantly — **true** answer. It signals self-awareness and
prioritization skill, which matters more to a good interviewer than a fragile, half-understood tool
integration.

---

## 5. Full Interview Question Bank (With Model Answers)

### Project framing
**Q: Walk me through this project end to end.**
A: I took a real, messy UK retail transaction dataset and built a full analytics pipeline: cleaned
and validated it in Python, modeled it into a MySQL star-schema warehouse, ran SQL-based business
analysis including RFM customer segmentation, and built an interactive Power BI dashboard on top —
all traced back to three concrete business questions I defined upfront (country performance,
product popularity, customer loyalty/churn).

**Q: What was the hardest part of this project?**
A: Data type issues that failed silently — `Invoice` and `StockCode` secretly contained mixed
Python types inside one `object` column, which caused `.str` methods to return `NaN` instead of an
error. It taught me to verify column contents directly (`.apply(type).value_counts()`) rather than
trusting a column's apparent dtype.

**Q: What would you improve with more time?**
A: I'd add Apache Airflow to orchestrate the pipeline stages automatically, investigate the
ambiguous `GIFT` product code further, and potentially extend the warehouse with the second year of
data (2010-2011) for longer-term trend analysis — I intentionally scoped that out to protect time
for a complete, verified core project.

### Data cleaning
See `docs/day2_learning_notes.md` for the full, detailed Q&A on duplicates, data types, non-product
code investigation, price anomalies, and Customer ID handling — all still valid and worth
re-reading before the interview.

### Data warehouse / modeling (DE-focused)
**Q: Why did you use a star schema instead of just querying the flat CSV directly?**
A: A star schema avoids repeating descriptive text (country names, product descriptions) across
every one of 500K+ transaction rows, keeps data consistent (a customer's country is stored once,
not 50,000 times), and is the standard, query-efficient design for analytical (not transactional)
workloads.

**Q: Why surrogate keys instead of using the natural IDs (CustomerID, StockCode) directly as
primary keys?**
A: Surrogate keys are simple, stable integers — fast for joins, and they stay stable even if the
source system's ID format changes. It's standard warehouse practice to decouple the warehouse's
internal keys from the source system's identifiers.

**Q: Why does `dim_date` use a chosen `YYYYMMDD` integer key instead of an auto-increment key like
the other dimensions?**
A: It's a well-known data warehousing convention — a self-describing key that sorts and filters
correctly by date range through simple integer comparison, without needing a join just to know
what a key "means."

**Q: How did you verify your warehouse was loaded correctly?**
A: I ran LEFT JOIN + IS NULL checks from `fact_sales` to each dimension table, confirming 0
orphaned foreign key references — meaning every transaction correctly links to a real customer,
product, and date.

**Q: Why DECIMAL instead of FLOAT for money columns?**
A: Floating-point types can introduce small rounding errors that compound over many rows —
unacceptable for financial figures. DECIMAL stores exact values with a fixed number of digits.

### SQL / RFM
**Q: What's a CTE and why use one?**
A: A Common Table Expression (`WITH ... AS (...)`) is a named, temporary result set you can
reference later in the same query — it breaks a complex query into readable, labeled stages
instead of deeply nested subqueries.

**Q: What's a window function, and how does `NTILE()` differ from `GROUP BY`?**
A: A window function computes a value across a set of rows without collapsing them — each row
keeps its identity but gains a calculated value (like a rank or bucket). `GROUP BY` collapses many
rows into one row per group. `NTILE(4)` splits all rows into 4 equal buckets by rank, which is
exactly what's needed to score customers into quartiles without losing per-customer detail.

**Q: Explain Recency, Frequency, Monetary and how you calculated each.**
A: Recency = days since a customer's last real purchase (`DATEDIFF` against the dataset's max
date). Frequency = count of distinct invoices per customer. Monetary = sum of their `TotalPrice`.
Each gets scored into quartiles (1-4) and combined into a segment via a `CASE` statement.

**Q: Why did the RFM result have fewer customers than the full customer dimension?**
A: `customer_metrics` only includes customers with at least one row where `IsValidSale = TRUE`. A
small number of customers (97) had zero valid sales — every transaction they made was cancelled,
a non-product entry, or zero-price — so there's no real purchase history to calculate RFM from.

**Q: What business action follows from your "At Risk" segment findings?**
A: 524 customers, averaging ₤2,341.57 in historical spend, haven't purchased recently. That's
quantifiable revenue at risk of permanent churn — a strong, targeted case for a win-back campaign,
since they've already proven high value, making them a better ROI target than new-customer
acquisition.

**Q: Why did you save the RFM query as a MySQL VIEW?**
A: A view behaves like a virtual, always-up-to-date table without duplicating storage — it let
Power BI import RFM results directly via a normal table connection, instead of needing to
reimplement `NTILE()`-style window function logic in DAX, which is considerably harder.

### Power BI
**Q: Why model relationships in Power BI instead of just importing one big flat table?**
A: Keeping the star schema intact in Power BI (rather than flattening it) keeps the model
efficient and avoids duplicate/inflated data — Power BI's relationship engine is built to handle
exactly this fact/dimension structure, applying filters correctly across related tables.

**Q: What's the difference between a measure and a calculated column in Power BI?**
A: A measure (DAX) is computed dynamically based on current filter context (e.g. `Total Revenue`
recalculates depending on which country/date is selected). A calculated column is computed once
per row at load/refresh time and stored — used for static, row-level classifications, not
aggregations that need to respond to filters.

**Q: Why did you need a MySQL Connector/NET driver installed separately?**
A: Power BI's built-in MySQL connector relies on an external client library, not bundled with
Power BI itself — a common real-world integration detail, not unique to this project.

### Python / Pandas
See `docs/day2_learning_notes.md` for the full breakdown of pandas methods used and why (duplicates,
dtype fixes, `.str` accessor, `.isin()`, `.groupby()`, `.fillna()` with lookup, `.notnull()`,
calculated columns).

---

## 6. Quick-Reference: Project File Structure

```
retail-analytics-project/
├── data/
│   ├── raw/                        (original Excel/CSV, untouched)
│   └── processed/                  (cleaned CSVs)
├── notebooks/
│   ├── 01_data_loading_inspection.ipynb
│   ├── 02_eda.ipynb
│   └── 03_load_warehouse.ipynb
├── SQL/
│   ├── 01_schema.sql
│   ├── 02_rfm_analysis.sql
│   └── 03_create_rfm_view.sql
├── powerbi/
│   └── retail_analytics_dashboard.pbix
├── docs/
│   ├── day2_learning_notes.md
│   └── PROJECT_MASTER_GUIDE.md     (this file)
└── README.md
```
