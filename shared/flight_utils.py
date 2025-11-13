"""Shared helpers for Lufthansa Group flight logic."""

from __future__ import annotations

import re
from collections.abc import Sequence

LH_GROUP_AIRLINES: tuple[str, ...] = ("LH", "LX", "OS", "SN", "EW", "4Y", "EN")
_PRICE_PATTERN = re.compile(r"([0-9]+(?:[.,][0-9]+)?)")


def lhg_airlines_list(extra: Sequence[str] | None = None) -> list[str]:
    """Return Lufthansa Group airline codes plus any extras (deduplicated)."""

    seen: list[str] = []
    for code in LH_GROUP_AIRLINES:
        seen.append(code)
    if extra:
        for code in extra:
            normalized = code.upper()
            if normalized not in seen:
                seen.append(normalized)
    return seen


def airlines_csv(extra: Sequence[str] | None = None) -> str:
    """Return comma-separated airline codes for SearchAPI queries."""

    return ",".join(lhg_airlines_list(extra))


def normalise_price(
    raw_price: str | float | int | None,
    *,
    currency: str = "EUR",
) -> dict[str, float | str] | None:
    """Convert loosely formatted price strings into `{amount, currency}`."""

    if raw_price is None:
        return None
    if isinstance(raw_price, (int, float)):
        return {"amount": float(raw_price), "currency": currency}

    match = _PRICE_PATTERN.search(raw_price.replace("\u202f", " "))
    if not match:
        return None
    value = match.group(1).replace(",", ".")
    try:
        amount = float(value)
    except ValueError:
        return None
    inferred_currency = currency or _infer_currency_symbol(raw_price) or "EUR"
    return {"amount": amount, "currency": inferred_currency}


def _infer_currency_symbol(raw_price: str) -> str | None:
    if raw_price.strip().startswith("$"):
        return "USD"
    if raw_price.strip().startswith("£"):
        return "GBP"
    if raw_price.strip().startswith("CHF"):
        return "CHF"
    if raw_price.strip().startswith("€"):
        return "EUR"
    return None


def extract_best_price(
    flights_payload: dict[str, object],
    *,
    currency: str = "EUR",
) -> dict[str, float | str] | None:
    """Scan SearchAPI google_flights payload for the cheapest listed fare."""

    candidates = []
    for key in ("best_flights", "other_flights"):
        bucket = flights_payload.get(key)
        if isinstance(bucket, list):
            candidates.extend(bucket)

    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        price = candidate.get("price") or candidate.get("price_per_ticket")
        normalized = normalise_price(price, currency=currency)
        if normalized:
            return normalized
    return None


__all__ = [
    "LH_GROUP_AIRLINES",
    "airlines_csv",
    "extract_best_price",
    "lhg_airlines_list",
    "normalise_price",
]
