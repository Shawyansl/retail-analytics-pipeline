"""
extract.py
read csv file and create initial profile from data
"""

import logging
import os
import pandas as pd

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler("./logs/extract.log")
formatter = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.propagate = False

REQUIRED_COLUMNS = [
    "sale_id",
    "sale_date",
    "customer_id",
    "customer_first_name",
    "customer_last_name",
    "customer_email",
    "customer_phone",
    "customer_city",
    "customer_signup_date",
    "product_id",
    "product_name",
    "category_name",
    "unit_cost",
    "unit_price",
    "branch_id",
    "branch_name",
    "branch_city",
    "sales_channel",
    "quantity",
    "discount_percent",
    "payment_method",
    "inventory_snapshot_date",
    "stock_quantity",  
    "reorder_level"
]


def extract_data(file_path:str):
    if not os.path.exists(file_path):
        logger.error(f"Input file not found: {file_path}")
        raise FileNotFoundError(f"Input file not found: {file_path}")

    try:
        df = pd.read_csv(file_path, dtype={"customer_phone": str})

    except Exception as e:
        logger.error(f"Failed to read CSV file: {e}")
        raise 

    logger.info(f"File read successfully: {file_path}")

    missing_columns = []
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            missing_columns.append(col)

    if missing_columns:
        logger.warning(f"Missing required columns: {missing_columns}")
    else:
        logger.info("All required columns are present.")

    """
    collect some information
    """ 
    n_rows, n_cols = df.shape
    logger.info(f"Row count: {n_rows:,}")
    logger.info(f"Column count: {n_cols}")
    
    null_counts = df.isnull().sum()
    columns_with_nulls = null_counts[null_counts > 0]
    if columns_with_nulls.empty:
        logger.info("Null check: no missing values found in any column.")
    else:
        logger.info(f"Null check: {len(columns_with_nulls)} column(s) contain missing values.")
        for col, count in columns_with_nulls.items():
            logger.info(f"  - {col}: {count:,} missing")
 
    duplicate_count = df.duplicated().sum()
    logger.info(f"Duplicate rows found: {duplicate_count:,}")

    describe_info = df.describe().to_string()
    logger.info(f"Basic numeric statistics:\n{describe_info}")
 
    logger.info("Data extraction completed successfully.")

    return df
       