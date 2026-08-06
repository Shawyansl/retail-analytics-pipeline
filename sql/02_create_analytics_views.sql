-- =====================================================
-- Retail Analytics Pipeline
-- بخش ۲: Views تحلیلی (02_create_analytics_views.sql)
-- =====================================================

-- -----------------------------------------------------
-- View ۱: vw_daily_revenue
-- روند فروش روزانه: مجموع درآمد ناخالص، خالص، سود، و تعداد سفارش هر روز
-- -----------------------------------------------------
CREATE OR REPLACE VIEW vw_daily_revenue AS
SELECT
    sale_date,
    COUNT(sale_id)              AS order_count,
    SUM(quantity)                AS total_quantity_sold,
    SUM(gross_revenue)           AS total_gross_revenue,
    SUM(discount_amount)         AS total_discount,
    SUM(net_revenue)             AS total_net_revenue,
    SUM(gross_profit)            AS total_gross_profit,
    ROUND(AVG(net_revenue), 2)   AS avg_order_value
FROM fact_sales
GROUP BY sale_date
ORDER BY sale_date;


-- -----------------------------------------------------
-- View ۲: vw_product_revenue
-- درآمد هر محصول: برای پیدا کردن ۱۰ محصول برتر- -----------------------------------------------------
CREATE OR REPLACE VIEW vw_product_revenue AS
SELECT
    p.product_id,
    p.product_name,
    c.category_name,
    COUNT(s.sale_id)             AS order_count,
    SUM(s.quantity)              AS total_quantity_sold,
    SUM(s.net_revenue)           AS total_net_revenue,
    SUM(s.gross_profit)          AS total_gross_profit
FROM fact_sales s
JOIN dim_products p    ON p.product_id = s.product_id
JOIN dim_categories c  ON c.category_id = p.category_id
GROUP BY p.product_id, p.product_name, c.category_name
ORDER BY total_net_revenue DESC;


-- -----------------------------------------------------
-- View ۳: vw_branch_revenue
-- درآمد هر شعبه: برای مقایسه‌ی عملکرد شعبه‌ها
-- -----------------------------------------------------
CREATE OR REPLACE VIEW vw_branch_revenue AS
SELECT
    b.branch_id,
    b.branch_name,
    b.branch_city,
    b.sales_channel,
    COUNT(s.sale_id)             AS order_count,
    SUM(s.quantity)              AS total_quantity_sold,
    SUM(s.net_revenue)           AS total_net_revenue,
    SUM(s.gross_profit)          AS total_gross_profit,
    ROUND(AVG(s.net_revenue), 2) AS avg_order_value
FROM fact_sales s
JOIN dim_branches b ON b.branch_id = s.branch_id
GROUP BY b.branch_id, b.branch_name, b.branch_city, b.sales_channel
ORDER BY total_net_revenue DESC;


-- -----------------------------------------------------
-- View ۴: vw_category_margin
-- سودآوری هر دسته‌بندی (حاشیه‌ی سود میانگین و کل)
-- -----------------------------------------------------
CREATE OR REPLACE VIEW vw_category_margin AS
SELECT
    c.category_id,
    c.category_name,
    COUNT(s.sale_id)                  AS order_count,
    SUM(s.net_revenue)                AS total_net_revenue,
    SUM(s.gross_profit)               AS total_gross_profit,
    ROUND(
        CASE WHEN SUM(s.net_revenue) = 0 THEN 0
             ELSE SUM(s.gross_profit) / SUM(s.net_revenue) * 100
        END, 2)                       AS overall_margin_percent,
    ROUND(AVG(s.margin_percent), 2)   AS avg_margin_percent
FROM fact_sales s
JOIN dim_products p   ON p.product_id = s.product_id
JOIN dim_categories c ON c.category_id = p.category_id
GROUP BY c.category_id, c.category_name
ORDER BY total_gross_profit DESC;


-- -----------------------------------------------------
-- View ۵: vw_customer_lifetime_value
-- ارزش طول عمر مشتری (CLV): برای پیدا کردن ۱۰ مشتری برتر
-- -----------------------------------------------------
CREATE OR REPLACE VIEW vw_customer_lifetime_value AS
SELECT
    cu.customer_id,
    cu.first_name,
    cu.last_name,
    cu.email,
    cu.city,
    cu.signup_date,
    COUNT(s.sale_id)                AS total_orders,
    SUM(s.net_revenue)              AS lifetime_net_revenue,
    SUM(s.gross_profit)             AS lifetime_gross_profit,
    ROUND(AVG(s.net_revenue), 2)    AS avg_order_value,
    MAX(s.sale_date)                AS last_purchase_date
FROM fact_sales s
JOIN dim_customers cu ON cu.customer_id = s.customer_id
GROUP BY cu.customer_id, cu.first_name, cu.last_name, cu.email, cu.city, cu.signup_date
ORDER BY lifetime_net_revenue DESC;


-- -----------------------------------------------------
-- View ۶: vw_stockout_risk
-- ریسک اتمام موجودی: بر اساس آخرین اسنپ‌شات هر محصول/شعبه
-- -----------------------------------------------------
CREATE OR REPLACE VIEW vw_stockout_risk AS
WITH latest_snapshot AS (
    -- برای هر محصول در هر شعبه، فقط آخرین تاریخ اسنپ‌شات را نگه می‌داریم
    SELECT
        product_id,
        branch_id,
        MAX(snapshot_date) AS latest_date
    FROM fact_inventory_snapshot
    GROUP BY product_id, branch_id
)
SELECT
    p.product_id,
    p.product_name,
    b.branch_id,
    b.branch_name,
    inv.snapshot_date,
    inv.stock_quantity,
    inv.reorder_level,
    (inv.stock_quantity - inv.reorder_level) AS stock_surplus,
    CASE
        WHEN inv.stock_quantity <= inv.reorder_level THEN 'at_risk'
        WHEN inv.stock_quantity <= inv.reorder_level * 1.2 THEN 'watch'
        ELSE 'ok'
    END AS risk_status
FROM fact_inventory_snapshot inv
JOIN latest_snapshot ls
    ON ls.product_id = inv.product_id
    AND ls.branch_id = inv.branch_id
    AND ls.latest_date = inv.snapshot_date
JOIN dim_products p  ON p.product_id = inv.product_id
JOIN dim_branches b  ON b.branch_id = inv.branch_id
ORDER BY stock_surplus ASC;