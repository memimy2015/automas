import os
import sys

# Add project root to sys.path
# File path: /Users/bytedance/automas/resources/tools/file_operation.py
# Project root: /Users/bytedance/automas
# current_dir = os.path.dirname(os.path.abspath(__file__)) # resources/tools
# resources_dir = os.path.dirname(current_dir) # resources
# automas_dir = os.path.dirname(resources_dir) # automas
# if automas_dir not in sys.path:
#     sys.path.insert(0, automas_dir)

from config.logger import setup_logger

logger = setup_logger("FileOperation")

def read_file(file_path):
    """
    Reads the content of a file.
    
    Args:
        file_path (str): The path to the file to read.
        
    Returns:
        str: The content of the file.
        
    Raises:
        FileNotFoundError: If the file does not exist.
        IOError: If there is an error reading the file.
    """
    logger.info(f"Reading file: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            logger.info(f"Successfully read {len(content)} characters from {file_path}")
            return content
    except Exception as e:
        error_msg = f"Error reading file {file_path}: {e}"
        logger.error(error_msg)
        return error_msg

def write_file(file_path, content):
    """
    Writes content to a file. Creates directories if they don't exist.
    
    Args:
        file_path (str): The path to the file to write.
        content (str): The content to write to the file.
        
    Returns:
        str: Success message or error message.
    """
    logger.info(f"Writing to file: {file_path}")
    try:
        # Create directory if it doesn't exist
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            logger.info(f"Creating directory: {directory}")
            os.makedirs(directory)
            
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        success_msg = f"Successfully wrote to {file_path}"
        logger.info(success_msg)
        return success_msg
    except Exception as e:
        error_msg = f"Error writing to file {file_path}: {e}"
        logger.error(error_msg)
        return error_msg

# if __name__ == "__main__":
#     # Test cases
#     test_file = "test_output/test.txt"
#     print(write_file(test_file, "Hello, World!"))
#     print(read_file(test_file))
