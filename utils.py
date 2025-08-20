import os
from dotenv import load_dotenv

def get_openai_api_key():
    """
    Get OpenAI API key from environment variables or .env file
    """
    load_dotenv()
    
    # Try to get from environment variable first
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        # Try to get from .env file
        api_key = os.getenv("OPENAI_API_KEY")
        
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY not found. Please set it as an environment variable "
            "or in a .env file in your project directory."
        )
    
    return api_key

def get_serper_api_key():
    """
    Get Serper API key from environment variables or .env file
    """
    load_dotenv()
    
    # Try to get from environment variable first
    api_key = os.getenv("SERPER_API_KEY")
    
    if not api_key:
        # Try to get from .env file
        api_key = os.getenv("SERPER_API_KEY")
        
    if not api_key:
        raise ValueError(
            "SERPER_API_KEY not found. Please set it as an environment variable "
            "or in a .env file in your project directory."
        )
    
    return api_key