import pandas as pd
from load import load_data
from extract import extract_data
from transform import transform_data
from quality import run_quality_checks
from reports import generate_all_reports

if __name__ == "__main__":
    file_path = "./data/raw/retail_transactions_denormalized.csv"

    df = extract_data(file_path)
    tables, rejected_df = transform_data(df)
    tables, results, all_rejected_df = run_quality_checks(tables)

    load_data(tables, rejected_df, all_rejected_df,
              load_path1="./data/processed/rejected_records/rejected_records.csv",
              load_path2="./data/processed/rejected_records/quality_rejected_records.csv")
    generate_all_reports()