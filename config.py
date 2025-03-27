import os
from pathlib import Path

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
        self.OPENAI_MODEL = "gpt-4o"  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        
        # Request limits
        self.DAILY_REQUEST_LIMIT = 800  # Maximum requests per day
        
        # Wiki generation settings
        self.MIN_PARAGRAPHS = 3
        self.MAX_PARAGRAPHS = 5
