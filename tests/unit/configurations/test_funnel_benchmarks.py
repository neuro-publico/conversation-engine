import pytest

from app.configurations.funnel_benchmarks import classify_all_rates, classify_rate

PROFILE = "dropshipping_prospecting"


class TestClassifyRate:
    """Traffic-light classifier for individual rates."""

    # hook_rate: red < 0.25, yellow [0.25, 0.35), green >= 0.35
    @pytest.mark.parametrize(
        "value,expected",
        [
            (0.10, "red"),
            (0.24, "red"),
            (0.25, "yellow"),
            (0.30, "yellow"),
            (0.34, "yellow"),
            (0.35, "green"),
            (0.50, "green"),
        ],
    )
    def test_hook_rate(self, value, expected):
        assert classify_rate(PROFILE, "hook_rate", value) == expected

    # cpc: green <= 0.50, yellow (0.50, 1.00], red > 1.00
    @pytest.mark.parametrize(
        "value,expected",
        [
            (0.30, "green"),
            (0.50, "green"),
            (0.51, "yellow"),
            (1.00, "yellow"),
            (1.01, "red"),
            (2.50, "red"),
        ],
    )
    def test_cpc_cost_metric(self, value, expected):
        assert classify_rate(PROFILE, "cpc", value) == expected

    # roas: red < 1.5, yellow [1.5, 3.0), green >= 3.0
    @pytest.mark.parametrize(
        "value,expected",
        [
            (0.5, "red"),
            (1.49, "red"),
            (1.5, "yellow"),
            (2.5, "yellow"),
            (3.0, "green"),
            (5.0, "green"),
        ],
    )
    def test_roas(self, value, expected):
        assert classify_rate(PROFILE, "roas", value) == expected

    def test_unknown_metric_returns_yellow(self):
        assert classify_rate(PROFILE, "nonexistent_metric", 0.5) == "yellow"

    def test_unknown_profile_returns_yellow(self):
        assert classify_rate("nonexistent_profile", "hook_rate", 0.5) == "yellow"

    def test_none_value_returns_yellow(self):
        assert classify_rate(PROFILE, "hook_rate", None) == "yellow"


class TestClassifyAllRates:
    def test_all_rates_mixed(self):
        rates = {
            "hook_rate": 0.40,  # green
            "ctr": 0.8,  # red (< 1.0)
            "cpc": 0.75,  # yellow
            "roas": 2.0,  # yellow
        }
        result = classify_all_rates(PROFILE, rates)
        assert result == {
            "hook_rate": "green",
            "ctr": "red",
            "cpc": "yellow",
            "roas": "yellow",
        }

    def test_empty_rates_returns_empty(self):
        assert classify_all_rates(PROFILE, {}) == {}
