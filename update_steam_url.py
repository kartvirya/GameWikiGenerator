import pandas as pd
import os

# Path to Excel file
excel_path = 'data/game_wiki.xlsx'

# Check if file exists
if not os.path.exists(excel_path):
    print(f"Excel file not found at {excel_path}")
    exit(1)

# Load the Excel file
print(f"Reading Excel file: {excel_path}")
df = pd.read_excel(excel_path, engine='openpyxl')

# Find Undertale by Game ID
game_index = df[df['Game ID'] == 13627].index

# Update the Steam URL if found
if len(game_index) > 0:
    # Update the Steam URL
    df.at[game_index[0], 'Steam URL'] = 'https://store.steampowered.com/app/391540/Undertale/'
    
    # Save the updated DataFrame back to Excel
    df.to_excel(excel_path, index=False, engine='openpyxl')
    
    print("Added Steam URL for Undertale")
else:
    print("Undertale (Game ID: 13627) not found in the Excel file") 