"""
Tests para helper_price.
Verifica el parseo correcto de precios en diferentes formatos.
"""

from decimal import Decimal

import pytest

from app.scrapers.helper_price import parse_price


class TestParsePrice:
    """Tests para la función parse_price."""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "input_value,expected",
        [
            # Números directos
            (10, Decimal("10")),
            (10.99, Decimal("10.99")),
            (0, Decimal("0")),
            (0.01, Decimal("0.01")),
            # Strings simples
            ("10", Decimal("10")),
            ("10.99", Decimal("10.99")),
            ("0.99", Decimal("0.99")),
            # Con símbolos de moneda
            ("$10.99", Decimal("10.99")),
            ("€29.99", Decimal("29.99")),
            ("£15.50", Decimal("15.50")),
            ("US$25.00", Decimal("25.00")),
            # Con comas
            ("1,234.56", Decimal("1234.56")),
            ("10,99", Decimal("1099")),  # Comas se remueven
            # Con espacios y texto
            ("Price: $49.99", Decimal("49.99")),
            ("  $10.99  ", Decimal("10.99")),
        ],
    )
    def test_parse_price_valid_inputs(self, input_value, expected):
        """Debe parsear correctamente diferentes formatos de precio válidos."""
        result = parse_price(input_value)
        assert result == expected

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "input_value",
        [
            None,
            "",
            "   ",
            "invalid",
            "N/A",
            "Free",
            [],
            {},
        ],
    )
    def test_parse_price_invalid_inputs_return_none(self, input_value):
        """Debe retornar None para valores inválidos."""
        result = parse_price(input_value)
        assert result is None

    @pytest.mark.unit
    def test_parse_price_with_integer(self):
        """Debe manejar enteros correctamente."""
        assert parse_price(100) == Decimal("100")
        assert parse_price(0) == Decimal("0")

    @pytest.mark.unit
    def test_parse_price_with_float(self):
        """Debe manejar flotantes correctamente."""
        result = parse_price(99.99)
        assert result == Decimal("99.99")

    @pytest.mark.unit
    def test_parse_price_extracts_first_number(self):
        """Debe extraer el primer número encontrado en el string."""
        result = parse_price("From $10.99 to $20.99")
        assert result == Decimal("10.99")

    @pytest.mark.unit
    def test_parse_price_handles_large_numbers(self):
        """Debe manejar números grandes."""
        result = parse_price("$1,234,567.89")
        assert result == Decimal("1234567.89")

    @pytest.mark.unit
    def test_parse_price_handles_small_decimals(self):
        """Debe manejar decimales pequeños."""
        result = parse_price("$0.01")
        assert result == Decimal("0.01")
