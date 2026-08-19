"""
load.py

Loads transformed tables into PostgreSQL and saves rejected records to CSV.
"""
import logging
import pandas as pd
import psycopg2
from config import get_db_config
from io import StringIO
from time import perf_counter


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


CHUNK_SIZE = 100_000


def load_table(conn, table_name: str, df: pd.DataFrame) -> None:
    """
    Bulk-load df into table_name via  COPY -> TEMP staging -> INSERT ... SELECT.

    The staging table deliberately carries no constraints, no indexes and no defaults,
    so the per-row cost of unique-index probes and FK checks is deferred to the single
    set-at-a-time INSERT ... SELECT at the end instead of being paid a million times.

    All tables are loaded in the transaction managed by load_data(). The staging table
    is created with ON COMMIT DROP and is removed after the final commit or rollback.

    Replaces an executemany() loop that ran at ~2,360 rows/s on fact_sales
    (997,968 rows / 423 s) and ~1,370 rows/s on fact_inventory_snapshot
    (975,478 rows / 713 s), measured 2026-08-19.
    """
    if df.empty:
        logger.warning(
            f"{table_name}: received an empty DataFrame -- nothing to load. "
            "Something upstream probably went wrong."
        )
        return

    started = perf_counter()

    # Build the column list once and reuse it for COPY and for INSERT ... SELECT, so the
    # two sides can never drift out of order. Quoted to survive any odd identifier.
    column_sql = ", ".join(f'"{column}"' for column in df.columns)
    staging_table = f"stg_{table_name}"

    with conn.cursor() as cur:
        # CTAS with WITH NO DATA copies column names and types only -- no PK, no FK, no
        # UNIQUE, no NOT NULL, no SERIAL default. Note this also means the `id` column of
        # fact_inventory_snapshot is simply absent here, because df does not carry it.
        cur.execute(
            f'CREATE TEMP TABLE "{staging_table}" ON COMMIT DROP AS '
            f'SELECT {column_sql} FROM "{table_name}" WITH NO DATA'
        )

        # FORMAT CSV lets pandas do the quoting/escaping. NULL '' matches to_csv's
        # na_rep="" so NaN / NaT / pd.NA all arrive as real SQL NULL.
        copy_sql = (
            f'COPY "{staging_table}" ({column_sql}) '
            f"FROM STDIN WITH (FORMAT CSV, NULL '')"
        )

        # Chunked so we never hold the whole table as one giant Python string.
        for start in range(0, len(df), CHUNK_SIZE):
            buffer = StringIO()
            df.iloc[start:start + CHUNK_SIZE].to_csv(
                buffer, index=False, header=False, na_rep=""
            )
            buffer.seek(0)
            cur.copy_expert(copy_sql, buffer)

        cur.execute(
            f'INSERT INTO "{table_name}" ({column_sql}) '
            f'SELECT {column_sql} FROM "{staging_table}" '
            "ON CONFLICT DO NOTHING"
        )
        # For INSERT ... ON CONFLICT DO NOTHING, rowcount is the number of rows that were
        # actually written -- conflicting rows are not counted. This is the only honest
        # source for "how many landed".
        inserted = cur.rowcount


    elapsed = perf_counter() - started
    skipped = len(df) - inserted
    rate = len(df) / elapsed if elapsed > 0 else 0.0
    logger.info(
        f"{table_name}: staged {len(df):,} row(s), inserted {inserted:,}, "
        f"skipped {skipped:,} on conflict, in {elapsed:.2f}s "
        f"({rate:,.0f} rows/s); awaiting final commit."
    )



def save_rejected(rejected_df: pd.DataFrame, path: str = "./data/processed/rejected_records/rejected_records.csv") -> None:

    if rejected_df.empty:
        logger.info("No rejected records to save.")
    else:
        rejected_df.to_csv(path, index=False)
        logger.info(f"Saved {len(rejected_df)} rejected records to {path}.")


def load_data(tables: dict, rejected_df: pd.DataFrame, all_rejected_df: pd.DataFrame, load_path1, load_path2) -> None:

    save_rejected(rejected_df, load_path1)
    save_rejected(all_rejected_df, load_path2)
    conn = get_connection(get_db_config())
    try:
        for table_name in LOAD_ORDER:
            load_table(conn, table_name, tables[table_name])

        conn.commit()
        logger.info("All tables committed successfully.")

    except Exception:
        conn.rollback()
        logger.exception("Load failed; all database changes were rolled back.")
        raise

    finally:
        conn.close()
        logger.info("Database connection closed.")
