import os
import pandas as pd
from config import Config
from rawg_api import RawgAPI
from logger import setup_logger
import time

# Set up the logger
logger = setup_logger()

# Initialize configuration and APIs
config = Config()
rawg_api = RawgAPI(config.RAWG_API_KEY)

def update_review_counts():
    """Update review counts for all games in the Excel file."""
    logger.info("Starting update of review counts")
    
    try:
        # Read the Excel file
        excel_path = config.EXCEL_FILE_PATH
        df = pd.read_excel(excel_path, engine='openpyxl')
        
        # Check if there are games to update
        if len(df) == 0:
            logger.info("No games to update")
            return
        
        logger.info(f"Found {len(df)} games to update")
        
        # Track updates
        updated_count = 0
        
        # Iterate through all games
        for index, row in df.iterrows():
            try:
                game_id = row['Game ID']
                game_name = row['Name']
                
                # Fetch latest data from RAWG API
                logger.info(f"Fetching data for {game_name} (ID: {game_id})")
                game_details = rawg_api.get_game_details(game_id)
                
                if game_details and 'ratings_count' in game_details:
                    # Get the ratings count
                    ratings_count = game_details.get('ratings_count', 0)
                    
                    # Update the dataframe
                    df.at[index, 'Review Count'] = ratings_count
                    
                    logger.info(f"Updated {game_name}: Review Count = {ratings_count}")
                    updated_count += 1
                    
                    # Sleep to avoid rate limits
                    time.sleep(0.5)
                else:
                    logger.warning(f"Could not fetch data for {game_name} (ID: {game_id})")
            
            except Exception as e:
                logger.error(f"Error updating game {row.get('Name', 'Unknown')}: {e}")
        
        # Save the updated dataframe
        df.to_excel(excel_path, index=False, engine='openpyxl')
        
        logger.info(f"Update completed. Updated {updated_count} out of {len(df)} games.")
        
    except Exception as e:
        logger.error(f"Error in update_review_counts: {e}")

if __name__ == "__main__":
    update_review_counts()
    print("Review count update complete! Check the logs for details.") 