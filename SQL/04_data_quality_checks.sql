-- Manual data quality checks (the pipeline runs the same checks automatically in src/retail_pipeline/quality.py).
-- Every query should return 0.
USE retail_analytics;

-- Fact rows pointing at a product that doesn't exist
SELECT COUNT(*) AS orphaned_products
FROM fact_sales f
LEFT JOIN dim_product p ON f.ProductKey = p.ProductKey
WHERE p.ProductKey IS NULL;

-- Fact rows pointing at a date that doesn't exist
SELECT COUNT(*) AS orphaned_dates
FROM fact_sales f
LEFT JOIN dim_date d ON f.DateKey = d.DateKey
WHERE d.DateKey IS NULL;

-- Fact rows with a CustomerKey that doesn't exist (NULL CustomerKey = anonymous sale, which is allowed)
SELECT COUNT(*) AS orphaned_customers
FROM fact_sales f
LEFT JOIN dim_customer c ON f.CustomerKey = c.CustomerKey
WHERE f.CustomerKey IS NOT NULL AND c.CustomerKey IS NULL;

-- Valid sales must have a positive price
SELECT COUNT(*) AS valid_sales_with_bad_price
FROM fact_sales
WHERE IsValidSale = 1 AND Price <= 0;
