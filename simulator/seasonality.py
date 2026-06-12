"""
Demand multiplier model — NOUREDDINE data platform.
Uses ONLY fixed calendar windows from CLAUDE.md. Never compute Hijri dates.
"""
import random
from datetime import date, timedelta

# Fixed Islamic calendar windows (civil dates) — NEVER guess or compute
CALENDAR_EVENTS = [
    # Ramadan 2024
    {"name": "Ramadan 2024", "type": "ramadan", "start": date(2024, 3, 11), "end": date(2024, 4, 9)},
    {"name": "Eid al-Fitr 2024", "type": "eid_fitr", "start": date(2024, 4, 10), "end": date(2024, 4, 10)},
    {"name": "Pre-Eid al-Fitr 2024", "type": "pre_eid_fitr", "start": date(2024, 3, 27), "end": date(2024, 4, 9)},
    {"name": "Eid al-Adha 2024", "type": "eid_adha", "start": date(2024, 6, 16), "end": date(2024, 6, 16)},
    # Ramadan 2025
    {"name": "Ramadan 2025", "type": "ramadan", "start": date(2025, 3, 1), "end": date(2025, 3, 30)},
    {"name": "Eid al-Fitr 2025", "type": "eid_fitr", "start": date(2025, 3, 31), "end": date(2025, 3, 31)},
    {"name": "Pre-Eid al-Fitr 2025", "type": "pre_eid_fitr", "start": date(2025, 3, 17), "end": date(2025, 3, 30)},
    {"name": "Eid al-Adha 2025", "type": "eid_adha", "start": date(2025, 6, 6), "end": date(2025, 6, 6)},
    # Ramadan 2026
    {"name": "Ramadan 2026", "type": "ramadan", "start": date(2026, 2, 18), "end": date(2026, 3, 19)},
    {"name": "Eid al-Fitr 2026", "type": "eid_fitr", "start": date(2026, 3, 20), "end": date(2026, 3, 20)},
    {"name": "Pre-Eid al-Fitr 2026", "type": "pre_eid_fitr", "start": date(2026, 3, 6), "end": date(2026, 3, 19)},
    {"name": "Eid al-Adha 2026", "type": "eid_adha", "start": date(2026, 5, 27), "end": date(2026, 5, 27)},
]

# Multipliers per event type x product category
MULTIPLIERS = {
    "pre_eid_fitr": {"Qamis": 4.0, "GiftSet": 4.0, "Grooming": 3.5, "Accessory": 3.0, "ReadyToWear": 3.0, "Suit": 2.5, "LeatherGoods": 2.5, "default": 4.0},
    "ramadan":      {"Grooming": 2.5, "Qamis": 2.5, "ReadyToWear": 2.5, "GiftSet": 2.0, "Accessory": 1.8, "Suit": 1.5, "LeatherGoods": 1.5, "default": 2.5},
    "eid_adha":     {"Suit": 2.8, "ReadyToWear": 2.8, "Qamis": 2.5, "Accessory": 2.5, "LeatherGoods": 2.5, "GiftSet": 2.0, "Grooming": 1.8, "default": 2.8},
    "eid_fitr":     {"Qamis": 3.0, "GiftSet": 3.0, "Grooming": 2.5, "Accessory": 2.5, "ReadyToWear": 2.5, "Suit": 2.0, "LeatherGoods": 2.0, "default": 3.0},
    "nikah":        {"Suit": 2.2, "Accessory": 2.2, "LeatherGoods": 2.2, "ReadyToWear": 1.8, "GiftSet": 1.8, "Qamis": 1.5, "Grooming": 1.5, "default": 2.2},
    "black_friday": {"default": 3.2},
}

BASE_YEAR = 2023
GROWTH_RATE = 0.15  # +15%/year


def _nikah_season(d: date) -> bool:
    return 6 <= d.month <= 8


def _black_friday(d: date) -> bool:
    # Last Friday of November
    nov_last = date(d.year, 11, 30)
    while nov_last.weekday() != 4:  # 4 = Friday
        nov_last -= timedelta(days=1)
    return d == nov_last


def _get_event_type(d: date):
    # Check pre_eid_fitr first (subset of ramadan, higher priority)
    for ev in CALENDAR_EVENTS:
        if ev["type"] == "pre_eid_fitr" and ev["start"] <= d <= ev["end"]:
            return "pre_eid_fitr"
    for ev in CALENDAR_EVENTS:
        if ev["type"] == "eid_fitr" and ev["start"] <= d <= ev["end"]:
            return "eid_fitr"
        if ev["type"] == "eid_adha" and ev["start"] <= d <= ev["end"]:
            return "eid_adha"
        if ev["type"] == "ramadan" and ev["start"] <= d <= ev["end"]:
            return "ramadan"
    if _black_friday(d):
        return "black_friday"
    if _nikah_season(d):
        return "nikah"
    return None


def demand_multiplier(d: date, category: str = "default") -> float:
    event_type = _get_event_type(d)
    if event_type:
        mults = MULTIPLIERS[event_type]
        base = mults.get(category, mults["default"])
    else:
        base = 1.0

    # Growth trend
    years_since_base = (d.year - BASE_YEAR) + (d.month - 7) / 12.0
    growth = (1 + GROWTH_RATE) ** max(0, years_since_base)

    # Weekend uplift
    weekend = 1.1 if d.weekday() >= 5 else 1.0

    # Payday uplift (1st and 15th of month)
    payday = 1.08 if d.day in (1, 15) else 1.0

    # Noise +/-15%
    noise = random.uniform(0.85, 1.15)

    return base * growth * weekend * payday * noise


def get_calendar_event_name(d: date):
    """Returns the canonical event name for Grafana/reporting."""
    event_type = _get_event_type(d)
    if event_type == "pre_eid_fitr":
        for ev in CALENDAR_EVENTS:
            if ev["type"] == "pre_eid_fitr" and ev["start"] <= d <= ev["end"]:
                return ev["name"]
    if event_type:
        for ev in CALENDAR_EVENTS:
            if ev["type"] == event_type and ev["start"] <= d <= ev["end"]:
                return ev["name"]
    if _nikah_season(d):
        return f"Nikah Season {d.year}"
    if _black_friday(d):
        return f"Black Friday {d.year}"
    return None
