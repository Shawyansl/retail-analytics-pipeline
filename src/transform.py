"""
transform.py

Profile/Clean
Pandas/NumPy
Normalize into Tables
"""
import logging
import pandas as pd
import numpy as np


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler("./logs/transform.log")
formatter = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.propagate = False


DATE_COLUMNS = [
"sale_date",
"customer_signup_date",
"inventory_snapshot_date"
]

def standardize_column_names(df:pd.DataFrame) -> pd.DataFrame:
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(r"[()]", "", regex=True)
        .str.replace(r"[\s-]+", "_", regex=True)
    )
    logger.info("Column names standardized successfully.")
    return df

def strip_whitespace_from_text_columns(df:pd.DataFrame) -> pd.DataFrame:
    text_columns = df.select_dtypes(include=["object", "string"]).columns
    for col in text_columns:
        df[col] = df[col].str.strip()
    logger.info("Whitespace stripped from text columns successfully.")
    return df

def normalize_city_category_names(df:pd.DataFrame) -> pd.DataFrame:
    if 'payment_method' in df.columns:
        df['payment_method'] = df['payment_method'].str.lower()
    if 'product_name' in df.columns:
        df['product_name'] = df['product_name'].str.title()
    if 'customer_city' in df.columns:
        df['customer_city'] = df['customer_city'].str.title()
    if 'branch_city' in df.columns:
        df['branch_city'] = df['branch_city'].str.title()
    if 'category_name' in df.columns:
        df['category_name'] = df['category_name'].str.title()
    logger.info("City and category names normalized successfully.")
    return df

def parse_dates(df: pd.DataFrame, date_columns: list[str]) -> pd.DataFrame:
    for col in date_columns:
        if col in df.columns:
            before_invalid = df[col].isna().sum()

            df[col] = parse_mixed_format_dates(df[col], col_name=col)


            after_invalid = df[col].isna().sum()

            logger.info(
                f"{col}: Parsed to datetime. Invalid dates before: {before_invalid}, after: {after_invalid}"
            )
        else:
            logger.warning(f"Column {col} not found in DataFrame.")
    return df

def parse_mixed_format_dates(date_series: pd.Series, col_name: str) -> pd.Series:
    s = date_series.fillna("").astype(str).str.strip()

    pattern_ymd_slash = s.str.match(r'^\d{4}/\d{2}/\d{2}$')
    pattern_ymd_dash = s.str.match(r'^\d{4}-\d{2}-\d{2}$')
    pattern_mdy_slash = s.str.match(r'^\d{2}/\d{2}/\d{4}$')
    pattern_dmy_dash = s.str.match(r'^\d{2}-\d{2}-\d{4}$')
 
    result = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
 
    result[pattern_ymd_slash] = pd.to_datetime(s[pattern_ymd_slash], format="%Y/%m/%d", errors="coerce")
    result[pattern_ymd_dash] = pd.to_datetime(s[pattern_ymd_dash], format="%Y-%m-%d", errors="coerce")
    result[pattern_mdy_slash] = pd.to_datetime(s[pattern_mdy_slash], format="%m/%d/%Y", errors="coerce")
    result[pattern_dmy_dash] = pd.to_datetime(s[pattern_dmy_dash], format="%d-%m-%Y", errors="coerce")
 
    matched = pattern_ymd_slash | pattern_ymd_dash | pattern_mdy_slash | pattern_dmy_dash
    n_unmatched = int((~matched).sum())
    if n_unmatched > 0:
        logger.warning(f"{col_name}: {n_unmatched} row(s) did not match any known date pattern -> quarantined as NaT")
 
    n_parsed_but_invalid = int((matched & result.isna()).sum())
    if n_parsed_but_invalid > 0:
        logger.warning(f"{col_name}: {n_parsed_but_invalid} row(s) matched a pattern but had an invalid calendar date (e.g. month 13) -> NaT")
 
    return result

def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    before_count = len(df)
    df = df.drop_duplicates()
    after_count = len(df)
    logger.info(f"Removed {before_count - after_count} duplicate rows. Remaining rows: {after_count}.")
    return df

def quarantine_invalid_sales(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    NOTE: unlike the initial plan (which split quarantine logic between
    transform.py and quality.py per the project spec), this project
    consolidates all row-level rejection rules here in transform.py
    for simplicity. quality.py will focus on cross-table checks
    (foreign key validity, dimension uniqueness) instead.
    NaN is spelled out in every numeric rule on purpose. A comparison against NaN is
    False, so `df['quantity'] <= 0` lets a null quantity through -- and the DDL declares
    `quantity INT NOT NULL CHECK (quantity > 0)`. ON CONFLICT DO NOTHING only absorbs
    unique-constraint violations, not NOT NULL or CHECK, so one null here aborts the
    whole million-row load at the very end.
    """
    rules = {
        "invalid_sale_date": df['sale_date'].isna(),
        "missing_discount": df['discount_percent'].isna(),
        "discount_out_of_range": (df['discount_percent'] < 0) | (df['discount_percent'] > 100),
        "missing_quantity": df['quantity'].isna(),
        "invalid_quantity": df['quantity'] <= 0,
        "duplicate_sale_id": df['sale_id'].duplicated(keep=False),
        "missing_sale_id": df['sale_id'].isna(),
        "missing_stock_quantity": df['stock_quantity'].isna(),
        "invalid_stock_quantity": df['stock_quantity'] < 0,
    }

    invalid_mask = pd.Series(False, index=df.index)

    for rule_name, rule_mask in rules.items():
        invalid_mask |= rule_mask

    rejected_df = df.loc[invalid_mask].copy()
    clean_df = df.loc[~invalid_mask].copy()

    # A row can break several rules at once, and a single overwritten column would report
    # only whichever rule happens to come last in `rules`. Join them so the CSV shows the
    # full reason, and keep a count so the per-reason numbers below stay reconcilable.
    reason_parts = pd.Series("", index=rejected_df.index)
    for rule_name, rule_mask in rules.items():
        hits = rule_mask.reindex(rejected_df.index, fill_value=False)
        reason_parts[hits] = reason_parts[hits] + f"{rule_name};"

    rejected_df['rejection_reason'] = reason_parts.str.rstrip(";")

    logger.info("Rejected sales summary:")

    # Counted over rejected_df, not df: these are the rows actually removed. Because a row
    # can appear under more than one reason, the numbers below can sum to more than the
    # total -- that is overlap, not double-rejection.
    for reason, mask in rules.items():
        n_hit = int(mask.reindex(rejected_df.index, fill_value=False).sum())
        logger.info(f"{reason}: {n_hit}")

    n_multi = int(rejected_df['rejection_reason'].str.contains(";").sum())
    if n_multi > 0:
        logger.info(f"({n_multi} of the rejected rows broke more than one rule)")

    logger.info(f"Total rejected: {len(rejected_df)}")
    logger.info(f"Remaining clean rows: {len(clean_df)}")

    return clean_df, rejected_df

def resolve_customer_email_conflicts(df: pd.DataFrame) -> pd.DataFrame:
    """
    Give every customer_id a single email: the one appearing on most of its rows.

    Side effect worth knowing about: because the winning email is mapped back onto
    every row of the customer, rows whose email was null are filled in from the
    customer's other rows. That is intentional (the same trick as
    resolve_customer_phone_conflicts), so the count is logged rather than left silent.

    A customer whose every row has a null email keeps its null -- there is no email
    to vote for -- and does not abort the run.
    """
    email_counts_before = df.groupby('customer_id')['customer_email'].nunique()
    n_conflicts = int((email_counts_before > 1).sum())

    if n_conflicts == 0:
        # Note this fast path also skips the null-filling described above. Harmless
        # only because no conflicts means no email disagreements to propagate.
        logger.info("No customer_id/email conflicts found.")
        return df

    nulls_before = int(df['customer_email'].isna().sum())

    # Tally votes instead of aggregating with a per-group lambda.
    #
    # The previous version was `.agg(lambda x: x.value_counts().idxmax())`, which
    # raised "ValueError: attempt to get argmax of an empty sequence" for any
    # customer_id whose every row had a null email: value_counts() drops nulls, so
    # that group's tally is empty and idxmax() has nothing to choose. The
    # n_conflicts guard above does not protect against it, because agg runs over
    # every customer, not just the conflicting ones -- one all-null customer
    # anywhere in the file killed the whole run.
    #
    # Dropping nulls before the groupby means such a customer never enters the
    # tally at all; map() below then finds no key for it and leaves its email NaN.
    # Selecting the two columns first keeps this off the full 24-column frame.
    votes = (
        df.loc[df['customer_email'].notna(), ['customer_id', 'customer_email']]
        .groupby(['customer_id', 'customer_email'], sort=False)
        .size()
        .reset_index(name='n_rows')
    )

    # sort=False above leaves votes in order of first appearance, and mergesort is
    # stable, so a tie is broken by whichever email was seen first in the file.
    # The default quicksort is not stable, which would leave the winner of a tie up
    # to sort internals -- two runs over the same input could disagree.
    votes = votes.sort_values('n_rows', ascending=False, kind='mergesort')

    tied = votes.groupby('customer_id')['n_rows'].transform('max').eq(votes['n_rows'])
    n_tied = int((votes.loc[tied, 'customer_id'].value_counts() > 1).sum())

    majority_email = (
        votes.drop_duplicates('customer_id')
        .set_index('customer_id')['customer_email']
    )
    df['customer_email'] = df['customer_id'].map(majority_email)

    logger.info(
        f"Resolved {n_conflicts} customer_id(s) with conflicting emails "
        f"using majority-vote strategy."
    )

    if n_tied:
        # A tie means majority vote could not actually decide. The pick is stable
        # but arbitrary, so say so rather than presenting it as a resolved conflict.
        logger.warning(
            f"{n_tied} customer_id(s) had two or more emails tied on the same row "
            "count; kept the one seen first in the file."
        )

    nulls_after = int(df['customer_email'].isna().sum())
    if nulls_before:
        logger.info(
            f"Filled {nulls_before - nulls_after} null email(s) from the same "
            f"customer's other rows; {nulls_after} row(s) had no email anywhere "
            "for their customer_id and stay null."
        )

    return df

def resolve_customer_phone_conflicts(df: pd.DataFrame) -> pd.DataFrame:

    before_null = df['customer_phone'].isna().sum()

    # For each customer_id, get one non-null phone value if one exists
    known_phone = (
        df.dropna(subset=['customer_phone'])
        .drop_duplicates(subset=['customer_id'])
        .set_index('customer_id')['customer_phone']
    )

    missing_mask = df['customer_phone'].isna()
    df.loc[missing_mask, 'customer_phone'] = df.loc[missing_mask, 'customer_id'].map(known_phone)

    after_null = df['customer_phone'].isna().sum()

    logger.info(
        f"customer_phone: filled {before_null - after_null} row(s) from another "
        f"row of the same customer_id; {after_null} row(s) remain null "
        f"(no valid phone found anywhere for that customer)."
    )

    return df
def generate_category_keys(df: pd.DataFrame) -> pd.DataFrame:

    unique_categories = sorted(df['category_name'].dropna().unique())
    category_id_map = {name: f"CAT{i:03d}" for i, name in enumerate(unique_categories, start=1)}
    df['category_id'] = df['category_name'].map(category_id_map)
    logger.info(f"Generated category_id for {len(unique_categories)} unique categories.")
    return df

def fix_negative_prices(df: pd.DataFrame) -> pd.DataFrame:

    for col in ['unit_cost', 'unit_price']:

        negative_mask = df[col] < 0
        negative_count = int(negative_mask.sum())

        if negative_count == 0:
            logger.info(f"{col}: no negative values found")
            continue

        # Build reference price only from healthy positive rows
        ref_prices = (
            df[df[col] > 0]
            .groupby('product_id')[col]
            .median()
        )

        negative_abs_values = df.loc[negative_mask, col].abs()

        product_reference = (
            df.loc[negative_mask, 'product_id']
            .map(ref_prices)
        )

        # Check if negative value is just sign-flipped
        verified_mask = negative_abs_values.eq(product_reference)

        verified_count = int(verified_mask.sum())
        rejected_count = negative_count - verified_count

        logger.info(
            f"{col}: "
            f"negative={negative_count}, "
            f"verified_fixed={verified_count}, "
            f"rejected={rejected_count}"
        )

        # Convert verified sign-flips
        verified_indexes = df.loc[negative_mask].index[verified_mask]

        df.loc[verified_indexes, col] = df.loc[verified_indexes, col].abs()

        # Reject suspicious negatives
        rejected_indexes = df.loc[negative_mask].index[~verified_mask]

        if len(rejected_indexes) > 0:
            logger.warning(
                f"{col}: setting {len(rejected_indexes)} "
                "unverified negative values to NaN"
            )

            df.loc[rejected_indexes, col] = np.nan
    return df


def fill_missing_product_prices(df: pd.DataFrame) -> pd.DataFrame:

    for col in ['unit_cost', 'unit_price']:

        before = df[col].isna().sum()

        product_avg = (
            df.groupby('product_id')[col]
            .median()
        )

        df[col] = df[col].fillna(df['product_id'].map(product_avg))


        after = df[col].isna().sum()

        logger.info(
            f"{col}: "
            f"filled={before-after}, "
            f"remaining={after}"
        )

    return df

def calculate_sales_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df["gross_revenue"] = df["quantity"] * df["unit_price"]
    df["discount_amount"] = df["gross_revenue"] * (df["discount_percent"] / 100)
    df["net_revenue"] = df["gross_revenue"] - df["discount_amount"]
    df["gross_profit"] = df["net_revenue"] - (df["quantity"] * df["unit_cost"])
    df["margin_percent"] = np.where(
        df["net_revenue"] != 0,
        (df["gross_profit"] / df["net_revenue"]) * 100,
        np.nan
    )

    metric_columns = [
        "gross_revenue",
        "discount_amount",
        "net_revenue",
        "gross_profit",
        "margin_percent",
    ]
    df[metric_columns] = df[metric_columns].round(2)

    n_incomplete = int(df[metric_columns].isna().any(axis=1).sum())
    if n_incomplete > 0:
        logger.warning(
            f"metrics: {n_incomplete} row(s) have NaN in a derived column "
            "-> price repair left a gap, downstream sums will silently undercount"
        )
    else:
        logger.info("metrics: all derived columns computed, no NaN rows")

    total_gross = df["gross_revenue"].sum()
    total_net = df["net_revenue"].sum()
    total_profit = df["gross_profit"].sum()

    logger.info(
        "metrics totals: "
        f"gross_revenue={total_gross:,.2f}, "
        f"discount_amount={df['discount_amount'].sum():,.2f}, "
        f"net_revenue={total_net:,.2f}, "
        f"gross_profit={total_profit:,.2f}, "
        f"overall_margin_percent={total_profit / total_net * 100:,.2f}"
    )

    return df


def split_into_dimensions_and_facts(df: pd.DataFrame) -> dict[str, pd.DataFrame]:

    # -- dim_customers --
    #   customer_id, first_name, last_name, email, phone, city, signup_date
    dim_customers = (
        df[
            [
                "customer_id",
                "customer_first_name",
                "customer_last_name",
                "customer_email",
                "customer_phone",
                "customer_city",
                "customer_signup_date",
            ]
        ]
        .drop_duplicates()
        .rename(
            columns={
                "customer_first_name": "first_name",
                "customer_last_name": "last_name",
                "customer_email": "email",
                "customer_phone": "phone",
                "customer_city": "city",
                "customer_signup_date": "signup_date",
            }
        )
        .sort_values("customer_id")
        .reset_index(drop=True)
    )
    # -- dim_categories --
    #   category_id, category_name (category_id already built by
    #   generate_category_keys; nothing else to do)
    dim_categories = (
        df[["category_id", "category_name"]]
        .drop_duplicates()
        .sort_values("category_id")
        .reset_index(drop=True)
    )

    # -- dim_products --
    #   product_id, product_name, category_id, unit_cost, unit_price
    #   Links to dim_categories via category_id, NOT category_name --
    #   the DDL has a foreign key on it.
    dim_products = (
        df[
            [
                "product_id",
                "product_name",
                "category_id",
                "unit_cost",
                "unit_price",
            ]
        ]
        .drop_duplicates()
        .sort_values("product_id")
        .reset_index(drop=True)
    )

    # -- dim_branches --
    #   branch_id, branch_name, branch_city, sales_channel
    dim_branches = (
        df[
            [
                "branch_id",
                "branch_name",
                "branch_city",
                "sales_channel",
            ]
        ]
        .drop_duplicates()
        .sort_values("branch_id")
        .reset_index(drop=True)
    )

    # -- fact_sales (one row per sale) --
    #   sale_id, sale_date, customer_id, product_id, branch_id, quantity,
    #   discount_percent, payment_method, and the 5 metric columns.
    #   sale_id is already unique (quarantine_invalid_sales dropped the dupes).
    fact_sales = (
        df[
            [
                "sale_id",
                "sale_date",
                "customer_id",
                "product_id",
                "branch_id",
                "quantity",
                "discount_percent",
                "payment_method",
                "gross_revenue",
                "discount_amount",
                "net_revenue",
                "gross_profit",
                "margin_percent",
            ]
        ]
        .sort_values("sale_id")
        .reset_index(drop=True)
    )


    inventory_keys = ["inventory_snapshot_date", "product_id", "branch_id"]
    inventory = df[inventory_keys + ["sale_date", "sale_id", "stock_quantity", "reorder_level"]]

    # groupby silently drops rows with a NaN/NaT key, so count them before it happens
    n_unkeyed = int(inventory[inventory_keys].isna().any(axis=1).sum())
    if n_unkeyed > 0:
        logger.warning(
            f"fact_inventory_snapshot: dropping {n_unkeyed} row(s) with a missing "
            "snapshot_date/product_id/branch_id -- cannot be keyed"
        )
        
        inventory = inventory.dropna(subset=inventory_keys)

    inventory = inventory.sort_values(["sale_date", "sale_id"])

    rows_before = len(inventory)
    inventory = (
        inventory
        .groupby(inventory_keys, as_index=False)[["stock_quantity", "reorder_level"]]
        .last()
    )
    inventory[["stock_quantity", "reorder_level"]] = (
        inventory[["stock_quantity", "reorder_level"]].round().astype("Int64")
    )
    logger.info(
        f"fact_inventory_snapshot: collapsed {rows_before - len(inventory)} "
        f"conflicting row(s) into {len(inventory)} unique triples "
        f"(kept the row with the latest sale_date/sale_id per triple)"
    )

    fact_inventory_snapshot = (
        inventory
        .rename(columns={"inventory_snapshot_date": "snapshot_date"})
        .sort_values(["snapshot_date", "product_id", "branch_id"])
        .reset_index(drop=True)
    )

    tables = {
        "dim_customers": dim_customers,
        "dim_categories": dim_categories,
        "dim_products": dim_products,
        "dim_branches": dim_branches,
        "fact_sales": fact_sales,
        "fact_inventory_snapshot": fact_inventory_snapshot,
    }

    n_dup_sale_ids = int(fact_sales["sale_id"].duplicated().sum())
    if n_dup_sale_ids > 0:
        logger.error(
            f"fact_sales: {n_dup_sale_ids} duplicate sale_id(s) survived quarantine "
            "-> PRIMARY KEY violation on load"
        )

    for table_name, table_df in tables.items():
        logger.info(f"{table_name}: {len(table_df)} rows, {len(table_df.columns)} columns")

    return tables


"""
This is main transformation function that applies all the transformations to the DataFrame.
"""


def transform_data(df:pd.DataFrame) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    df = standardize_column_names(df)
    df = strip_whitespace_from_text_columns(df)
    df = normalize_city_category_names(df)
    df = parse_dates(df, DATE_COLUMNS)
    df = remove_duplicates(df)

    clean_df, rejected_df = quarantine_invalid_sales(df)
    clean_df = resolve_customer_email_conflicts(clean_df)
    clean_df = resolve_customer_phone_conflicts(clean_df)
    clean_df = generate_category_keys(clean_df)

    clean_df = fix_negative_prices(clean_df)
    clean_df = fill_missing_product_prices(clean_df)
    clean_df = calculate_sales_metrics(clean_df)

    tables = split_into_dimensions_and_facts(clean_df)

    logger.info("Transformation completed successfully.")

    return tables, rejected_df