import os
import threading
import pandas as pd
import re
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, Response, make_response

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
        
        # Get most recent games for display
        most_recent_games = df.sort_index(ascending=False).head(5).to_dict('records')
        
        # Get top rated games by Review Count
        # First, ensure Review Count column exists and handle non-numeric values
        if 'Review Count' in df.columns:
            # Convert to numeric, coercing errors to NaN
            df['Review Count'] = pd.to_numeric(df['Review Count'], errors='coerce')
            # Filter out NaN values and sort by Review Count descending
            top_rated_df = df.dropna(subset=['Review Count']).sort_values('Review Count', ascending=False)
            top_rated_games = top_rated_df.head(5).to_dict('records')
        else:
            top_rated_games = []
        
        # Check if a background job is running
        job_status = "Running" if job_running else "Not running"
        
        # Get the model being used for wiki generation
        openai_model = "GPT-3.5"
        
        logger.info(f"Home page loaded. Total games: {game_count}, Job status: {job_status}")
        
    except Exception as e:
        logger.error(f"Error loading game data: {e}")
        game_count = 0
        most_recent_games = []
        top_rated_games = []
        job_status = "Unknown"
        openai_model = "GPT-3.5"
    
    # Pass data to template
    return render_template(
        'index.html',
        game_count=game_count,
        most_recent_games=most_recent_games,
        top_rated_games=top_rated_games,
        job_status=job_status,
        openai_model=openai_model
    )

@app.route('/games')
@app.route('/games/<int:page>')
@app.route('/games/sort/<sort_by>/<int:page>')
def games(page=1, sort_by='recent'):
    """Display all processed games with pagination."""
    try:
        # Always reload games from Excel to get the latest data
        # This ensures newly processed games appear immediately
        df = pd.read_excel(config.EXCEL_FILE_PATH, engine='openpyxl')
        
        # Convert Review Count to numeric for proper sorting
        if 'Review Count' in df.columns:
            df['Review Count'] = pd.to_numeric(df['Review Count'], errors='coerce')
        
        # Sort based on sort_by parameter
        if sort_by == 'ratings':
            # Sort by Review Count (highest first)
            df = df.sort_values('Review Count', ascending=False, na_position='last')
            logger.info("Sorting games by Review Count")
        else:
            # Default sort by most recently added (assuming the file is in chronological order)
            df = df.sort_index(ascending=False)
            logger.info("Sorting games by most recent")
        
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
            total_games=total_games,
            sort_by=sort_by
        )
        
    except Exception as e:
        logger.error(f"Error loading games: {e}")
        return render_template('games.html', games=[], page=1, total_pages=1, total_games=0, sort_by='recent')

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
            
        # Handle NaN values in columns
        for column in ['Image URL', 'Steam URL', 'Store Links']:
            if column in game.columns:
                game[column] = game[column].apply(lambda x: '' if pd.isna(x) else x)
            else:
                # Add empty column if it doesn't exist (for older data)
                game[column] = ''
            
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
        
        # If store links are missing but we have game ID, try to fetch them
        if not game_data.get('Store Links') or not game_data.get('Steam URL'):
            try:
                logger.info(f"Fetching missing store links for game {game_id}")
                game_details = rawg_api.get_game_details(game_id)
                if game_details:
                    if 'steam_url' in game_details and not game_data.get('Steam URL'):
                        game_data['Steam URL'] = game_details.get('steam_url', '')
                    
                    if 'store_links' in game_details and not game_data.get('Store Links'):
                        # Format store links
                        store_links = []
                        for store_name, url in game_details.get('store_links', {}).items():
                            if url:
                                store_links.append(f"{store_name}: {url}")
                        
                        game_data['Store Links'] = "\n".join(store_links)
            except Exception as store_error:
                logger.error(f"Error fetching store links for game {game_id}: {store_error}")
        
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
            search_results = rawg_api.search_games(query, min_reviews=1)
            
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

@app.template_filter('regex_search')
def regex_search(text, pattern):
    """Search for regex pattern in text and return all matches"""
    if not text:
        return []
    return re.findall(pattern, text)

@app.template_filter('truncate_html')
def truncate_html(html, length=200):
    """Truncate HTML text to specified length without breaking tags"""
    if not html:
        return ""
    # Simple tag stripping for truncation
    text = re.sub('<[^<]+?>', '', html)
    if len(text) <= length:
        return text
    return text[:length].rsplit(' ', 1)[0] + '...'

@app.route('/sitemap.xml')
def sitemap():
    """Generate a sitemap.xml file for search engines."""
    try:
        # Get the site URL dynamically from request
        host_url = request.host_url.rstrip('/')
        
        # Start XML content
        xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        
        # Add static pages
        now = datetime.utcnow()
        day = now.day
        day_suffix = 'th' if 11 <= day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
        today = now.strftime(f'%B {day}{day_suffix}, %Y')
        
        # Home page
        xml_content += f'  <url>\n    <loc>{host_url}/</loc>\n    <lastmod>{today}</lastmod>\n    <changefreq>daily</changefreq>\n    <priority>1.0</priority>\n  </url>\n'
        
        # Games list page
        xml_content += f'  <url>\n    <loc>{host_url}/games</loc>\n    <lastmod>{today}</lastmod>\n    <changefreq>daily</changefreq>\n    <priority>0.9</priority>\n  </url>\n'
        
        # Search page
        xml_content += f'  <url>\n    <loc>{host_url}/search</loc>\n    <lastmod>{today}</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>0.8</priority>\n  </url>\n'
        
        # Add all game detail pages
        try:
            df = pd.read_excel(config.EXCEL_FILE_PATH, engine='openpyxl')
            
            # For each game, add a URL
            for _, game in df.iterrows():
                game_id = game['Game ID']
                # Use the last modified date of the game if available, otherwise use today
                lastmod = today
                xml_content += f'  <url>\n    <loc>{host_url}/game/{game_id}</loc>\n    <lastmod>{lastmod}</lastmod>\n    <changefreq>monthly</changefreq>\n    <priority>0.7</priority>\n  </url>\n'
                
                # Add the static HTML version as well
                xml_content += f'  <url>\n    <loc>{host_url}/static-game/{game_id}.html</loc>\n    <lastmod>{lastmod}</lastmod>\n    <changefreq>monthly</changefreq>\n    <priority>0.7</priority>\n  </url>\n'
        
        except Exception as e:
            logger.error(f"Error generating game URLs for sitemap: {e}")
        
        # Close XML
        xml_content += '</urlset>'
        
        # Return XML response
        response = make_response(xml_content)
        response.headers["Content-Type"] = "application/xml"
        
        logger.info("Sitemap.xml generated successfully")
        return response
        
    except Exception as e:
        logger.error(f"Error generating sitemap: {e}")
        return Response("Error generating sitemap", status=500)

@app.route('/robots.txt')
def robots():
    """Generate a robots.txt file for search engines."""
    host_url = request.host_url.rstrip('/')
    content = f"User-agent: *\nAllow: /\nSitemap: {host_url}/sitemap.xml\n"
    response = make_response(content)
    response.headers["Content-Type"] = "text/plain"
    return response

@app.route('/static-game/<int:game_id>.html')
def static_game_page(game_id):
    """Generate a static version of the game detail page for SEO."""
    try:
        # Load the game data
        df = pd.read_excel(config.EXCEL_FILE_PATH, engine='openpyxl')
        
        # Find the game by ID
        game = df[df['Game ID'] == game_id]
        
        if len(game) == 0:
            logger.error(f"Game not found for static page: {game_id}")
            return "Game not found", 404
            
        # Handle NaN values in columns
        for column in ['Image URL', 'Steam URL', 'Store Links']:
            if column in game.columns:
                game[column] = game[column].apply(lambda x: '' if pd.isna(x) else x)
            else:
                # Add empty column if it doesn't exist (for older data)
                game[column] = ''
            
        # Convert to dictionary for template
        game_data = game.iloc[0].to_dict()
        
        # Render the template
        html_content = render_template('static_game.html', game=game_data)
        
        # Return HTML response
        response = make_response(html_content)
        response.headers["Content-Type"] = "text/html"
        
        logger.info(f"Static page generated for game: {game_data.get('Name', 'Unknown')}")
        return response
        
    except Exception as e:
        logger.error(f"Error generating static game page: {e}")
        return "Error generating page", 500

@app.route('/generate-static-pages')
def generate_all_static_pages():
    """Admin route to trigger regeneration of all static pages."""
    try:
        # This is an administrative function that could be run periodically
        # Start a background thread to generate static files
        def generate_pages_thread():
            try:
                df = pd.read_excel(config.EXCEL_FILE_PATH, engine='openpyxl')
                game_count = len(df)
                
                logger.info(f"Starting static page generation for {game_count} games")
                
                # Create the static directory if it doesn't exist
                static_dir = os.path.join(app.static_folder, 'pages')
                os.makedirs(static_dir, exist_ok=True)
                
                # For each game, generate a static HTML file
                for _, game in df.iterrows():
                    try:
                        game_id = game['Game ID']
                        
                        # Handle NaN values
                        game_data = {}
                        for column, value in game.items():
                            game_data[column] = '' if pd.isna(value) else value
                        
                        # Render the template
                        html_content = render_template('static_game.html', game=game_data)
                        
                        # Write to file
                        file_path = os.path.join(static_dir, f"{game_id}.html")
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(html_content)
                            
                        logger.info(f"Generated static page for game {game_id}: {game_data.get('Name', 'Unknown')}")
                        
                    except Exception as game_error:
                        logger.error(f"Error generating static page for game {game.get('Game ID', 'Unknown')}: {game_error}")
                
                # Generate index file
                index_html = render_template('static_index.html', games=df.to_dict('records'))
                with open(os.path.join(static_dir, "index.html"), 'w', encoding='utf-8') as f:
                    f.write(index_html)
                
                logger.info(f"Static page generation completed for {game_count} games")
                
            except Exception as e:
                logger.error(f"Error in static page generation thread: {e}")
        
        # Start the thread
        thread = threading.Thread(target=generate_pages_thread)
        thread.daemon = True
        thread.start()
        
        flash("Static page generation started. This may take a few minutes.", "info")
        return redirect(url_for('index'))
        
    except Exception as e:
        logger.error(f"Error starting static page generation: {e}")
        flash("Error starting static page generation", "error")
        return redirect(url_for('index'))

# Add the home page route
app.add_url_rule('/', 'index', index)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)