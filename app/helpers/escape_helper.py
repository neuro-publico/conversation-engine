import logging
import re

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

MAX_CONTENT_CHARS = 15000

NOISE_TAGS = [
    "script",
    "style",
    "noscript",
    "svg",
    "link",
    "meta",
    "head",
    "nav",
    "footer",
    "header",
    "aside",
    "iframe",
]

NOISE_SELECTORS = [
    "[id*='review']",
    "[class*='review']",
    "[id*='related']",
    "[class*='related']",
    "[id*='recommend']",
    "[class*='recommend']",
    "[id*='sponsored']",
    "[class*='sponsored']",
    "[id*='comment']",
    "[class*='comment']",
    "[id*='sidebar']",
    "[class*='sidebar']",
    "[id*='footer']",
    "[class*='footer']",
    "[id*='nav']",
    "[class*='nav']",
    "[id*='breadcrumb']",
    "[class*='breadcrumb']",
    "[id*='cookie']",
    "[class*='cookie']",
    "[id*='banner']",
    "[class*='banner']",
    "[id*='advertisement']",
    "[class*='advertisement']",
    "[id*='ad-']",
    "[class*='ad-']",
]

PRODUCT_SELECTORS = [
    "#productTitle",
    "#title",
    "[class*='product-title']",
    "[class*='productTitle']",
    "#price",
    "#priceblock_ourprice",
    "#priceblock_dealprice",
    "[class*='price']",
    "[class*='Price']",
    "#productDescription",
    "#feature-bullets",
    "[class*='product-description']",
    "[class*='productDescription']",
    "[class*='description']",
    "#imageBlock",
    "[class*='product-image']",
    "[class*='productImage']",
    "[class*='gallery']",
    "[class*='variant']",
    "[class*='variation']",
    "[class*='option']",
    "[class*='swatch']",
    "#aplus",
    "[class*='a-plus']",
]


def truncate_content(text: str, max_chars: int = MAX_CONTENT_CHARS) -> str:
    if len(text) <= max_chars:
        return text

    truncated = text[:max_chars]
    last_space = truncated.rfind(" ")
    if last_space > max_chars * 0.8:
        truncated = truncated[:last_space]

    logger.info(f"Content truncated: {len(text)} -> {len(truncated)} chars")
    return truncated


def extract_product_content(html_content: str, max_chars: int = MAX_CONTENT_CHARS) -> str:
    soup = BeautifulSoup(html_content, "html.parser")

    for tag in soup(NOISE_TAGS):
        tag.decompose()

    for selector in NOISE_SELECTORS:
        for tag in soup.select(selector):
            tag.decompose()

    product_parts = []
    for selector in PRODUCT_SELECTORS:
        for el in soup.select(selector):
            text = el.get_text(separator=" ", strip=True)
            if text and len(text) > 3:
                product_parts.append(text)
            for img in el.find_all("img", src=True):
                product_parts.append(f'[img: {img["src"]}]')

    if product_parts:
        images = []
        for img in soup.find_all("img", src=True)[:10]:
            src = img.get("src", "")
            if src and "pixel" not in src and "blank" not in src and len(src) > 10:
                images.append(f"[img: {src}]")
        content = " ".join(product_parts) + " " + " ".join(images)
        return truncate_content(content, max_chars)

    logger.info("No product selectors matched, falling back to clean_html_deeply with truncation")
    cleaned = clean_html_deeply(html_content)
    return truncate_content(cleaned, max_chars)


def clean_placeholders(text: str, allowed_keys: list = None) -> str:
    if allowed_keys is None:
        allowed_keys = []

    def replace_placeholder(match):
        key = match.group(1).strip("\"' ")  # Remueve comillas internas
        return match.group(0) if key in allowed_keys else ""

    pattern = re.compile(r"\{\s*[\"']?([^\"'\{\}]+)[\"']?\s*\}")
    return pattern.sub(replace_placeholder, text)


def clean_html_deeply(html_content):
    soup = BeautifulSoup(html_content, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg", "link", "meta", "head"]):
        tag.decompose()

    for tag in soup.find_all(True):
        if tag.name == "img":
            tag.attrs = {key: tag.attrs[key] for key in ["src", "alt"] if key in tag.attrs}
        else:
            tag.attrs = {}

    simplified_html = str(soup)
    simplified_html_clean = re.sub(r"\s+", " ", simplified_html).strip()

    return simplified_html_clean


def clean_html_less_deeply(html_content):
    soup = BeautifulSoup(html_content, "html5lib")

    for tag in soup(["script", "style", "noscript", "svg", "link", "meta", "head"]):
        tag.decompose()

    for tag in soup.find_all(True):
        if tag.name == "img":
            tag.attrs = {key: tag.attrs[key] for key in ["src", "alt", "class", "id", "title"] if key in tag.attrs}
        elif tag.name == "a":
            tag.attrs = {key: tag.attrs[key] for key in ["href", "title", "target", "class", "id"] if key in tag.attrs}
        elif tag.name == "source":
            tag.attrs = {key: tag.attrs[key] for key in ["media", "srcset", "type"] if key in tag.attrs}
        elif tag.name == "picture":
            tag.attrs = {key: tag.attrs[key] for key in ["id", "class"] if key in tag.attrs}
        else:
            allowed_common_attrs = ["id", "class"]
            tag.attrs = {key: tag.attrs[key] for key in allowed_common_attrs if key in tag.attrs}

    simplified_html = str(soup)
    simplified_html_clean = re.sub(r"\s+", " ", simplified_html).strip()

    return simplified_html_clean
