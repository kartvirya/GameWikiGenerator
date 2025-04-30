import os
import time
import logging
import concurrent.futures
import threading
from tqdm import tqdm
from datetime import datetime

from config import Config
from logger import setup_logger
from rawg_api import RawgAPI
from openai_api import OpenAIAPI
from excel_manager import ExcelManager

# Set up the logger
logger = setup_logger()

class RapidGameProcessor:
    """Specialized processor for rapidly generating many game wiki entries."""
    
    def __init__(self, target_count=10000, time_limit_minutes=5):
        """Initialize the rapid processor.
        
        Args:
            target_count: Target number of games to process
            time_limit_minutes: Time limit in minutes
        """
        logger.info(f"Initializing Rapid Game Processor (target: {target_count} games in {time_limit_minutes} minutes)")
        
        # Set environment variable for rapid mode
        os.environ["RAPID_MODE"] = "True"
        
        # Initialize configuration and components
        self.config = Config()
        self.rawg_api = RawgAPI(self.config.RAWG_API_KEY)
        self.openai_api = OpenAIAPI(self.config.OPENAI_API_KEY)
        self.openai_api.set_rapid_mode(True)
        
        # Create a separate Excel file for rapid processing
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.excel_path = str(self.config.DATA_DIR / f"rapid_wiki_{timestamp}.xlsx")
        self.excel_manager = ExcelManager(self.excel_path)
        
        # Set processing parameters
        self.target_count = target_count
        self.time_limit_seconds = time_limit_minutes * 60
        self.processed_games = set()
        self.processing_queue = []
        self.games_processed = 0
        self.start_time = None
        self.lock = threading.Lock()
        
        # Status tracking
        self.success_count = 0
        self.error_count = 0
        
        logger.info("Rapid Game Processor initialized")
        
    def _load_game_batch(self, page_size=40, page_count=5):
        """Load a batch of games to process.
        
        Args:
            page_size: Number of games to fetch per page
            page_count: Number of pages to fetch
        """
        logger.info(f"Loading game batch (page_size={page_size}, page_count={page_count})")
        games = []
        
        # Fetch multiple pages in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=page_count) as executor:
            futures = []
            for page in range(1, page_count + 1):
                futures.append(executor.submit(
                    self.rawg_api.get_indie_games, 
                    page=page, 
                    page_size=page_size, 
                    min_reviews=1
                ))
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    page_games = future.result()
                    if page_games:
                        games.extend(page_games)
                except Exception as e:
                    logger.error(f"Error fetching game page: {e}")
        
        # Filter out already processed games
        new_games = [g for g in games if g['id'] not in self.processed_games]
        
        logger.info(f"Loaded {len(new_games)} new games for processing")
        return new_games
    
    def _process_single_game(self, game):
        """Process a single game.
        
        Args:
            game: Game data from RAWG API
            
        Returns:
            True if successful, False otherwise
        """
        game_id = game['id']
        game_name = game.get('name', 'Unknown Game')
        
        try:
            # Skip if already processed
            if game_id in self.processed_games:
                return False
                
            # Get game details
            game_details = self.rawg_api.get_game_details(game_id)
            if not game_details:
                logger.warning(f"Could not fetch details for game: {game_name}")
                return False
            
            # Prepare wiki input
            wiki_input = {
                'name': game_details.get('name', ''),
                'description': game_details.get('description', ''),
                'released': game_details.get('released', ''),
                'platforms': [p.get('platform', {}).get('name', '') for p in game_details.get('platforms', [])],
                'developers': [d.get('name', '') for d in game_details.get('developers', [])],
                'publishers': [p.get('name', '') for p in game_details.get('publishers', [])],
                'genres': [g.get('name', '') for g in game_details.get('genres', [])],
                'tags': [t.get('name', '') for t in game_details.get('tags', [])],
                'rating': game_details.get('rating', 0),
            }
            
            # Generate wiki content
            wiki_entry, references = self.openai_api.generate_wiki_entry(wiki_input)
            
            # Format developer names
            developers = game_details.get('developers', [])
            dev_names = [dev.get('name', '') for dev in developers if dev and isinstance(dev, dict)]
            
            # Prepare Excel data
            excel_data = {
                'Game ID': game_id,
                'Name': game_details.get('name', ''),
                'Studio': ', '.join(dev_names),
                'Release Date': game_details.get('released', ''),
                'Metacritic': game_details.get('metacritic', 0),
                'Review Count': game_details.get('ratings_count', 0),
                'Image URL': game_details.get('background_image', ''),
                'Wiki Entry': wiki_entry,
                'References': references,
                'Steam URL': game_details.get('steam_url', ''),
            }
            
            # Save to Excel
            with self.lock:
                self.excel_manager.add_game_entry(excel_data)
                self.processed_games.add(game_id)
                self.success_count += 1
                self.games_processed += 1
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing game {game_name}: {e}")
            with self.lock:
                self.error_count += 1
            return False
    
    def run(self):
        """Run the rapid processing job."""
        self.start_time = time.time()
        current_time = self.start_time
        end_time = self.start_time + self.time_limit_seconds
        
        logger.info(f"Starting rapid processing (target: {self.target_count} games in {self.time_limit_seconds} seconds)")
        
        # Initialize progress bar
        pbar = tqdm(total=self.target_count, desc="Processing games")
        
        # Processing loop
        while (current_time < end_time and self.games_processed < self.target_count):
            # Load more games if needed
            if len(self.processing_queue) < 100:
                new_games = self._load_game_batch(
                    page_size=self.config.PAGE_SIZE,
                    page_count=5
                )
                self.processing_queue.extend(new_games)
            
            # Process games in parallel batches
            batch_size = min(self.config.BATCH_SIZE, len(self.processing_queue))
            if batch_size > 0:
                batch = self.processing_queue[:batch_size]
                self.processing_queue = self.processing_queue[batch_size:]
                
                # Process batch in parallel
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.PARALLEL_REQUESTS) as executor:
                    list(executor.map(self._process_single_game, batch))
            
            # Update progress bar
            pbar.n = self.games_processed
            pbar.refresh()
            
            # Check time
            current_time = time.time()
            
            # Small delay to prevent CPU overuse
            time.sleep(0.01)
        
        # Close progress bar
        pbar.close()
        
        # Calculate statistics
        elapsed_time = time.time() - self.start_time
        games_per_minute = (self.games_processed / elapsed_time) * 60
        
        logger.info(f"Rapid processing completed:")
        logger.info(f"- Games processed: {self.games_processed}")
        logger.info(f"- Successful: {self.success_count}")
        logger.info(f"- Errors: {self.error_count}")
        logger.info(f"- Time elapsed: {elapsed_time:.2f} seconds")
        logger.info(f"- Processing rate: {games_per_minute:.2f} games per minute")
        logger.info(f"- Results saved to: {self.excel_path}")
        
        return {
            "games_processed": self.games_processed,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "elapsed_time": elapsed_time,
            "games_per_minute": games_per_minute,
            "excel_path": self.excel_path
        }

if __name__ == "__main__":
    # Parse command-line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Rapid Game Wiki Generator")
    parser.add_argument("--count", type=int, default=10000, help="Target number of games to process")
    parser.add_argument("--time", type=int, default=5, help="Time limit in minutes")
    args = parser.parse_args()
    
    # Run the processor
    processor = RapidGameProcessor(target_count=args.count, time_limit_minutes=args.time)
    results = processor.run()
    
    # Print summary
    print("\n--- Rapid Processing Complete ---")
    print(f"Games processed: {results['games_processed']}")
    print(f"Success rate: {results['success_count']}/{results['games_processed']} ({results['success_count']/max(1, results['games_processed'])*100:.1f}%)")
    print(f"Time elapsed: {results['elapsed_time']:.2f} seconds")
    print(f"Processing rate: {results['games_per_minute']:.2f} games per minute")
    print(f"Results saved to: {results['excel_path']}") 