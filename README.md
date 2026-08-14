# گزارش خلاصه‌ی تحلیلی — Retail Analytics Pipeline

> ⚠️ این یک **قالب** است. بخش‌های داخل `[ ]` باید بعد از اجرای موفق کامل پایپ‌لاین (با داده‌ی واقعی) با اعداد و یافته‌های واقعی پر شوند.

## ۱. خلاصه‌ی اجرایی

این گزارش نتایج تحلیل [تعداد] تراکنش فروش، در بازه‌ی زمانی [تاریخ شروع] تا [تاریخ پایان]، در [تعداد] شعبه را ارائه می‌دهد.

## ۲. یافته‌های کلیدی

### روند فروش
- مجموع درآمد خالص در کل بازه: **[مقدار] تومان**
- بیشترین فروش روزانه: **[تاریخ]** با **[مقدار]**
- روند کلی: [صعودی / نزولی / ثابت] — نمودار: `charts/daily_revenue_trend.png`

### محصولات برتر
- پرفروش‌ترین محصول: **[نام محصول]** با درآمد **[مقدار]**
- ۳ محصول برتر: [نام ۱]، [نام ۲]، [نام ۳]
- نمودار: `charts/top_10_products.png`

### عملکرد شعبه‌ها
- بهترین شعبه: **[نام شعبه]** با درآمد **[مقدار]**
- ضعیف‌ترین شعبه: **[نام شعبه]**
- نمودار: `charts/branch_revenue.png`

### سودآوری دسته‌بندی‌ها
- بیشترین حاشیه‌ی سود: دسته‌ی **[نام دسته]** با **[درصد]٪**
- کمترین حاشیه‌ی سود: دسته‌ی **[نام دسته]** با **[درصد]٪**
- نمودار: `charts/category_margin.png`

### مشتریان برتر (CLV)
- با ارزش‌ترین مشتری: **[نام]** با مجموع خرید **[مقدار]**
- نکته: [مثلاً «۲۰٪ مشتریان، ۵۰٪ درآمد را تشکیل می‌دهند» — اگر محاسبه شد]

### ریسک اتمام موجودی
- تعداد محصولات در وضعیت `at_risk`: **[عدد]**
- تعداد محصولات در وضعیت `watch`: **[عدد]**
- شعبه‌ی با بیشترین ریسک: **[نام شعبه]**
- نمودار: `charts/stockout_risk.png`

## ۳. کیفیت داده

- تعداد کل ردیف‌های خام: **[عدد]**
- تعداد ردیف‌های حذف‌شده (تکراری): **[عدد]**
- تعداد ردیف‌های Quarantine‌شده (نامعتبر): **[عدد]** — جزئیات در `data/processed/rejected_records/`
- دلایل اصلی رد شدن رکوردها: [مثلاً «quantity منفی»، «product_id نامعتبر»]

## ۴. پیشنهادهای عملیاتی

- [مثلاً: «سفارش مجدد فوری برای محصولات در وضعیت at_risk در شعبه‌ی X»]
- [مثلاً: «بررسی علت حاشیه‌ی سود پایین در دسته‌ی Y»]

## ۵. محدودیت‌های تحلیل

- این تحلیل بر پایه‌ی یک نمونه/برداشت واحد از داده است و روند بلندمدت را نشان نمی‌دهد.
- [هر محدودیت دیگری که در طول پروژه با آن مواجه شدید]

--------------------------------------------------------------------------------------------------------------------------

--------------------------------------------------------------------------------------------------------------------------

# Analytics Summary Report — Retail Analytics Pipeline

> ⚠️ This is a **template**. The sections inside `[ ]` should be filled in with actual numbers and findings after a successful full pipeline run (with real data).

## 1. Executive Summary

This report provides the results of the analysis of [number] sales transactions, from [start date] to [end date], in [number] branches.

## 2. Key Findings

### Sales Trend
- Total Net Revenue for the entire period: **[Amount] Tomans**
- Highest Daily Sales: **[Date]** with **[Amount]**
- Overall Trend: [Ascending / Descending / Flat] — Chart: `charts/daily_revenue_trend.png`

### Top Products
- Best Selling Product: **[Product Name]** with Revenue **[Amount]**
- Top 3 Products: [Name 1], [Name 2], [Name 3]
- Chart: `charts/top_10_products.png`

### Branch Performance
- Best Branch: **[Branch Name]** with Revenue **[Amount]**
- Weakest Branch: **[Branch Name]**
- Chart: `charts/branch_revenue.png`

### Category Profitability
- Highest Profit Margin: **[Category Name]** with **[Percentage]%**
- Lowest Profit Margin: Category **[Category Name]** with **[Percentage]%**
- Chart: `charts/category_margin.png`

### Top Customers (CLV)
- Most Valuable Customer: **[Name]** with Total Purchases **[Amount]**
- Note: [e.g. "20% of Customers Generate 50% of Revenue" — If Calculated]

### Out-of-Stock Risk
- Number of Products in `at_risk` Status: **[Number]**
- Number of Products in `watch` Status: **[Number]**
- Branch with the Highest Risk: **[Branch Name]**
- Chart: `charts/stockout_risk.png`

## 3. Data Quality

- Total number of raw rows: **[number]**
- Number of deleted (duplicate) rows: **[number]**
- Number of quarantined (invalid) rows: **[number]** — Details in `data/processed/rejected_records/`
- Main reasons for rejecting records: [e.g. "negative quantity", "invalid product_id"]

## 4. Actionable recommendations

- [e.g. "Immediate reorder for products in at_risk status in branch X"]
- [e.g. "Investigate the cause of low profit margin in category Y"]

## 5. Analysis limitations

- This analysis is based on a single sample/sampling of data and does not indicate a long-term trend.
- [Any other limitations you encountered during the project]