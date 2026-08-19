-- =====================================================
-- Retail Analytics Pipeline
-- بخش ۳: کوئری‌های تحلیلی نهایی (03_analysis_queries.sql)
-- این فایل روی Viewهای ساخته‌شده در 02_create_analytics_views.sql اجرا می‌شود
-- =====================================================

-- -----------------------------------------------------
-- کوئری ۱: روند فروش روزانه (Daily Revenue Trend)
-- شامل رشد/افت نسبت به روز قبل با LAG()
-- -----------------------------------------------------
SELECT
    sale_date,
    order_count,
    total_net_revenue,
    total_gross_profit,
    avg_order_value,
    total_net_revenue - LAG(total_net_revenue) OVER (ORDER BY sale_date) AS revenue_change_from_prev_day
FROM vw_daily_revenue
ORDER BY sale_date;


-- -----------------------------------------------------
-- کوئری ۲: ۱۰ محصول برتر بر اساس درآمد
-- -----------------------------------------------------
SELECT
    product_id,
    product_name,
    category_name,
    total_quantity_sold,
    total_net_revenue,
    total_gross_profit
FROM vw_product_revenue
ORDER BY total_net_revenue DESC
LIMIT 10;


-- -----------------------------------------------------
-- کوئری ۳: عملکرد شعبه‌ها به ترتیب درآمد
-- به همراه رتبه (RANK) برای مقایسه‌ی سریع
-- -----------------------------------------------------
SELECT
    branch_id,
    branch_name,
    branch_city,
    sales_channel,
    order_count,
    total_net_revenue,
    total_gross_profit,
    RANK() OVER (ORDER BY total_net_revenue DESC) AS revenue_rank
FROM vw_branch_revenue
ORDER BY revenue_rank;


-- -----------------------------------------------------
-- کوئری ۴: سودآوری هر دسته‌بندی
-- فقط دسته‌هایی که حداقل سود مثبت داشته‌اند
-- -----------------------------------------------------
SELECT
    category_id,
    category_name,
    order_count,
    total_net_revenue,
    total_gross_profit,
    overall_margin_percent,
    avg_margin_percent
FROM vw_category_margin
WHERE total_gross_profit > 0
ORDER BY overall_margin_percent DESC;


-- -----------------------------------------------------
-- کوئری ۵: ۱۰ مشتری برتر بر اساس ارزش طول عمر (CLV)
-- -----------------------------------------------------
SELECT
    customer_id,
    first_name || ' ' || last_name AS full_name,
    city,
    total_orders,
    lifetime_net_revenue,
    lifetime_gross_profit,
    avg_order_value,
    last_purchase_date
FROM vw_customer_lifetime_value
ORDER BY lifetime_net_revenue DESC
LIMIT 10;


-- -----------------------------------------------------
-- کوئری ۶: گزارش ریسک اتمام موجودی
-- فقط محصولاتی که در وضعیت "at_risk" یا "watch" هستند
-- -----------------------------------------------------
SELECT
    product_id,
    product_name,
    branch_id,
    branch_name,
    snapshot_date,
    stock_quantity,
    reorder_level,
    stock_surplus,
    risk_status
FROM vw_stockout_risk
WHERE risk_status IN ('at_risk', 'watch')
ORDER BY stock_surplus ASC;


-- -----------------------------------------------------
-- کوئری ۷ (اضافی): خلاصه‌ی کلی کسب‌وکار در یک نگاه
-- ترکیب چند معیار کلیدی برای گزارش مدیریتی
-- -----------------------------------------------------
SELECT
    (SELECT SUM(total_net_revenue) FROM vw_daily_revenue)                       AS total_net_revenue_all_time,
    (SELECT SUM(total_gross_profit) FROM vw_daily_revenue)                      AS total_gross_profit_all_time,
    (SELECT COUNT(*) FROM vw_stockout_risk WHERE risk_status = 'at_risk')       AS products_at_risk_count,
    (SELECT product_name FROM vw_product_revenue ORDER BY total_net_revenue DESC LIMIT 1) AS best_selling_product,
    (SELECT branch_name FROM vw_branch_revenue ORDER BY total_net_revenue DESC LIMIT 1)   AS top_branch;
