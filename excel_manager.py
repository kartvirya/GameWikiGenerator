import os
import logging
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class ExcelManager:
    """Manages Excel file operations for storing game wiki data."""
    
    def __init__(self, file_path: str):
        """Initialize the Excel Manager.
        
        Args:
            file_path: Path to the Excel file
        """
        self.file_path = file_path
        self._ensure_file_exists()
        
    def _ensure_file_exists(self) -> None:
        """Ensure the Excel file exists with the correct structure."""
        if not os.path.exists(self.file_path):
            logger.info(f"Creating new Excel file at {self.file_path}")
            # Create a new DataFrame with the expected columns
            df = pd.DataFrame(columns=[
                'Game ID',
                'Name',
                'Studio',
                'Release Date',
                'Metacritic',  # Changed from Review Count 
                'Ratings Count',  # Added new column for RAWG ratings count
                'Image URL',
                'Wiki Entry',
                'References',
                'Additional Info',
                'Steam URL',
                'Store Links',
                'Date Added'
            ])
            
            # Save the empty DataFrame to create the file
            df.to_excel(self.file_path, index=False)
            logger.info("New Excel file created successfully")
        else:
            logger.info(f"Excel file already exists at {self.file_path}")
            
    def add_game_entry(self, game_data: Dict[str, Any]) -> bool:
        """Add a new game entry to the Excel file.
        
        Args:
            game_data: Dictionary containing game information
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load the existing Excel file
            df = pd.read_excel(self.file_path)
            
            # Check if the game already exists
            if 'Game ID' in df.columns and game_data['Game ID'] in df['Game ID'].values:
                logger.warning(f"Game {game_data['Name']} already exists in the Excel file")
                return False
                
            # Add the current date
            game_data['Date Added'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Append the new data
            new_row = pd.DataFrame([game_data])
            df = pd.concat([df, new_row], ignore_index=True)
            
            # Save the updated DataFrame
            df.to_excel(self.file_path, index=False)
            
            logger.info(f"Added game {game_data['Name']} to Excel file")
            return True
            
        except Exception as e:
            logger.error(f"Error adding game entry to Excel: {e}")
            return False
            
    def get_processed_game_ids(self) -> List[int]:
        """Get a list of game IDs that have already been processed.
        
        Returns:
            List of game IDs
        """
        try:
            df = pd.read_excel(self.file_path)
            
            if 'Game ID' in df.columns:
                # Convert to integers and handle any invalid values
                game_ids = []
                for game_id in df['Game ID']:
                    try:
                        game_ids.append(int(game_id))
                    except (ValueError, TypeError):
                        pass
                        
                return game_ids
            
            return []
            
        except Exception as e:
            logger.error(f"Error reading processed game IDs: {e}")
            return []
            
    def get_game_count(self) -> int:
        """Get the total number of games in the Excel file.
        
        Returns:
            Number of games
        """
        try:
            df = pd.read_excel(self.file_path)
            return len(df)
        except Exception as e:
            logger.error(f"Error getting game count: {e}")
            return 0
