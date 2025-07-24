from decimal import Decimal
from typing import Optional, Any
import re


def parse_price(price_str: Any) -> Optional[Decimal]:
    if isinstance(price_str, (int, float)):
        return Decimal(str(price_str))

    if isinstance(price_str, str):
        match = re.search(r"[\d,.]+", price_str)
        if match:
            num_str = match.group(0).replace(",", "")
            try:
                return Decimal(num_str)
            except:
                pass

    return None
