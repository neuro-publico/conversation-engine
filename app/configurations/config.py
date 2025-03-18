import os

from dotenv import load_dotenv

load_dotenv()

HOST_AGENT_CONFIG = os.getenv('HOST_AGENT_CONFIG')

DEEP_SEEK_HOST = os.getenv('HOST_DEEP_SEEK')

AGENT_RECOMMEND_PRODUCTS_ID = os.getenv('AGENT_RECOMMEND_PRODUCTS_ID')
AGENT_RECOMMEND_SIMILAR_PRODUCTS_ID = os.getenv('AGENT_RECOMMEND_SIMILAR_PRODUCTS_ID')
RAPIDAPI_KEY = os.getenv('RAPIDAPI_KEY')

RAPIDAPI_HOST = os.getenv('RAPIDAPI_HOST')

S3_UPLOAD_API = os.getenv('S3_UPLOAD_API')

AGENT_IMAGE_VARIATIONS = "agent_image_variations"
SCRAPER_AGENT = "scraper_agent"

AUTH_SERVICE_URL: str = os.getenv('AUTH_SERVICE_URL')

GOOGLE_VISION_API_KEY: str = os.getenv('GOOGLE_VISION_API_KEY')
REPLICATE_API_KEY: str = os.getenv('REPLICATE_API_KEY')
SCRAPERAPI_KEY: str = os.getenv('SCRAPERAPI_KEY')
URL_SCRAPER_LAMBDA: str = os.getenv('URL_SCRAPER_LAMBDA')

API_KEY: str = os.getenv('API_KEY')
GOOGLE_GEMINI_API_KEY: str = os.getenv('GOOGLE_GEMINI_API_KEY')
