import pandas as pd
from src.load import load_data
from src.extract import extract_data
from src.transform import transform_data
from src.quality import run_quality_checks
from reports.reports import generate_all_reports

if __name__ == "__main__":
    file_path = "./data/raw/retail_transactions_denormalized.csv"
    df = extract_data(file_path)
    tables, rejected_df = transform_data(df)
    tables, results, all_rejected_df = run_quality_checks(tables)

    load_data(tables, rejected_df, all_rejected_df)
    generate_all_reports()