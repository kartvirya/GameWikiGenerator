#!/usr/bin/env bash
# Exit on error
set -e

# Display Python version
python --version

# Install Python dependencies
pip install -r .render/requirements.txt

# Create data directory if it doesn't exist
mkdir -p data

# Create default Excel file if needed (won't overwrite existing)
if [ ! -f "data/game_wiki.xlsx" ]; then
    echo "Creating initial Excel file structure"
    python -c "
import pandas as pd
from openpyxl import Workbook
# Create a new workbook
wb = Workbook()
ws = wb.active
ws.title = 'Game Wiki Entries'
# Add headers
headers = ['Game ID', 'Name', 'Studio', 'Release Date', 'Wiki Entry', 'References', 'Image URL', 'Date Added', 'Review Count', 'Additional Info']
for col, header in enumerate(headers, 1):
    ws.cell(row=1, column=col, value=header)
# Save the workbook
wb.save('data/game_wiki.xlsx')
print('Created initial Excel file structure')
"
fi

# Ensure static directories exist
mkdir -p static/css
mkdir -p static/js
mkdir -p static/img

# Ready for deployment message
echo "Build completed successfully!"