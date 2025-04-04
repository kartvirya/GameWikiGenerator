import pandas as pd
from config import Config

# Initialize configuration to get the Excel file path
config = Config()
excel_path = config.EXCEL_FILE_PATH

print(f"Checking Excel file: {excel_path}")

# Read the Excel file
df = pd.read_excel(excel_path, engine='openpyxl')

# Print the column names
print("\nColumns in the Excel file:")
print(df.columns.tolist())

# Check if Ratings Count column exists
if 'Ratings Count' in df.columns:
    # Convert to numeric to handle any non-numeric values
    df['Ratings Count'] = pd.to_numeric(df['Ratings Count'], errors='coerce')
    
    # Get statistics about the Ratings Count column
    print("\nRatings Count statistics:")
    print(f"Mean: {df['Ratings Count'].mean()}")
    print(f"Min: {df['Ratings Count'].min()}")
    print(f"Max: {df['Ratings Count'].max()}")
    print(f"Number of games with 0 ratings: {(df['Ratings Count'] == 0).sum()}")
    print(f"Number of games with ratings > 0: {(df['Ratings Count'] > 0).sum()}")
    
    # Show a sample of games with their ratings counts
    print("\nSample of games with their ratings counts:")
    sample = df[['Name', 'Game ID', 'Ratings Count']].head(10)
    print(sample)
else:
    print("\nRatings Count column not found in the Excel file") 