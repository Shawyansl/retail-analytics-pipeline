"""
load.py

Loads transformed tables into PostgreSQL, writes the normalized dimension and
fact tables to data/processed/ as CSV, and saves rejected records to CSV.
"""
import logging
import os
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


def truncate_tables(conn) -> None:
    table_sql = ", ".join(f'"{table_name}"' for table_name in LOAD_ORDER)

    with conn.cursor() as cur:
        cur.execute(f"TRUNCATE TABLE {table_sql} RESTART IDENTITY")

    logger.info(
        f"Truncated {len(LOAD_ORDER)} table(s) in this transaction; "
        "the previous run's rows are gone unless this transaction rolls back."
    )

def load_table(conn, table_name: str, df: pd.DataFrame) -> None:
    if df.empty:
        raise ValueError(
            f"{table_name}: received an empty DataFrame. The table was truncated at the "
            "start of this transaction, so continuing would publish an empty table."
        )

    started = perf_counter()
    column_sql = ", ".join(f'"{column}"' for column in df.columns)
    staging_table = f"stg_{table_name}"

    with conn.cursor() as cur:
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

    if skipped:
        logger.warning(
            f"{table_name}: {skipped:,} row(s) skipped on conflict even though the table "
            "was truncated at the start of this transaction -- the DataFrame carries "
            "duplicate keys that the quality checks did not remove."
        )



def save_processed_tables(
    tables: dict[str, pd.DataFrame],
    out_dir: str = "./data/processed",
) -> None:

    os.makedirs(out_dir, exist_ok=True)

    missing = [name for name in LOAD_ORDER if name not in tables]
    if missing:
        raise KeyError(
            f"save_processed_tables: no DataFrame supplied for {missing}. "
            "All six normalized tables are required deliverables."
        )

    unexpected = [name for name in tables if name not in LOAD_ORDER]
    if unexpected:
        logger.warning(
            f"save_processed_tables: ignoring unexpected table(s) {unexpected}; "
            f"only the six tables in LOAD_ORDER are written."
        )

    total_bytes = 0

    # LOAD_ORDER rather than dict order, so the log reads the same way every run.
    for table_name in LOAD_ORDER:
        df = tables[table_name]
        path = os.path.join(out_dir, f"{table_name}.csv")

        started = perf_counter()
        df.to_csv(path, index=False, na_rep="", date_format="%Y-%m-%d")
        elapsed = perf_counter() - started

        size = os.path.getsize(path)
        total_bytes += size

        if df.empty:
            # Header-only file: written on purpose so the deliverable exists and the
            # emptiness is visible, but it means an upstream step produced nothing.
            logger.warning(
                f"{table_name}: wrote a header-only {path} -- the DataFrame was empty."
            )
        else:
            logger.info(
                f"{table_name}: wrote {len(df):,} row(s), {len(df.columns)} column(s) "
                f"to {path} ({size / 1024 / 1024:.1f} MB) in {elapsed:.2f}s."
            )

    logger.info(
        f"Wrote {len(LOAD_ORDER)} processed CSV file(s) to {out_dir} "
        f"({total_bytes / 1024 / 1024:.1f} MB total)."
    )


def save_rejected(rejected_df: pd.DataFrame, path: str = "./data/processed/rejected_records/rejected_records.csv") -> None:

    if rejected_df.empty:
        logger.info("No rejected records to save.")
    else:
        rejected_df.to_csv(path, index=False)
        logger.info(f"Saved {len(rejected_df)} rejected records to {path}.")


def load_data(tables: dict, rejected_df: pd.DataFrame, all_rejected_df: pd.DataFrame, load_path1, load_path2,
              processed_dir: str = "./data/processed") -> None:

    save_processed_tables(tables, processed_dir)
    save_rejected(rejected_df, load_path1)
    save_rejected(all_rejected_df, load_path2)
    conn = get_connection(get_db_config())
    try:
        # Same transaction as the loads below, so a failure anywhere restores the old rows.
        truncate_tables(conn)

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
