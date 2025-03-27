import os
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logger():
    """Set up and configure the application logger.
    
    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Create a unique log file name with timestamp
    timestamp = datetime.now().strftime("%Y%m%d")
    log_file = log_dir / f"game_wiki_generator_{timestamp}.log"
    
    # Configure logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)
    
    # Create file handler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)
    
    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    logger.info("Logger initialized")
    return logger
