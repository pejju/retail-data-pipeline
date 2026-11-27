-- Star schema for the retail analytics warehouse.
-- Idempotent: safe to run on every pipeline run (IF NOT EXISTS everywhere).
-- The pipeline creates the database itself (name from DB_NAME in .env) and skips USE statements.

CREATE DATABASE IF NOT EXISTS retail_analytics;
USE retail_analytics;

CREATE TABLE IF NOT EXISTS dim_customer (
    CustomerKey INT AUTO_INCREMENT PRIMARY KEY,
    CustomerID INT,
    Country VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS dim_product (
    ProductKey INT AUTO_INCREMENT PRIMARY KEY,
    StockCode VARCHAR(20),
    Description VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS dim_date (
    DateKey INT PRIMARY KEY,
    FullDate DATE,
    Year INT,
    Month INT,
    MonthName VARCHAR(20),
    Quarter INT,
    Weekday VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS fact_sales (
    SalesKey INT AUTO_INCREMENT PRIMARY KEY,
    InvoiceNo VARCHAR(20),
    CustomerKey INT,
    ProductKey INT,
    DateKey INT,
    Quantity INT,
    Price DECIMAL(10,3),       -- 3 decimals: some items are priced at 0.001
    TotalPrice DECIMAL(12,3),
    IsCancelled BOOLEAN,
    IsValidSale BOOLEAN,
    FOREIGN KEY (CustomerKey) REFERENCES dim_customer(CustomerKey),
    FOREIGN KEY (ProductKey) REFERENCES dim_product(ProductKey),
    FOREIGN KEY (DateKey) REFERENCES dim_date(DateKey)
);
