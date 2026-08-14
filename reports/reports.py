"""
reports.py
خواندن نتایج Viewهای تحلیلی از PostgreSQL و ساخت ۵ نمودار الزامی پروژه با Matplotlib
"""
import logging
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # بدون نیاز به نمایشگر گرافیکی — برای اجرا داخل Docker ضروریه
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
from sqlalchemy import create_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/reports.log", mode="a"),
    ],
)
logger = logging.getLogger(__name__)

CHARTS_DIR = Path("reports/charts")
CHARTS_DIR.mkdir(parents=True, exist_ok=True)


def get_engine():
    """ساخت اتصال به دیتابیس با استفاده از متغیرهای محیطی (.env)"""
    user = os.getenv("POSTGRES_USER", "retail_admin")
    password = os.getenv("POSTGRES_PASSWORD")
    db = os.getenv("POSTGRES_DB", "retail_analytics")
    host = os.getenv("DB_HOST", "db")
    port = os.getenv("DB_PORT", "5432")
    conn_str = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    return create_engine(conn_str)


def format_axis_currency(ax, axis="y"):
    """فرمت اعداد محور به‌صورت خوانا (مثلاً 1,200,000 به‌جای 1200000)"""
    formatter = mticker.FuncFormatter(lambda x, _: f"{x:,.0f}")
    if axis == "y":
        ax.yaxis.set_major_formatter(formatter)
    else:
        ax.xaxis.set_major_formatter(formatter)


def chart_daily_revenue(engine):
    """نمودار ۱: روند فروش روزانه (خطی)"""
    df = pd.read_sql("SELECT sale_date, total_net_revenue FROM vw_daily_revenue ORDER BY sale_date;", engine)
    if df.empty:
        logger.warning("vw_daily_revenue خالیه — نمودار روند روزانه رد شد.")
        return

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df["sale_date"], df["total_net_revenue"], color="#2563eb", linewidth=2)
    ax.set_title("روند فروش روزانه (Net Revenue)")
    ax.set_xlabel("تاریخ")
    ax.set_ylabel("درآمد خالص")
    format_axis_currency(ax)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "daily_revenue_trend.png", dpi=150)
    plt.close(fig)
    logger.info("نمودار daily_revenue_trend.png ساخته شد.")


def chart_top_products(engine):
    """نمودار ۲: ۱۰ محصول برتر بر اساس درآمد (میله‌ای)"""
    df = pd.read_sql(
        "SELECT product_name, total_net_revenue FROM vw_product_revenue ORDER BY total_net_revenue DESC LIMIT 10;",
        engine,
    )
    if df.empty:
        logger.warning("vw_product_revenue خالیه — نمودار محصولات برتر رد شد.")
        return

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(df["product_name"][::-1], df["total_net_revenue"][::-1], color="#16a34a")
    ax.set_title("۱۰ محصول برتر بر اساس درآمد")
    ax.set_xlabel("درآمد خالص")
    format_axis_currency(ax, axis="x")
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "top_10_products.png", dpi=150)
    plt.close(fig)
    logger.info("نمودار top_10_products.png ساخته شد.")


def chart_branch_revenue(engine):
    """نمودار ۳: درآمد هر شعبه (میله‌ای)"""
    df = pd.read_sql(
        "SELECT branch_name, total_net_revenue FROM vw_branch_revenue ORDER BY total_net_revenue DESC;",
        engine,
    )
    if df.empty:
        logger.warning("vw_branch_revenue خالیه — نمودار شعبه‌ها رد شد.")
        return

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(df["branch_name"], df["total_net_revenue"], color="#f59e0b")
    ax.set_title("درآمد هر شعبه")
    ax.set_ylabel("درآمد خالص")
    format_axis_currency(ax)
    plt.xticks(rotation=45, ha="right")
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "branch_revenue.png", dpi=150)
    plt.close(fig)
    logger.info("نمودار branch_revenue.png ساخته شد.")


def chart_category_margin(engine):
    """نمودار ۴: حاشیه‌ی سود هر دسته‌بندی (میله‌ای)"""
    df = pd.read_sql(
        "SELECT category_name, overall_margin_percent FROM vw_category_margin ORDER BY overall_margin_percent DESC;",
        engine,
    )
    if df.empty:
        logger.warning("vw_category_margin خالیه — نمودار حاشیه‌ی سود رد شد.")
        return

    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ["#16a34a" if v >= 0 else "#dc2626" for v in df["overall_margin_percent"]]
    ax.bar(df["category_name"], df["overall_margin_percent"], color=colors)
    ax.set_title("حاشیه‌ی سود هر دسته‌بندی (٪)")
    ax.set_ylabel("درصد حاشیه‌ی سود")
    ax.axhline(0, color="black", linewidth=0.8)
    plt.xticks(rotation=45, ha="right")
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "category_margin.png", dpi=150)
    plt.close(fig)
    logger.info("نمودار category_margin.png ساخته شد.")


def chart_stockout_risk(engine):
    """نمودار ۵: تعداد محصولات در معرض ریسک اتمام موجودی، به تفکیک شعبه"""
    df = pd.read_sql(
        """
        SELECT branch_name, risk_status, COUNT(*) AS product_count
        FROM vw_stockout_risk
        WHERE risk_status IN ('at_risk', 'watch')
        GROUP BY branch_name, risk_status
        ORDER BY branch_name;
        """,
        engine,
    )
    if df.empty:
        logger.warning("vw_stockout_risk خالیه یا ریسکی وجود نداره — نمودار ریسک موجودی رد شد.")
        return

    pivot = df.pivot(index="branch_name", columns="risk_status", values="product_count").fillna(0)
    fig, ax = plt.subplots(figsize=(10, 5))
    pivot.plot(kind="bar", stacked=True, ax=ax, color={"at_risk": "#dc2626", "watch": "#f59e0b"})
    ax.set_title("تعداد محصولات در معرض ریسک اتمام موجودی (به تفکیک شعبه)")
    ax.set_ylabel("تعداد محصول")
    ax.set_xlabel("شعبه")
    plt.xticks(rotation=45, ha="right")
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "stockout_risk.png", dpi=150)
    plt.close(fig)
    logger.info("نمودار stockout_risk.png ساخته شد.")


def generate_all_reports():
    logger.info("شروع ساخت گزارش‌ها...")
    engine = get_engine()

    chart_daily_revenue(engine)
    chart_top_products(engine)
    chart_branch_revenue(engine)
    chart_category_margin(engine)
    chart_stockout_risk(engine)

    logger.info("ساخت گزارش‌ها به پایان رسید.")


if __name__ == "__main__":
    generate_all_reports()