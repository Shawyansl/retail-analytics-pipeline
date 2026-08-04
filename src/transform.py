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

    rules = {
        "invalid_sale_date": df['sale_date'].isna(),
        "discount_out_of_range": (df['discount_percent'] < 0) | (df['discount_percent'] > 100),
        "invalid_quantity": df['quantity'] <= 0,
        "duplicate_sale_id": df['sale_id'].duplicated(keep=False)
    }

    invalid_mask = pd.Series(False, index=df.index)

    for rule_name, rule_mask in rules.items():
        invalid_mask |= rule_mask

    rejected_df = df.loc[invalid_mask].copy()
    clean_df = df.loc[~invalid_mask].copy()

    rejected_df['rejection_reason'] = None
    for rule_name, rule_mask in rules.items():
        rejected_df.loc[rule_mask, 'rejection_reason'] = rule_name


    logger.info("Rejected sales summary:")

    for reason, mask in rules.items():
        logger.info(f"{reason}: {int(mask.sum())}")

    logger.info(f"Total rejected: {len(rejected_df)}")
    logger.info(f"Remaining clean rows: {len(clean_df)}")

    return clean_df, rejected_df

def resolve_customer_email_conflicts(df: pd.DataFrame) -> pd.DataFrame:

    email_counts_before = df.groupby('customer_id')['customer_email'].nunique()
    n_conflicts = int((email_counts_before > 1).sum())

    if n_conflicts == 0:
        logger.info("No customer_id/email conflicts found.")
        return df

    majority_email = df.groupby('customer_id')['customer_email'].agg(
        lambda x: x.value_counts().idxmax() #num of repeat , return name of email that has max repeat
    )
    df['customer_email'] = df['customer_id'].map(majority_email)

    logger.info(
        f"Resolved {n_conflicts} customer_id(s) with conflicting emails "
        f"using majority-vote strategy."
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

"""
This is main transformation function that applies all the transformations to the DataFrame.
"""


def transform_data(df:pd.DataFrame) -> pd.DataFrame:
    df = standardize_column_names(df)
    df = strip_whitespace_from_text_columns(df)
    df = normalize_city_category_names(df)
    df = parse_dates(df, DATE_COLUMNS)
    df = remove_duplicates(df)

    clean_df, rejected_df = quarantine_invalid_sales(df)
    clean_df = resolve_customer_email_conflicts(clean_df)
    clean_df = generate_category_keys(clean_df)

    clean_df = fix_negative_prices(clean_df)
    clean_df = fill_missing_product_prices(clean_df)

    logger.info("Transformation completed successfully.")

    return clean_df, rejected_df