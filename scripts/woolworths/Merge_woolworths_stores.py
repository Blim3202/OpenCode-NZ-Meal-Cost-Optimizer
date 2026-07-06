import pandas as pd
import os
import csv
from pathlib import Path

def merge_store_data():
    # Config
    script_dir = Path(__file__).parent  # proj/scripts/woolworths/
    DATA_DIR = script_dir.parent.parent / 'data'
    CSV_FILE = os.path.join(DATA_DIR, "woolworths_stores.csv")

    # Read the CSV files
    df_choices = pd.read_csv(os.path.join(DATA_DIR, "woolworths_store_choices.csv"))
    df_data = pd.read_csv(os.path.join(DATA_DIR, "woolworths_store_data.csv"))

    # Select only the columns we need from the second table
    df_data_subset = df_data[['SiteDataID', 'latitude', 'longitude']]

    # Left join: keep all rows from df_choices, add lat/long where id matches SiteDataID
    merged = df_choices.merge(df_data_subset,
                            left_on='id',
                            right_on='SiteDataID',
                            how='left')

    # Drop the redundant 'SiteDataID' column (since we already have 'id')
    merged = merged.drop('SiteDataID', axis=1)

    # Now merged contains all columns from df_choices plus 'latitude' and 'longitude'
    # Rows without a match will have NaN for these new columns
    # Note that woolworths Flaxmere still has not had the lat long added to the map data - might be added in eventually
    merged.to_csv(CSV_FILE, index=False, encoding='utf-8')
    print(f"✅ Successfully saved structured data for {len(merged)} woolworths stores at {CSV_FILE}.\n")


if __name__ == "__main__":
    merge_store_data()