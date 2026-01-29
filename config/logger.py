import os
import logging
from datetime import datetime

def setup_logger(name=None):
    """
    Setup logger to write to logs directory with date in filename.
    Returns a logger instance.
    """
    # Create logs directory if it doesn't exist
    # Get project root (assuming config/logger.py -> config -> root)
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_file_dir)
    logs_dir = os.path.join(project_root, 'logs')
    
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
        
    timestamp = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(logs_dir, f"automas_{timestamp}.log")
    
    # Configure the root logger or a specific named logger
    # If name is None, it configures the root logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Check if handler already exists to avoid duplicate logs
    if not logger.handlers:
        # File Handler
        file_handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Optional: Console Handler if you want logs on stdout too
        # console_handler = logging.StreamHandler()
        # console_handler.setFormatter(formatter)
        # logger.addHandler(console_handler)
        
    return logger
