import os

from dotenv import load_dotenv

load_dotenv()

HOST_AGENT_CONFIG = os.getenv('HOST_AGENT_CONFIG')

DEEP_SEEK_HOST = os.getenv('HOST_DEEP_SEEK')

AGENT_RECOMMEND_PRODUCTS_ID = os.getenv('AGENT_RECOMMEND_PRODUCTS_ID')

RAPIDAPI_KEY = os.getenv('RAPIDAPI_KEY')

RAPIDAPI_HOST = os.getenv('RAPIDAPI_HOST')
