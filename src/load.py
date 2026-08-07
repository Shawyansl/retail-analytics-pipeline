"""
load.py

Loads transformed tables into PostgreSQL and saves rejected records to CSV.
"""
import logging
import pandas as pd
import psycopg2
from src.config import get_db_config


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler("./logs/load.log")
formatter = logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.propagate = False


LOAD_ORDER = [
    "dim_categories",
    "dim_customers",
    "dim_branches",
    "dim_products",
    "fact_sales",
    "fact_inventory_snapshot",
]


def get_connection(config: dict):
    try:
        return psycopg2.connect(**config)
    except psycopg2.Error as e:
        logger.error(f"Error connecting to database: {e}")
        raise


def load_table(conn, table_name: str, df: pd.DataFrame) -> None:
    # TODO: insert all rows from df into table_name using INSERT ... ON CONFLICT DO NOTHING
    #
    # Steps:
    #   1. Build the column list from df.columns  ->  e.g. "col1, col2, col3"
    #   2. Build the placeholders string          ->  e.g. "%s, %s, %s"  (one %s per column)
    #   3. Build the SQL string:
    #        INSERT INTO {table_name} ({cols}) VALUES ({placeholders}) ON CONFLICT DO NOTHING
    #   4. Convert df to a list of tuples: df.where(pd.notnull(df), None).values.tolist()
    #      (the .where(..., None) converts NaN/NaT to Python None so psycopg2 writes NULL)
    #   5. Open a cursor, call cursor.executemany(sql, rows), then conn.commit()
    #   6. Log how many rows were attempted
    table_cols = ", ".join(df.columns)
    placeholders = ", ".join(["%s"] * len(df.columns))
    sql = f"INSERT INTO {table_name} ({table_cols}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
    rows = df.where(pd.notnull(df), None).values.tolist()
    with conn.cursor() as cursor:
        cursor.executemany(sql, rows)
        conn.commit()
    logger.info(f"Attempted to load {len(rows)} rows into {table_name}.")



def save_rejected(rejected_df: pd.DataFrame, path: str = "./reports/rejected_records.csv") -> None:

    if rejected_df.empty:
        logger.info("No rejected records to save.")
    else:
        rejected_df.to_csv(path, index=False)
        logger.info(f"Saved {len(rejected_df)} rejected records to {path}.")


def load_data(tables: dict, rejected_df: pd.DataFrame, all_rejected_df: pd.DataFrame) -> None:

    save_rejected(rejected_df)
    save_rejected(all_rejected_df, "./data/raw/quality_rejected_records.csv")
    conn = get_connection(get_db_config())
    try:
        for table_name in LOAD_ORDER:
            load_table(conn, table_name, tables[table_name])
    finally:
        conn.close()
        logger.info("Database connection closed.")

