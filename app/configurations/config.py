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
SCRAPER_AGENT_DIRECT = "scraper_agent_direct_code"

AUTH_SERVICE_URL: str = os.getenv('AUTH_SERVICE_URL')

GOOGLE_VISION_API_KEY: str = os.getenv('GOOGLE_VISION_API_KEY')
REPLICATE_API_KEY: str = os.getenv('REPLICATE_API_KEY')
SCRAPERAPI_KEY: str = os.getenv('SCRAPERAPI_KEY')
URL_SCRAPER_LAMBDA: str = os.getenv('URL_SCRAPER_LAMBDA')

API_KEY: str = os.getenv('API_KEY')
GOOGLE_GEMINI_API_KEY: str = os.getenv('GOOGLE_GEMINI_API_KEY')

ENVIRONMENT: str = os.getenv('ENVIRONMENT')

OPENAI_API_KEY: str = os.getenv('OPENAI_API_KEY')

DROPI_S3_BASE_URL: str = os.getenv('DROPI_S3_BASE_URL', 'https://d39ru7awumhhs2.cloudfront.net/')
DROPI_HOST: str = os.getenv('DROPI_HOST', 'https://test-api.dropi.co')
DROPI_API_KEY: str = os.getenv('DROPI_API_KEY')
DROPI_API_KEY_CO: str = os.getenv('DROPI_API_KEY_CO', os.getenv('DROPI_API_KEY'))
DROPI_API_KEY_MX: str = os.getenv('DROPI_API_KEY_MX', os.getenv('DROPI_API_KEY'))
DROPI_API_KEY_AR: str = os.getenv('DROPI_API_KEY_AR', os.getenv('DROPI_API_KEY'))
DROPI_API_KEY_CL: str = os.getenv('DROPI_API_KEY_CL', os.getenv('DROPI_API_KEY'))
DROPI_API_KEY_PE: str = os.getenv('DROPI_API_KEY_PE', os.getenv('DROPI_API_KEY'))
DROPI_API_KEY_PY: str = os.getenv('DROPI_API_KEY_PY', os.getenv('DROPI_API_KEY'))
DROPI_API_KEY_EC: str = os.getenv('DROPI_API_KEY_EC', os.getenv('DROPI_API_KEY'))


def get_dropi_api_key(country: str = "co") -> str:
    country_keys = {
        "co": DROPI_API_KEY_CO,
        "mx": DROPI_API_KEY_MX,
        "ar": DROPI_API_KEY_AR,
        "cl": DROPI_API_KEY_CL,
        "pe": DROPI_API_KEY_PE,
        "py": DROPI_API_KEY_PY,
        "ec": DROPI_API_KEY_EC,
    }
    return country_keys.get(country.lower(), DROPI_API_KEY)


FAL_AI_API_KEY: str = os.getenv('FAL_AI_API_KEY')
