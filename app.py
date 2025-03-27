import os
import threading
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash

from config import Config
from logger import setup_logger
from rawg_api import RawgAPI
from openai_api import OpenAIAPI
from excel_manager import ExcelManager

# Set up the logger
logger = setup_logger()

# Initialize the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Initialize configuration and APIs
config = Config()
rawg_api = RawgAPI(config.RAWG_API_KEY)
openai_api = OpenAIAPI(config.OPENAI_API_KEY)
excel_manager = ExcelManager(config.EXCEL_FILE_PATH)

# Global variables
ITEMS_PER_PAGE = 10

def index():
    """Home page route."""
    # Always get the latest game count directly from Excel
    try:
        df = pd.read_excel(config.EXCEL_FILE_PATH, engine='openpyxl')
        game_count = len(df)
        
        # Get some stats for display
        most_recent_games = df.sort_index(ascending=False).head(5).to_dict('records')
        
        # Check if a background job is running
        job_status = "Running" if job_running else "Not running"
        
        logger.info(f"Home page loaded. Total games: {game_count}, Job status: {job_status}")
        
    except Exception as e:
        logger.error(f"Error loading game count: {e}")
        game_count = 0
        most_recent_games = []
        job_status = "Unknown"
    
    # Pass data to template
    return render_template(
        'index.html',
        game_count=game_count,
        most_recent_games=most_recent_games,
        job_status=job_status
    )

@app.route('/games')
@app.route('/games/<int:page>')
def games(page=1):
    """Display all processed games with pagination."""
    try:
        # Always reload games from Excel to get the latest data
        # This ensures newly processed games appear immediately
        df = pd.read_excel(config.EXCEL_FILE_PATH, engine='openpyxl')
        
        # Sort by most recently added (assuming the file is in chronological order)
        # This shows newest games first
        df = df.sort_index(ascending=False)
        
        # Handle NaN values in Image URL column
        df['Image URL'] = df['Image URL'].apply(lambda x: '' if pd.isna(x) else x)
        
        # Calculate pagination
        total_games = len(df)
        total_pages = (total_games + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
        
        # Ensure valid page number
        page = max(1, min(page, total_pages) if total_pages > 0 else 1)
        
        # Get games for current page
        start_idx = (page - 1) * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE
        games_page = df.iloc[start_idx:end_idx].to_dict('records')
        
        logger.info(f"Displaying {len(games_page)} games (page {page}/{total_pages}), total: {total_games} games")
        
        return render_template(
            'games.html',
            games=games_page,
            page=page,
            total_pages=total_pages,
            total_games=total_games
        )
        
    except Exception as e:
        logger.error(f"Error loading games: {e}")
        return render_template('games.html', games=[], page=1, total_pages=1, total_games=0)

@app.route('/game/<int:game_id>')
def game_detail(game_id):
    """Display detailed information for a single game."""
    try:
        # Always reload game from Excel to get the latest data
        df = pd.read_excel(config.EXCEL_FILE_PATH, engine='openpyxl')
        
        # Find the game by ID
        game = df[df['Game ID'] == game_id]
        
        if len(game) == 0:
            flash("Game not found", "error")
            return redirect(url_for('games'))
            
        # Handle NaN values in Image URL column
        game['Image URL'] = game['Image URL'].apply(lambda x: '' if pd.isna(x) else x)
            
        # Convert to dictionary for template
        game_data = game.iloc[0].to_dict()
        
        # If image URL is missing, try to fetch it from the RAWG API
        if not game_data.get('Image URL'):
            try:
                logger.info(f"Fetching missing image for game {game_id}")
                game_details = rawg_api.get_game_details(game_id)
                if game_details and 'background_image' in game_details:
                    game_data['Image URL'] = game_details.get('background_image', '')
            except Exception as img_error:
                logger.error(f"Error fetching image for game {game_id}: {img_error}")
        
        logger.info(f"Displaying details for game: {game_data.get('Name', 'Unknown')}")
        return render_template('game_detail.html', game=game_data)
        
    except Exception as e:
        logger.error(f"Error loading game details: {e}")
        flash("Error loading game details", "error")
        return redirect(url_for('games'))

@app.route('/search', methods=['GET', 'POST'])
def search():
    """Search for games on RAWG.io."""
    if request.method == 'POST':
        query = request.form.get('query', '')
        
        if not query:
            flash("Please enter a search query", "warning")
            return render_template('search.html')
            
        try:
            # Always get fresh processed game IDs directly from Excel to filter out already processed games
            try:
                df = pd.read_excel(config.EXCEL_FILE_PATH, engine='openpyxl')
                processed_ids = df['Game ID'].tolist() if 'Game ID' in df.columns else []
            except Exception as excel_error:
                logger.error(f"Error reading Excel file: {excel_error}")
                processed_ids = []
            
            # Search for games
            search_results = rawg_api.search_games(query)
            
            # Filter out already processed games
            filtered_results = [game for game in search_results if game['id'] not in processed_ids]
            
            logger.info(f"Search for '{query}' returned {len(search_results)} results, {len(filtered_results)} unprocessed")
            
            return render_template(
                'search_results.html',
                query=query,
                search_results=filtered_results
            )
            
        except Exception as e:
            logger.error(f"Error searching for games: {e}")
            flash("Error searching for games", "error")
            return render_template('search.html')
            
    return render_template('search.html')

# Global variable to track games being processed
processing_games = {}

@app.route('/process/<int:game_id>')
def process_game(game_id):
    """Process a single game by ID."""
    global processing_games
    
    # Check if already processing
    if game_id in processing_games:
        flash(f"Game is already being processed. Please wait.", "info")
        return redirect(url_for('search'))
    
    try:
        # Get the game details from RAWG
        game_details = rawg_api.get_game_details(game_id)
        
        if not game_details:
            flash("Could not fetch game details", "error")
            return redirect(url_for('search'))
            
        # Create a simple game dict for processor
        game = {
            'id': game_id,
            'name': game_details.get('name', 'Unknown Game')
        }
        
        # Process in background thread
        def process_game_thread(game):
            global processing_games
            try:
                # Initialize GameWikiGenerator components from main.py
                from main import GameWikiGenerator
                generator = GameWikiGenerator()
                
                # Process the game
                success = generator.process_game(game)
                logger.info(f"Background processing for {game['name']} completed with status: {success}")
            except Exception as e:
                logger.error(f"Error in background processing for {game['name']}: {e}")
            finally:
                # Remove from processing list when done
                if game['id'] in processing_games:
                    del processing_games[game['id']]
        
        # Mark as processing
        processing_games[game_id] = game['name']
        
        # Start thread
        thread = threading.Thread(target=process_game_thread, args=(game,))
        thread.daemon = True
        thread.start()
        
        flash(f"Started processing game: {game['name']}. You can check the game library once processing is complete.", "success")
        return redirect(url_for('games'))
            
    except Exception as e:
        logger.error(f"Error starting game processing {game_id}: {e}")
        # Remove from processing if there was an error
        if game_id in processing_games:
            del processing_games[game_id]
        flash("Error processing game", "error")
        return redirect(url_for('search'))

# Global variable to track if job is running
job_running = False

@app.route('/run-job')
def run_job():
    """Run the daily job manually."""
    global job_running
    
    if job_running:
        flash("A job is already running in the background", "info")
        return redirect(url_for('games'))
    
    try:
        # Start the job in a background thread
        def run_background_job():
            global job_running
            try:
                # Initialize GameWikiGenerator components from main.py
                from main import GameWikiGenerator
                generator = GameWikiGenerator()
                
                # Run the job with the full daily limit from config (800 games)
                generator.run_daily_job()
                
                logger.info("Background job completed successfully")
            except Exception as e:
                logger.error(f"Error in background job: {e}")
            finally:
                job_running = False
        
        # Start the thread
        job_running = True
        thread = threading.Thread(target=run_background_job)
        thread.daemon = True
        thread.start()
        
        flash("Job started in the background. Check the game library for results.", "success")
        return redirect(url_for('games'))
        
    except Exception as e:
        logger.error(f"Error starting job: {e}")
        job_running = False
        flash("Error starting job", "error")
        return redirect(url_for('index'))

@app.template_filter('truncate_html')
def truncate_html(text, length=200):
    """Truncate text to a maximum length, preserving complete words"""
    if not text:
        return ""
        
    # Strip HTML tags
    import re
    text = re.sub(r'<.*?>', '', text)
    
    if len(text) <= length:
        return text
        
    # Find the last space before the length limit
    truncated = text[:length]
    last_space = truncated.rfind(' ')
    
    if last_space != -1:
        truncated = truncated[:last_space]
        
    return truncated + "..."

# Add the home page route
app.add_url_rule('/', 'index', index)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)