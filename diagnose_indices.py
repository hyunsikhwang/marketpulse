import yfinance as yf
import pandas as pd
from datetime import datetime

indices = {
    'Nikkei 225': '^N225',
    'KOSPI': '^KS11',
    'KOSDAQ': '^KQ11',
    'S&P500': '^GSPC' # Baseline for comparison
}

def diagnose():
    today = datetime.now()
    current_year = today.year
    start_date = datetime(current_year - 1, 12, 15).strftime('%Y-%m-%d')
    end_date = today.strftime('%Y-%m-%d')
    
    print(f"Diagnosing data for: {list(indices.keys())}")
    
    all_data = pd.DataFrame()
    for name, ticker in indices.items():
        print(f"\nFetching {name} ({ticker})...")
        try:
            # Using progress=False to keep output clean
            data = yf.download(ticker, start=start_date, end=end_date, progress=False)['Close']
            if data.empty:
                print(f"WARNING: No data found for {name}")
            else:
                if isinstance(data, pd.DataFrame):
                    data = data.iloc[:, 0]
                print(f"Success: {len(data)} rows found. Last date: {data.index[-1].date()}")
                all_data[name] = data
        except Exception as e:
            print(f"ERROR fetching {name}: {e}")
            
    if not all_data.empty:
        print("\n--- Data Alignment Check ---")
        print(f"Combined DataFrame shape: {all_data.shape}")
        print("\nMissing values (NaN) count:")
        print(all_data.isna().sum())
        
        print("\nRows with NaNs (first 5):")
        print(all_data[all_data.isna().any(axis=1)].head())
        
        # Check current year data
        current_year_df = all_data[all_data.index.year == current_year]
        print(f"\nCurrent Year ({current_year}) rows: {len(current_year_df)}")
        if not current_year_df.empty:
            print("\nLatest data for each index:")
            print(current_year_df.tail(1).T)
            
    return all_data

if __name__ == "__main__":
    diagnose()
