"""
Configuration module for the AI Sales Agent Application.

Author: Ben Walker (BenRWalker@icloud.com)
"""

# Modules
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv
from logger_config import setup_logger

# Set up logger for this module
logger = setup_logger(__name__)

def setup_env():
    """ Load environment variables from a .env file """
    load_dotenv()
    logger.info("Environment variables loaded from .env file")

# API Configuration
LLM_API_KEY = os.environ.get('LLM_API_KEY')
LLM_API_URL = os.environ.get('LLM_API_URL')

logger.info(f"Configuration module initialized with base url: {LLM_API_URL}")

# Create LLM client
try:
    ollama_client = AsyncOpenAI(
        base_url=LLM_API_URL,
        api_key=LLM_API_KEY
    )
    logger.info("Ollama client configured successfully")
except Exception as e:
    logger.error(f"Failed to configure Ollama client: {e}", exc_info=True)
    raise