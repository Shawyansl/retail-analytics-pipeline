import pandas as pd
from src.extract import extract_data
from src.transform import transform_data

if __name__ == "__main__":
    file_path = "./data/raw/retail_transactions_denormalized.csv"
    df = extract_data(file_path)
    clean_df, rejected_df = transform_data(df)

    print(clean_df)
    print("dataframe columns:", clean_df.columns)
    print(clean_df.columns.to_list())

