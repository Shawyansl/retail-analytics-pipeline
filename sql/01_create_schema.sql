-- =====================================================
-- Retail Analytics Pipeline — Schema
-- بخش ۱: طراحی دیتابیس (Dimension + Fact Tables)
-- =====================================================

DROP TABLE IF EXISTS fact_inventory_snapshot;
DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS dim_branches;
DROP TABLE IF EXISTS dim_products;
DROP TABLE IF EXISTS dim_categories;
DROP TABLE IF EXISTS dim_customers;

-- -----------------------------------------------------
-- Dimension Tables
-- -----------------------------------------------------

CREATE TABLE dim_customers (
    customer_id          VARCHAR(10) PRIMARY KEY,
    first_name           VARCHAR(100),
    last_name            VARCHAR(100),
    email                VARCHAR(150),
    phone                VARCHAR(30),
    city                 VARCHAR(100),
    signup_date          DATE
);

-- category_id در پایتون به شکل 'CAT001' تولید می‌شود، پس SERIAL نیست.
CREATE TABLE dim_categories (
    category_id          VARCHAR(10) PRIMARY KEY,
    category_name        VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE dim_products (
    product_id           VARCHAR(10) PRIMARY KEY,
    product_name         VARCHAR(150) NOT NULL,
    category_id          VARCHAR(10) NOT NULL REFERENCES dim_categories(category_id),
    unit_cost            NUMERIC(12,2) CHECK (unit_cost >= 0),
    unit_price           NUMERIC(12,2) CHECK (unit_price >= 0)
);

CREATE TABLE dim_branches (
    branch_id            VARCHAR(10) PRIMARY KEY,
    branch_name          VARCHAR(150) NOT NULL,
    branch_city          VARCHAR(100),
    sales_channel        VARCHAR(50)
);

-- -----------------------------------------------------
-- Fact Tables
-- -----------------------------------------------------

CREATE TABLE fact_sales (
    sale_id              VARCHAR(20) PRIMARY KEY,
    sale_date            DATE NOT NULL,
    customer_id          VARCHAR(10) NOT NULL REFERENCES dim_customers(customer_id),
    product_id           VARCHAR(10) NOT NULL REFERENCES dim_products(product_id),
    branch_id            VARCHAR(10) NOT NULL REFERENCES dim_branches(branch_id),
    quantity             INT NOT NULL CHECK (quantity > 0),
    discount_percent     NUMERIC(5,2) DEFAULT 0 CHECK (discount_percent >= 0 AND discount_percent <= 100),
    payment_method       VARCHAR(50),
    gross_revenue        NUMERIC(14,2),
    discount_amount      NUMERIC(14,2),
    net_revenue          NUMERIC(14,2),
    gross_profit         NUMERIC(14,2),
    margin_percent       NUMERIC(9,2)
);

CREATE TABLE fact_inventory_snapshot (
    id                   SERIAL PRIMARY KEY,
    snapshot_date        DATE NOT NULL,
    product_id           VARCHAR(10) NOT NULL REFERENCES dim_products(product_id),
    branch_id            VARCHAR(10) NOT NULL REFERENCES dim_branches(branch_id),
    stock_quantity       INT NOT NULL CHECK (stock_quantity >= 0),
    reorder_level        INT,
    CONSTRAINT uq_inventory_snapshot UNIQUE (snapshot_date, product_id, branch_id)
);

