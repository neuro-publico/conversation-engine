"""Traffic-light (semáforo) thresholds for funnel analysis metrics.

The agent classifies each rate as "red" | "yellow" | "green" using these
thresholds before sending the normalized input to the LLM. Values are in
decimal form (not percentages), except rates that Meta returns as percent
strings (ctr). Keep in sync with `meta_funnel_benchmarks` in ecommerce-service
if ever split.

Inspired by the n8n workflow "Identificar constraints y prioridades" where
these thresholds were originally calibrated against dropshipping ad accounts.
"""

from typing import Dict, List, Optional

# For each metric, a list of (status, lower_bound, upper_bound_exclusive) tuples.
# Value is "red" | "yellow" | "green". Order within each list matters only for
# readability — the classifier picks the first matching range.
BenchmarkRange = Dict[str, float]
MetricBenchmarks = Dict[str, BenchmarkRange]
ProfileBenchmarks = Dict[str, MetricBenchmarks]


BENCHMARKS: Dict[str, ProfileBenchmarks] = {
    "dropshipping_prospecting": {
        "hook_rate": {
            "green_gte": 0.35,
            "yellow_gte": 0.25,
            "yellow_lt": 0.35,
            "red_lt": 0.25,
        },
        "thruplay_rate": {
            "green_gte": 0.15,
            "yellow_gte": 0.08,
            "yellow_lt": 0.15,
            "red_lt": 0.08,
        },
        "ctr": {
            # Meta returns CTR as a percent already (e.g. 1.5 = 1.5%)
            "green_gte": 1.5,
            "yellow_gte": 1.0,
            "yellow_lt": 1.5,
            "red_lt": 1.0,
        },
        "cpc": {
            # For cost metrics, lower is better — inverted comparison
            "green_lte": 0.50,
            "yellow_gt": 0.50,
            "yellow_lte": 1.00,
            "red_gt": 1.00,
        },
        "roas": {
            "green_gte": 3.0,
            "yellow_gte": 1.5,
            "yellow_lt": 3.0,
            "red_lt": 1.5,
        },
        "click_to_purchase": {
            "green_gte": 0.03,
            "yellow_gte": 0.01,
            "yellow_lt": 0.03,
            "red_lt": 0.01,
        },
    }
}


def classify_rate(profile: str, metric: str, value: float) -> str:
    """Return 'red' | 'yellow' | 'green' for the given rate value.

    Falls back to 'yellow' if the profile/metric is not defined or the value is
    not finite.
    """
    if value is None:
        return "yellow"

    profile_benchmarks = BENCHMARKS.get(profile)
    if profile_benchmarks is None:
        return "yellow"

    thresholds = profile_benchmarks.get(metric)
    if thresholds is None:
        return "yellow"

    # Cost metrics (lower is better)
    if "green_lte" in thresholds:
        if value <= thresholds["green_lte"]:
            return "green"
        if value <= thresholds.get("yellow_lte", float("inf")):
            return "yellow"
        return "red"

    # Rate metrics (higher is better)
    if value >= thresholds.get("green_gte", float("inf")):
        return "green"
    if value >= thresholds.get("yellow_gte", float("inf")):
        return "yellow"
    return "red"


def classify_all_rates(profile: str, rates: Dict[str, float]) -> Dict[str, str]:
    """Classify all provided rates using the given benchmark profile."""
    return {metric: classify_rate(profile, metric, value) for metric, value in rates.items()}


def get_profile_thresholds(profile: str) -> Optional[ProfileBenchmarks]:
    """Return the full threshold map for a profile (or None if unknown)."""
    return BENCHMARKS.get(profile)
