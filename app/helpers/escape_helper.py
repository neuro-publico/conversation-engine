import re
from bs4 import BeautifulSoup


def clean_placeholders(text: str, allowed_keys: list = None) -> str:
    if allowed_keys is None:
        allowed_keys = []

    def replace_placeholder(match):
        key = match.group(1).strip('"\' ')  # Remueve comillas internas
        return match.group(0) if key in allowed_keys else ""

    pattern = re.compile(r"\{\s*[\"']?([^\"'\{\}]+)[\"']?\s*\}")
    return pattern.sub(replace_placeholder, text)


def clean_html_deeply(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')

    for tag in soup(['script', 'style', 'noscript', 'svg', 'link', 'meta', 'head']):
        tag.decompose()

    for tag in soup.find_all(True):
        if tag.name == 'img':
            tag.attrs = {key: tag.attrs[key] for key in ['src', 'alt'] if key in tag.attrs}
        else:
            tag.attrs = {}

    simplified_html = str(soup)
    simplified_html_clean = re.sub(r'\s+', ' ', simplified_html).strip()

    return simplified_html_clean
