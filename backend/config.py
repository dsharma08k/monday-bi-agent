"""
Configuration module for the Monday.com BI Agent backend.
Loads environment variables from .env file and exposes them as importable constants.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
load_dotenv()

# Monday.com API Configuration
MONDAY_API_TOKEN: str = os.getenv("MONDAY_API_TOKEN", "")
MONDAY_DEALS_BOARD_ID: str = os.getenv("MONDAY_DEALS_BOARD_ID", "")
MONDAY_WORKORDERS_BOARD_ID: str = os.getenv("MONDAY_WORKORDERS_BOARD_ID", "")

# Groq API Configuration
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

# Monday.com API Base URL
MONDAY_API_URL: str = "https://api.monday.com/v2"
