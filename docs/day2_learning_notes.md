# Day 2 — Data Cleaning: Learning Notes

Project: Retail Customer & Sales Analytics (UCI Online Retail II)

---

## 1. What We Did Today

1. Loaded the cleaned-Day-1 dataset and checked for fully duplicate rows.
2. Diagnosed and fixed mixed data types in `Invoice` and `StockCode`.
3. Identified cancelled orders (`Invoice` starting with `"C"`) and flagged them instead of deleting them.
4. Investigated non-product `StockCode`s (`POST`, `D`, `M`, `DOT`, `ADJUST`, `S`, `B`, `AMAZONFEE`, `GIFT`) using their `Description` as evidence — corrected an initial wrong assumption that *all* all-letter codes were non-products (some, like `PADS` and the `DCGS*` codes, turned out to be real products).
5. Recovered ~2,563 missing `Description` values by looking up the same `StockCode` elsewhere in the data; filled the remaining 365 truly unrecoverable ones with `"Unknown Product"` rather than dropping the rows.
6. Investigated `Price` anomalies — found 3 extreme negative "bad debt" adjustment rows (already caught by the non-product flag) and ~3,681 zero-price rows (real product codes, likely free samples/write-offs). Built a combined `IsValidSale` flag.
7. Created `data_customers`, a filtered subset excluding rows with missing `Customer ID`, for future customer-level analysis (RFM).
8. Added a `TotalPrice` calculated column (`Quantity × Price`).
9. Exported both the full cleaned dataset and the customer-only subset to `data/processed/`.

---

## 2. Python / Pandas Fundamentals Covered

| Concept | Method / Pattern | Why It Matters |
|---|---|---|
| Detecting duplicates | `data.duplicated()`, `.sum()` | `.duplicated()` returns True/False per row; `.sum()` treats True as 1 to get a count |
| Removing duplicates | `data.drop_duplicates(keep='first')` | `keep` controls which copy survives — `'first'`, `'last'`, or `False` (drop all copies) |
| Checking a single value's type | `type(x)` | Confirms whether a column secretly contains mixed types |
| Checking types across a whole column | `data['col'].apply(type).value_counts()` | Reveals mixed dtypes hiding inside an `object` column |
| Forcing consistent type | `data['col'].astype(str)` | Needed before using `.str` accessor methods; prevents silent `NaN` results |
| String accessor methods | `.str.startswith()`, `.str.isalpha()` | Pattern-match text columns; only work reliably on true string columns |
| Membership filtering | `data['col'].isin([...])` | Flags rows where a column matches any value in a list |
| Boolean masking / combining conditions | `~A & B & (C > 0)` | `~` = NOT, `&` = AND — combine multiple True/False conditions into one flag |
| Counting non-null values per group | `data.groupby('col')['other_col'].count()` | `.count()` ignores NaNs — useful for checking what's recoverable |
| Filling missing values from a lookup | `data['col'].fillna(data['key'].map(mapping))` | `.fillna()` only touches existing NaNs; `.map()` alone would overwrite everything |
| Filtering out nulls | `data[data['col'].notnull()]` | Keep only rows where a column has a real value |
| Calculated columns | `data['new'] = data['a'] * data['b']` | Pandas operations are vectorized — apply to the whole column at once, no loops needed |
| Saving to CSV | `data.to_csv(path, index=False)` | `index=False` avoids writing a meaningless row-number column into the file |

---

## 3. Data Analytics Fundamentals Covered

- **Keep vs. Flag vs. Drop framework for messy data:**
  - **Drop** only when a value can't be recovered *and* has no use for any analysis (e.g. fully duplicate rows).
  - **Flag** when a value/row is irrelevant to the *current* analysis but valid for another (e.g. cancelled orders, missing Customer ID, non-product codes).
  - **Fix/Recover** when the true value can be reconstructed from elsewhere in the data (e.g. missing Description via StockCode lookup).

- **Never trust a column's format/pattern alone** — verify meaning using evidence (checking `Description` before assuming all-letter `StockCode`s were non-products).

- **Zero-price vs. negative-price distinction** — zero prices don't distort revenue totals (contribute $0) but *can* distort quantity-based metrics (e.g. "top-selling products by units"); negative prices are outright invalid and need investigation.

- **Why keep raw data untouched** — always derive cleaned data into a separate file/folder (`data/processed/`), never overwrite the original raw export.

---

## 4. Possible Interview Questions From Today's Work (With Answers)

**Data cleaning philosophy**

- **Walk me through your approach to handling missing data in this project.**
  I used a three-way decision instead of a blanket rule: drop only if a value was truly unrecoverable and had no use anywhere (e.g. 365 rows with no way to recover a product description); recover/fix if the true value could be reconstructed from elsewhere in the data (e.g. filling ~2,563 missing descriptions by looking up the same StockCode elsewhere); and flag rather than delete if a value was irrelevant to the current analysis but valid for another (e.g. missing Customer ID — I kept those rows for country/product analysis, but excluded them only when doing customer-level analysis).

- **Why did you flag certain rows instead of deleting them?**
  Because deleting them would silently remove real transaction data — valid `Quantity`, `Price`, and `Country` — from analyses that don't actually depend on the field that was missing. For example, a row missing `Customer ID` still tells me real information about country-level revenue. Deleting the whole row would just be data loss for no reason.

- **Under what conditions would you actually drop a row?**
  Only when the row was true noise with zero informational value in any context — like the 6,865 fully duplicate rows (identical across every column, almost certainly a system/export glitch), where keeping the duplicate would have double-counted a transaction that never happened twice.

**Duplicates**

- **How did you detect duplicate rows in your dataset?**
  `data.duplicated()` flags any row that exactly matches an earlier row across every column; chaining `.sum()` gives the total count. I found 6,865 out of 525,461 rows (~1.3%).

- **What does the `keep` parameter in `drop_duplicates()` do?**
  It decides which copy of a duplicate set survives: `'first'` keeps the first occurrence and drops the rest, `'last'` keeps the last, and `False` drops every copy including the first. I used `keep='first'` since the copies were identical anyway — it didn't matter which one I kept.

- **What's a plausible real-world cause of exact duplicate transaction rows?**
  Since every field matched down to the exact second, it's unlikely to be two genuinely separate transactions — more plausibly a system glitch, like a double-scan at checkout or an export process running twice over the same data.

**Data types**

- **What issue did you find with the `Invoice` and `StockCode` columns, and how did you discover it?**
  Both were stored as `dtype: object` but actually contained a mix of Python `int` and `str` values — numeric-looking codes were read in as integers, while codes containing letters (like `C489449` or `POST`) were read in as strings. I discovered it when `.str.startswith('C')` returned `NaN` instead of `True`/`False` for rows I knew weren't missing, which led me to check `data['Invoice'].apply(type).value_counts()` and confirm the mixed types directly.

- **Why can a column with `dtype: object` still contain more than one actual Python type?**
  `object` is pandas' catch-all dtype for anything that isn't a fixed numeric/boolean/datetime type — it doesn't enforce that every value inside is the same Python type. A column can silently hold a mix of `int`, `str`, `float`, etc., unless you explicitly standardize it (e.g. with `.astype(str)`).

- **Why did `.str.startswith()` silently return `NaN` instead of throwing an error?**
  Pandas' `.str` accessor methods are designed to skip non-string elements gracefully rather than crash — so calling a string method on an integer element returns `NaN` instead of raising an exception. That's actually more dangerous than an error, because it can produce a plausible-looking but wrong result if you don't check for it.

**Business-code investigation (non-product StockCodes)**

- **How did you identify which `StockCode`s weren't real products?**
  I first found all-letter `StockCode`s using `.str.isalpha()` (real product codes always contain a digit), then cross-checked each one's actual `Description` text before deciding — rather than assuming format alone meant "not a product."

- **Describe a time your initial assumption about the data turned out to be wrong, and how you corrected it.**
  I initially assumed every all-letter `StockCode` (like `PADS`, `GIFT`, `DCGSSGIRL`) was a non-product administrative entry, purely based on the pattern. Checking the actual `Description` values showed some — like `PADS` ("PADS TO MATCH ALL CUSHIONS") and the `DCGS*` codes ("BOYS/GIRLS PARTY BAG") — were real products with inconsistent code formatting. I corrected my exclusion list to only include codes with confirmed non-product descriptions (`POST`, `D`, `M`, `DOT`, `ADJUST`, `S`, `B`, `AMAZONFEE`, plus `GIFT` since its description was blank everywhere and unverifiable).

- **Why is it risky to filter data based on a pattern (like "all-letter codes") instead of verifying meaning?**
  A pattern is a proxy, not the actual thing you care about — it can both over-match (excluding real products that happen to fit the pattern) and under-match (missing non-products that don't). Verifying against real evidence (the `Description` field) avoids silently corrupting the analysis based on a false assumption.

**Price/Quantity anomalies**

- **Why can't `Price` be negative in a legitimate transaction, unlike `Quantity`?**
  Negative `Quantity` has a real business meaning — a return/refund. Negative `Price` doesn't have an equivalent legitimate meaning for a sale; the 3 negative-price rows I found were actually `"Adjust bad debt"` accounting entries, not real transactions, and were already caught by my non-product `StockCode` flag (`StockCode = 'B'`).

- **Does a zero-price row affect a revenue calculation? Does it affect a quantity-based calculation? Why the difference?**
  No — since revenue is `Quantity × Price`, a `Price` of 0 contributes exactly $0 regardless of quantity, so it doesn't distort total revenue. It *can* distort a quantity-based metric like "top-selling products by units," since those rows still count units moved (e.g. free samples or stock write-offs) without representing real sales value. That's why I built a combined `IsValidSale` flag (not cancelled, not non-product, price > 0) specifically for revenue-focused analysis, while leaving quantity-based analysis to make its own judgment call about whether to include them.

**Customer ID**

- **Why didn't you fill in missing Customer IDs the way you filled in missing Descriptions?**
  `Customer ID` is a unique identifier — there's no data-driven way to reconstruct which specific customer made a purchase if it wasn't recorded. `Description`, by contrast, isn't unique per row; the same `StockCode` appears many times, so I could recover a missing description from another row with the same code. Guessing a Customer ID would fabricate identity data, which would corrupt any customer-level analysis built on top of it.

- **How did you handle analyses that do vs. don't depend on Customer ID?**
  I kept the full cleaned dataset (`data`) for analyses that don't need customer identity — country revenue, product popularity — and created a separate filtered subset (`data_customers`, using `.notnull()` on Customer ID) specifically for customer-level analysis like RFM, so the ~107,833 rows with missing IDs don't corrupt customer segmentation but also aren't wastefully deleted from the rest of the analysis.

**General**

- **What was the most surprising or difficult part of cleaning this dataset?**
  Discovering that `Invoice` and `StockCode` had silently mixed Python types within a single `object` column — it didn't throw an error, it just produced wrong-looking (`NaN`) results downstream, which taught me to verify column contents with `.apply(type).value_counts()` whenever behavior looks off, rather than trusting `dtype: object` at face value.

- **If you had another week, what would you clean or investigate further?**
  I'd look more closely at the `GIFT` StockCode (currently excluded due to lack of evidence) to see if transaction patterns (price, quantity, frequency) suggest what it actually represents, and I'd consider whether to bring in the second dataset sheet (2010-2011) for a longer time-series view — something I intentionally scoped out this week to protect time for SQL, Power BI, and documentation.

- **How would you explain your data cleaning decisions to a non-technical stakeholder?**
  I'd frame it around trust and impact: "I made sure every number in this dashboard reflects real transactions — I removed accidental duplicate records, separated real sales from internal adjustments and shipping charges, and made deliberate choices about missing data so we don't lose real sales history just because one field wasn't recorded."

---

*Notes generated collaboratively while building the project — reflects decisions actually made and reasoned through, not a generic checklist.*
