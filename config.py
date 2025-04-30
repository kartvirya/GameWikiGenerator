import os
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load environment variables from .env file
except ImportError:
    print("dotenv package not found. Environment variables must be set manually.")

class Config:
    """Configuration settings for the Game Wiki Generator."""
    
    def __init__(self):
        # API Keys
        self.RAWG_API_KEY = os.getenv("RAWG_API_KEY", "")
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        
        # Ensure API keys are provided
        if not self.RAWG_API_KEY:
            raise ValueError("RAWG API key is required. Set the RAWG_API_KEY environment variable.")
        
        if not self.OPENAI_API_KEY:
            raise ValueError("OpenAI API key is required. Set the OPENAI_API_KEY environment variable.")
        
        # File paths
        self.BASE_DIR = Path.cwd()
        self.DATA_DIR = self.BASE_DIR / "data"
        self.DATA_DIR.mkdir(exist_ok=True)
        
        timestamp = ""  # Use empty string for a single file
        self.EXCEL_FILE_PATH = str(self.DATA_DIR / f"game_wiki{timestamp}.xlsx")
        
        # API configuration
        self.RAWG_BASE_URL = "https://api.rawg.io/api"
        self.OPENAI_MODEL = "gpt-3.5-turbo-instruct"  # Using the fastest model for maximum speed
        
        # Request limits
        self.DAILY_REQUEST_LIMIT = 10000  # Increased for rapid processing
        
        # Wiki generation settings
        self.MIN_PARAGRAPHS = 1  # Minimum for faster generation
        self.MAX_PARAGRAPHS = 2  # Minimum for faster generation
        
        # Rapid processing settings
        self.RAPID_MODE = os.getenv("RAPID_MODE", "False").lower() == "true"
        self.PARALLEL_REQUESTS = 25  # Increased parallel requests
        self.REQUEST_DELAY = 0.05  # Minimal delay
        self.PAGE_SIZE = 50  # Larger page size for fetching games
        self.BATCH_SIZE = 200  # Larger batch size
