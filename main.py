import os
import time
import logging
import schedule
from datetime import datetime

from config import Config
from logger import setup_logger
from rawg_api import RawgAPI
from openai_api import OpenAIAPI
from excel_manager import ExcelManager
from app import app

# Set up the logger
logger = setup_logger()

class GameWikiGenerator:
    def __init__(self):
        """Initialize the Game Wiki Generator with required APIs and components."""
        logger.info("Initializing Game Wiki Generator")
        
        # Initialize APIs and managers
        self.config = Config()
        self.rawg_api = RawgAPI(self.config.RAWG_API_KEY)
        self.openai_api = OpenAIAPI(self.config.OPENAI_API_KEY)
        self.excel_manager = ExcelManager(self.config.EXCEL_FILE_PATH)
        
        # Track processed games to avoid duplicates
        self.processed_games = set()
        self.load_processed_games()
        
        # Counter for daily request tracking
        self.daily_request_count = 0
        self.request_limit = self.config.DAILY_REQUEST_LIMIT
        self.reset_date = datetime.now().date()
        
        logger.info("Game Wiki Generator initialized successfully")

    def load_processed_games(self):
        """Load already processed games from Excel to avoid duplicates."""
        try:
            existing_games = self.excel_manager.get_processed_game_ids()
            self.processed_games = set(existing_games)
            logger.info(f"Loaded {len(self.processed_games)} processed game IDs")
        except Exception as e:
            logger.error(f"Error loading processed games: {e}")

    def reset_daily_counter(self):
        """Reset the daily request counter."""
        self.daily_request_count = 0
        self.reset_date = datetime.now().date()
        logger.info("Daily request counter has been reset")

    def process_game(self, game):
        """Process a single game by fetching details, generating wiki entry, and saving to Excel."""
        try:
            game_id = game['id']
            
            # Skip if already processed
            if game_id in self.processed_games:
                logger.info(f"Skipping already processed game: {game['name']}")
                return False
            
            # Get detailed game info
            logger.info(f"Fetching details for game: {game['name']}")
            game_details = self.rawg_api.get_game_details(game_id)
            
            if not game_details:
                logger.warning(f"Could not fetch details for game: {game['name']}")
                return False
            
            # Prepare game data for wiki generation
            wiki_input = self.prepare_wiki_input(game_details)
            
            # Generate wiki entry
            logger.info(f"Generating wiki entry for: {game['name']}")
            wiki_entry, references = self.openai_api.generate_wiki_entry(wiki_input)
            
            # Prepare data for Excel
            excel_data = {
                'Game ID': game_id,
                'Name': game_details.get('name', ''),
                'Studio': ', '.join([dev.get('name', '') for dev in game_details.get('developers', [])]),
                'Release Date': game_details.get('released', ''),
                'Review Count': len(game_details.get('ratings', [])),
                'Image URL': game_details.get('background_image', ''),
                'Wiki Entry': wiki_entry,
                'References': references,
                'Additional Info': self.get_additional_info(game_details)
            }
            
            # Save to Excel
            logger.info(f"Saving data for: {game['name']}")
            self.excel_manager.add_game_entry(excel_data)
            
            # Mark as processed
            self.processed_games.add(game_id)
            
            # Increment request counter
            self.daily_request_count += 1
            
            logger.info(f"Successfully processed game: {game['name']}")
            
            # No delay in the web request context to avoid worker timeout
            # Delays should be handled at the scheduling level
            
            return True
        
        except Exception as e:
            logger.error(f"Error processing game {game.get('name', 'unknown')}: {e}")
            return False

    def prepare_wiki_input(self, game_details):
        """Prepare game data as input for wiki generation."""
        return {
            'name': game_details.get('name', ''),
            'description': game_details.get('description', ''),
            'released': game_details.get('released', ''),
            'platforms': [p.get('platform', {}).get('name', '') for p in game_details.get('platforms', [])],
            'developers': [d.get('name', '') for d in game_details.get('developers', [])],
            'publishers': [p.get('name', '') for p in game_details.get('publishers', [])],
            'genres': [g.get('name', '') for g in game_details.get('genres', [])],
            'tags': [t.get('name', '') for t in game_details.get('tags', [])],
            'ratings': game_details.get('ratings', []),
            'rating': game_details.get('rating', 0),
            'website': game_details.get('website', ''),
            'image_url': game_details.get('background_image', '')
        }

    def get_additional_info(self, game_details):
        """Format additional information from game details."""
        additional_info = []
        
        if game_details.get('rating'):
            additional_info.append(f"Average Rating: {game_details['rating']}")
        
        if game_details.get('playtime'):
            additional_info.append(f"Average Playtime: {game_details['playtime']} hours")
            
        if game_details.get('esrb_rating', {}).get('name'):
            additional_info.append(f"ESRB Rating: {game_details['esrb_rating']['name']}")
            
        if game_details.get('metacritic'):
            additional_info.append(f"Metacritic Score: {game_details['metacritic']}")
            
        platforms = [p.get('platform', {}).get('name', '') for p in game_details.get('platforms', [])]
        if platforms:
            additional_info.append(f"Platforms: {', '.join(platforms)}")
            
        return "\n".join(additional_info)

    def run_daily_job(self, limit=None):
        """Main job to run daily processing of games.
        
        Args:
            limit: Optional maximum number of games to process in this run
        """
        logger.info(f"Starting daily job for processing games{' (limited mode)' if limit else ''}")
        
        # Reset counter if it's a new day
        current_date = datetime.now().date()
        if current_date != self.reset_date:
            self.reset_daily_counter()
        
        # If limit is provided, use that instead of daily limit
        effective_limit = limit if limit is not None else self.request_limit
        
        # Check if we've hit the daily limit
        if self.daily_request_count >= effective_limit:
            logger.info(f"Request limit reached ({effective_limit}). Stopping.")
            return
        
        page = 1
        processed_count = 0
        while self.daily_request_count < self.request_limit and processed_count < effective_limit:
            try:
                # Get indie games (can be customized based on need)
                games = self.rawg_api.get_indie_games(page)
                
                if not games:
                    logger.info("No more games to process or API limit reached")
                    break
                
                # Process each game
                success_count = 0
                for game in games:
                    if self.daily_request_count >= self.request_limit or processed_count >= effective_limit:
                        logger.info(f"Request limit reached ({effective_limit}). Stopping.")
                        return
                    
                    success = self.process_game(game)
                    if success:
                        success_count += 1
                        processed_count += 1
                        # Add a delay between processing games to avoid API rate limits
                        # This is safe in the background thread
                        time.sleep(2)
                
                if success_count == 0:
                    # If we processed a page with no new games, move to the next page
                    page += 1
                
                # Break if no games were returned
                if not games:
                    break
                    
            except Exception as e:
                logger.error(f"Error in run_daily_job: {e}")
                # Reduce sleep time to avoid worker timeout
                time.sleep(5)  # Wait before retrying
        
        logger.info(f"Daily job completed. Processed {processed_count} games.")

def start_scheduler():
    """Start the scheduler for periodic processing."""
    try:
        logger.info("Starting Game Wiki Generator scheduler")
        
        # Initialize the generator
        generator = GameWikiGenerator()
        
        # Schedule the daily job
        schedule.every().day.at("00:00").do(generator.reset_daily_counter)
        
        # Run the job immediately and then schedule it to run every hour
        generator.run_daily_job()
        schedule.every(1).hour.do(generator.run_daily_job)
        
        logger.info("Job scheduled, entering main loop")
        
        # Keep the scheduler running
        while True:
            schedule.run_pending()
            time.sleep(60)
            
    except KeyboardInterrupt:
        logger.info("Scheduler terminated by user")
    except Exception as e:
        logger.critical(f"Critical error in scheduler: {e}")
        raise

# Create the data directory and ensure the Excel file exists
config = Config()
os.makedirs(config.DATA_DIR, exist_ok=True)
excel_manager = ExcelManager(config.EXCEL_FILE_PATH)
excel_manager._ensure_file_exists()

if __name__ == "__main__":
    # Run the app directly if script is executed
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
