import os
import pandas as pd
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def format_date_with_suffix(date_str):
    """
    Convert a date string to the format 'Month Day, Year' with appropriate suffix
    Handles ISO format dates like '2025-03-27 19:20:54'
    """
    try:
        # Try to parse the date string
        if isinstance(date_str, str):
            date_obj = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        elif isinstance(date_str, datetime):
            date_obj = date_str
        else:
            return date_str  # Return as is if not a recognized format
        
        # Get the day suffix
        day = date_obj.day
        day_suffix = 'th' if 11 <= day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
        
        # Format the date
        return date_obj.strftime(f'%B {day}{day_suffix}, %Y')
    except Exception as e:
        logger.error(f"Error formatting date '{date_str}': {e}")
        return date_str  # Return original if conversion failed

def update_excel_dates():
    """Update dates in the Excel file to the new format"""
    
    # Path to the Excel file
    excel_path = 'data/game_wiki.xlsx'
    
    try:
        # Check if file exists
        if not os.path.exists(excel_path):
            logger.error(f"Excel file not found: {excel_path}")
            return False
        
        # Read the Excel file
        logger.info(f"Reading Excel file: {excel_path}")
        df = pd.read_excel(excel_path, engine='openpyxl')
        
        # Check if 'Date Added' column exists
        if 'Date Added' not in df.columns:
            logger.error("'Date Added' column not found in Excel file")
            return False
        
        # Count original entries with date format
        date_entries_count = 0
        
        # Update the date format for each row
        for index, row in df.iterrows():
            date_value = row.get('Date Added')
            if date_value and isinstance(date_value, (str, datetime)):
                new_date = format_date_with_suffix(date_value)
                if new_date != date_value:
                    df.at[index, 'Date Added'] = new_date
                    date_entries_count += 1
        
        # Save the updated DataFrame back to Excel
        logger.info(f"Saving updated dates for {date_entries_count} entries")
        df.to_excel(excel_path, index=False, engine='openpyxl')
        
        logger.info("Excel dates updated successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error updating Excel dates: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting date format update")
    result = update_excel_dates()
    if result:
        logger.info("Date format update completed successfully")
    else:
        logger.error("Date format update failed") 