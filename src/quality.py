import logging
import pandas as pd

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler("./logs/quality.log")
formatter = logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.propagate = False


def check_dimension_uniqueness(tables: dict) -> tuple[list[dict], pd.DataFrame]:
    results = []
    rejected = []

    dims_to_check = {
        "dim_customers":  "customer_id",
        "dim_products":   "product_id",
        "dim_branches":   "branch_id",
        "dim_categories": "category_id",
    }

    for table_name, pk_col in dims_to_check.items():
        df = tables[table_name]

        n_issues = int(df[pk_col].duplicated().sum())

        my_dict = {
            "check": f"Uniqueness of {pk_col} in {table_name}",
            "passed": n_issues == 0,
            "issues": n_issues,
        }

        if my_dict["passed"]:
            logger.info(f"Check passed: {my_dict['check']}")
        else:
            logger.warning(f"Check failed: {my_dict['check']} - Issues: {n_issues}")

        results.append(my_dict)

        # keep="first": drop only the surplus copies, never the whole key. A dimension row
        #t duplicates when a descriptive attribute drifts across the source rows for one id
        # (a product's unit_price changes, a customer moves ciy) -- dropping every copy
        # would delete the key from the dimension, and check_foreign_keys would then delete
        # every fact row that references it. Losing an attribute revision is recoverable;
        # losing the entity plus all its facts is not.
        surplus_mask = df[pk_col].duplicated(keep="first")
        if surplus_mask.any():
            rejected_df = df.loc[surplus_mask].copy()
            rejected_df["table_name"] = table_name
            rejected_df["issue"] = (
                f"Surplus row for duplicate {pk_col}; kept the first occurrence"
            )
            rejected.append(rejected_df)
            logger.warning(
                f"{table_name}: kept the first row for {n_issues} duplicated {pk_col}(s) "
                f"and quarantined {int(surplus_mask.sum())} surplus row(s); the key itself "
                "stays in the dimension so its facts survive."
            )

        tables[table_name] = df.loc[~surplus_mask].copy()

    rejected_df = pd.concat(rejected, ignore_index=True) if rejected else pd.DataFrame()

    return results, rejected_df


def check_fact_pk(tables: dict) -> tuple[list[dict], pd.DataFrame]:
    results = []
    rejected = []

    facts_to_check = {
        "fact_sales":              ["sale_id"],
        "fact_inventory_snapshot": ["snapshot_date", "product_id", "branch_id"],
    }

    for table_name, pk_cols in facts_to_check.items():
        df = tables[table_name]
        n_issues = int(df.duplicated(subset=pk_cols).sum())

        my_dict = {
            "check": f"Uniqueness of {', '.join(pk_cols)} in {table_name}",
            "passed": n_issues == 0,
            "issues": n_issues,
        }

        if my_dict["passed"]:
            logger.info(f"Check passed: {my_dict['check']}")
        else:
            logger.warning(f"Check failed: {my_dict['check']} - Issues: {n_issues}")

        results.append(my_dict)

        # keep="first" here as well, but for a different reason than the dimensions above:
        # a fact row IS the measurement, so dropping every copy of a duplicated sale_id
        # discards a real sale on top of the bogus one. transform.quarantine_invalid_sales
        # already rejects genuinely ambiguous duplicate sale_ids with both copies; anything
        # still duplicated at this point is a survivor worth keeping one of.
        surplus_mask = df.duplicated(subset=pk_cols, keep="first")
        if surplus_mask.any():
            rejected_df = df.loc[surplus_mask].copy()
            rejected_df["table_name"] = table_name
            rejected_df["issue"] = (
                f"Surplus row for duplicate {', '.join(pk_cols)}; kept the first occurrence"
            )
            rejected.append(rejected_df)
            logger.warning(
                f"{table_name}: quarantined {int(surplus_mask.sum())} surplus row(s) for "
                f"{n_issues} duplicated key(s); kept the first occurrence of each."
            )

        tables[table_name] = df.loc[~surplus_mask].copy()

    rejected_df = pd.concat(rejected, ignore_index=True) if rejected else pd.DataFrame()

    return results, rejected_df


def check_foreign_keys(tables: dict) -> tuple[list[dict], pd.DataFrame]:
    results = []
    rejected = []

    fk_checks = [
        ("dim_products",            "category_id", "dim_categories", "category_id"),
        ("fact_sales",              "customer_id", "dim_customers",  "customer_id"),
        ("fact_sales",              "product_id",  "dim_products",   "product_id"),
        ("fact_sales",              "branch_id",   "dim_branches",   "branch_id"),
        ("fact_inventory_snapshot", "product_id",  "dim_products",   "product_id"),
        ("fact_inventory_snapshot", "branch_id",   "dim_branches",   "branch_id"),
    ]

    for left_table, fk_col, right_table, pk_col in fk_checks:
        left_df  = tables[left_table]
        right_df = tables[right_table]

        valid_keys = set(right_df[pk_col].dropna())

        n_issues = int((~left_df[fk_col].isin(valid_keys)).sum())
        my_dict = {
            "check": f"Foreign key {fk_col} in {left_table} references {pk_col} in {right_table}",
            "passed": n_issues == 0,
            "issues": n_issues,
        }

        bad_mask = ~left_df[fk_col].isin(valid_keys)
        if bad_mask.any():
            rejected_df = left_df.loc[bad_mask].copy()
            rejected_df["table_name"] = left_table
            rejected_df["issue"] = f"Foreign key {fk_col} does not reference {pk_col} in {right_table}"
            tables[left_table] = left_df.loc[~bad_mask].copy()
            rejected.append(rejected_df)


        if my_dict["passed"]:
            logger.info(f"Check passed: {my_dict['check']}")
        else:
            logger.warning(f"Check failed: {my_dict['check']} - Issues: {n_issues}")

        results.append(my_dict)

    rejected_df = pd.concat(rejected, ignore_index=True) if rejected else pd.DataFrame()

    return results, rejected_df


def check_null_keys(tables: dict) -> tuple[list[dict], pd.DataFrame]:
    results = []
    rejected = []

    null_checks = [
        ("dim_customers",  "customer_id"),
        ("dim_products",   "product_id"),
        ("dim_branches",   "branch_id"),
        ("dim_categories", "category_id"),
        ("fact_sales",     "sale_id"),
        ("fact_inventory_snapshot", ["snapshot_date", "product_id", "branch_id"]),
    ]

    for table_name, key_cols in null_checks:
        df = tables[table_name]

        if isinstance(key_cols, str):
            key_cols = [key_cols]

        bad_mask = df[key_cols].isnull().any(axis=1)
        n_issues = int(df[key_cols].isnull().any(axis=1).sum())

        if n_issues:
            rejected_df = df.loc[bad_mask].copy()
            rejected_df["table_name"] = table_name
            rejected_df["issue"] = f"Null values in {', '.join(key_cols)}"
            rejected.append(rejected_df)
            tables[table_name] = df.loc[~bad_mask].copy()

        my_dict = {
            "check": f"Null values in {', '.join(key_cols)} of {table_name}",
            "passed": n_issues == 0,
            "issues": n_issues,
        }

        if my_dict["passed"]:
            logger.info(f"Check passed: {my_dict['check']}")
        else:
            logger.warning(f"Check failed: {my_dict['check']} - Issues: {n_issues}")

        results.append(my_dict)

    rejected_df = pd.concat(rejected, ignore_index=True) if rejected else pd.DataFrame()

    return results, rejected_df


def assert_referential_integrity(tables: dict) -> None:
    edges = [
        ("dim_products",            "category_id", "dim_categories", "category_id"),
        ("fact_sales",              "customer_id", "dim_customers",  "customer_id"),
        ("fact_sales",              "product_id",  "dim_products",   "product_id"),
        ("fact_sales",              "branch_id",   "dim_branches",   "branch_id"),
        ("fact_inventory_snapshot", "product_id",  "dim_products",   "product_id"),
        ("fact_inventory_snapshot", "branch_id",   "dim_branches",   "branch_id"),
    ]

    problems = []
    for left_table, fk_col, right_table, pk_col in edges:
        valid_keys = set(tables[right_table][pk_col].dropna())
        n_orphan = int((~tables[left_table][fk_col].isin(valid_keys)).sum())
        if n_orphan:
            problems.append(
                f"{left_table}.{fk_col} -> {right_table}.{pk_col}: {n_orphan} orphan row(s)"
            )

    if problems:
        for problem in problems:
            logger.error(f"Referential integrity broken after all checks: {problem}")
        raise ValueError(
            "Refusing to load: orphan rows remain after the quality checks. "
            + "; ".join(problems)
        )

    logger.info(
        f"Referential integrity verified across {len(edges)} foreign-key edge(s); "
        "no orphan rows remain."
    )


def run_quality_checks(tables: dict) -> tuple[dict, list[dict], pd.DataFrame]:
    results = []
    rejected = []
    checks = [
        check_dimension_uniqueness,
        check_null_keys,
        check_fact_pk,
        check_foreign_keys,
    ]

    for check in checks:
        check_results, rejected_df = check(tables)
        results.extend(check_results)
        if not rejected_df.empty:
            rejected.append(rejected_df)

    all_rejected_df = pd.concat(rejected, ignore_index=True) if rejected else pd.DataFrame()

    assert_referential_integrity(tables)

    return tables, results, all_rejected_df