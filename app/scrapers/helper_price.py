from decimal import Decimal
from typing import Optional, Any


def parse_price(price_str: Any) -> Optional[Decimal]:
    if isinstance(price_str, (int, float)):
        return Decimal(str(price_str))

    if isinstance(price_str, str):
        clean_price = price_str.replace("$", "").replace(",", "").strip()
        try:
            return Decimal(clean_price)
        except:
            pass

    return None
