USE retail_analytics;

WITH customer_metrics AS (
    SELECT 
        c.CustomerKey,
        c.CustomerID,
        DATEDIFF((SELECT MAX(FullDate) FROM dim_date), MAX(d.FullDate)) AS Recency,
        COUNT(DISTINCT f.InvoiceNo) AS Frequency,
        SUM(f.TotalPrice) AS Monetary
    FROM fact_sales f
    JOIN dim_customer c ON f.CustomerKey = c.CustomerKey
    JOIN dim_date d ON f.DateKey = d.DateKey
    WHERE f.IsValidSale = TRUE
    GROUP BY c.CustomerKey, c.CustomerID
),
rfm_scores AS (
    SELECT *,
        NTILE(4) OVER (ORDER BY Recency DESC) AS R_Score,
        NTILE(4) OVER (ORDER BY Frequency ASC) AS F_Score,
        NTILE(4) OVER (ORDER BY Monetary ASC) AS M_Score
    FROM customer_metrics
)
SELECT *,
    (R_Score + F_Score + M_Score) AS RFM_Total,
    CASE 
        WHEN R_Score >= 3 AND F_Score >= 3 AND M_Score >= 3 THEN 'Champions'
        WHEN R_Score <= 2 AND F_Score >= 3 AND M_Score >= 3 THEN 'At Risk'
        WHEN R_Score >= 3 AND F_Score <= 2 THEN 'New/Occasional'
        ELSE 'Others'
    END AS Segment
FROM rfm_scores
ORDER BY RFM_Total DESC;

WITH customer_metrics AS (
    SELECT 
        c.CustomerKey,
        c.CustomerID,
        DATEDIFF((SELECT MAX(FullDate) FROM dim_date), MAX(d.FullDate)) AS Recency,
        COUNT(DISTINCT f.InvoiceNo) AS Frequency,
        SUM(f.TotalPrice) AS Monetary
    FROM fact_sales f
    JOIN dim_customer c ON f.CustomerKey = c.CustomerKey
    JOIN dim_date d ON f.DateKey = d.DateKey
    WHERE f.IsValidSale = TRUE
    GROUP BY c.CustomerKey, c.CustomerID
),
rfm_scores AS (
    SELECT *,
        NTILE(4) OVER (ORDER BY Recency DESC) AS R_Score,
        NTILE(4) OVER (ORDER BY Frequency ASC) AS F_Score,
        NTILE(4) OVER (ORDER BY Monetary ASC) AS M_Score
    FROM customer_metrics
),
rfm_final AS (
    SELECT *,
        (R_Score + F_Score + M_Score) AS RFM_Total,
        CASE 
            WHEN R_Score >= 3 AND F_Score >= 3 AND M_Score >= 3 THEN 'Champions'
            WHEN R_Score <= 2 AND F_Score >= 3 AND M_Score >= 3 THEN 'At Risk'
            WHEN R_Score >= 3 AND F_Score <= 2 THEN 'New/Occasional'
            ELSE 'Others'
        END AS Segment
    FROM rfm_scores
)
SELECT Segment, COUNT(*) AS NumCustomers, ROUND(AVG(Monetary),2) AS AvgSpend
FROM rfm_final
GROUP BY Segment
ORDER BY NumCustomers DESC;