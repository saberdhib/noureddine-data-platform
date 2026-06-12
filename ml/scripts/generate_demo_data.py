"""Generate a synthetic, calendar-correlated warehouse dataset for Bloc 4.

WHY THIS EXISTS
---------------
Bloc 4 (AI/MLOps) consumes ``gold.fact_sales`` produced by the Bloc 3 pipeline
(simulator -> Airflow -> dbt). When this Bloc 4 build was started the handed-over
repository did not yet contain the Bloc 3 simulator output, so this script
populates a realistic, **fully synthetic and obviously fake** demand history so
the model has data to train on. It is a *demo fixture / stand-in for the Bloc 3
output*, not a replacement for the Bloc 3 pipeline (see ADR 0014).

It fills, idempotently:
  - oltp.categories / products / inventory
  - oltp.calendar_events  (Ramadan, Eid al-Fitr, Eid al-Adha, Nikah, Black Friday, Summer Sale)
  - gold.dim_* and gold.fact_sales  (category x day demand with calendar uplifts)

No real personal data is used (governance: seed data must be obviously fake).
"""
from __future__ import annotations

import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

import numpy as np
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from config import get_engine  # noqa: E402

RNG = np.random.default_rng(42)

# Deterministic namespace so re-runs map the same names to the same UUIDs.
NS = uuid.UUID("00000000-0000-0000-0000-0000000b10c4")

CATEGORIES = {
    # category -> (base daily units, avg price eur, avg cost eur, seasonality_tag)
    "Qamis":        (22, 120.0, 55.0, "eid_peak"),
    "Grooming":     (30, 28.0, 9.0, "ramadan_steady"),
    "Accessory":    (18, 35.0, 12.0, "gift_season"),
    "GiftSet":      (10, 95.0, 40.0, "eid_peak"),
    "ReadyToWear":  (16, 160.0, 70.0, "nikah_season"),
    "LeatherGoods": (8, 210.0, 95.0, "gift_season"),
}
CHANNELS = ["Instagram", "TikTok", "Paid Ads", "Affiliate", "Organic Search", "AI Search"]

# Approximate (real-world) Islamic calendar anchors — fixed windows, never recomputed.
RAMADAN = {  # year -> (start, end)
    2023: (date(2023, 3, 23), date(2023, 4, 20)),
    2024: (date(2024, 3, 11), date(2024, 4, 9)),
    2025: (date(2025, 3, 1), date(2025, 3, 30)),
    2026: (date(2026, 2, 18), date(2026, 3, 19)),
    2027: (date(2027, 2, 8), date(2027, 3, 9)),
}
EID_FITR = {2023: date(2023, 4, 21), 2024: date(2024, 4, 10), 2025: date(2025, 3, 31),
            2026: date(2026, 3, 20), 2027: date(2027, 3, 10)}
EID_ADHA = {2023: date(2023, 6, 28), 2024: date(2024, 6, 16), 2025: date(2025, 6, 7),
            2026: date(2026, 5, 27), 2027: date(2027, 5, 17)}


def _uid(label: str) -> uuid.UUID:
    return uuid.uuid5(NS, label)


def black_friday(year: int) -> date:
    d = date(year, 11, 30)
    while d.weekday() != 4:  # Friday
        d -= timedelta(days=1)
    return d


def build_calendar_rows():
    rows = []
    for y in range(2023, 2028):
        rs, re = RAMADAN[y]
        rows.append(("Ramadan", "religious", rs, re))
        rows.append(("Aid Al Fitr", "religious", EID_FITR[y], EID_FITR[y] + timedelta(days=2)))
        rows.append(("Aid Al Adha", "religious", EID_ADHA[y], EID_ADHA[y] + timedelta(days=3)))
        rows.append(("Nikah Season", "cultural", date(y, 6, 1), date(y, 8, 31)))
        bf = black_friday(y)
        rows.append(("Black Friday", "retail", bf, bf))
        rows.append(("Summer Sale", "retail", date(y, 7, 1), date(y, 7, 31)))
    return rows


def _in(d: date, s: date, e: date) -> bool:
    return s <= d <= e


def demand_for(category: str, base: float, d: date) -> int:
    """Calendar-driven synthetic demand with weekly seasonality + noise."""
    y = d.year
    mult = 1.0
    rs, re = RAMADAN.get(y, (date(y, 1, 1), date(y, 1, 1)))
    fitr, adha = EID_FITR.get(y), EID_ADHA.get(y)
    # Pre-Eid (14d before Eid al-Fitr) is the big spike, especially Qamis/GiftSet.
    if fitr and 0 <= (fitr - d).days <= 14:
        mult *= 2.6 if category in ("Qamis", "GiftSet", "Accessory") else 1.6
    if adha and 0 <= (adha - d).days <= 14:
        mult *= 1.9 if category in ("Qamis", "GiftSet") else 1.3
    if _in(d, rs, re):  # Ramadan steady uplift (grooming, gifting)
        mult *= 1.5 if category == "Grooming" else 1.25
    if _in(d, date(y, 6, 1), date(y, 8, 31)) and category == "ReadyToWear":  # Nikah
        mult *= 1.7
    if d == black_friday(y):                       # Black Friday spike
        mult *= 1.8
    if _in(d, date(y, 7, 1), date(y, 7, 31)):      # Summer Sale
        mult *= 1.4
    # weekly seasonality: weekend uplift
    if d.weekday() >= 5:
        mult *= 1.2
    # gentle yearly growth
    mult *= 1.0 + 0.06 * (y - 2023)
    noise = RNG.normal(1.0, 0.12)
    return max(0, int(round(base * mult * max(0.4, noise))))


def main():
    engine = get_engine()
    start = date(2023, 6, 1)
    end = date(2026, 6, 11)  # day before "today" (2026-06-12)

    with engine.begin() as conn:
        print("Resetting gold facts/dims and oltp calendar/inventory/products ...")
        conn.execute(text("TRUNCATE gold.fact_sales RESTART IDENTITY CASCADE"))
        for t in ("dim_product", "dim_date", "dim_channel", "dim_customer", "dim_calendar_event"):
            conn.execute(text(f"TRUNCATE gold.{t} RESTART IDENTITY CASCADE"))
        conn.execute(text("TRUNCATE oltp.calendar_events CASCADE"))
        conn.execute(text("DELETE FROM oltp.inventory"))
        conn.execute(text("DELETE FROM oltp.order_items"))
        conn.execute(text("DELETE FROM oltp.products"))
        conn.execute(text("DELETE FROM oltp.categories"))

        # --- oltp + dim categories/products/inventory ---
        cat_ids, prod_ids = {}, {}
        for cat, (_b, price, cost, season) in CATEGORIES.items():
            cid = _uid(f"cat:{cat}")
            cat_ids[cat] = cid
            conn.execute(text("INSERT INTO oltp.categories(category_id, category_name) VALUES (:i,:n)"),
                         {"i": str(cid), "n": cat})
            pid = _uid(f"prod:{cat}")
            prod_ids[cat] = pid
            conn.execute(text(
                "INSERT INTO oltp.products(product_id, sku, product_name, category_id, price_eur, cost_eur, seasonality_tag) "
                "VALUES (:i,:s,:n,:c,:p,:co,:se)"),
                {"i": str(pid), "s": f"SKU-{cat[:4].upper()}-001", "n": f"{cat} Signature",
                 "c": str(cat_ids[cat]), "p": price, "co": cost, "se": season})
            # inventory tuned so Stock Pilot shows a mix of green/orange/red signals
            stock = int(RNG.integers(60, 900))
            conn.execute(text(
                "INSERT INTO oltp.inventory(product_id, stock_quantity, reorder_threshold) VALUES (:i,:q,:t)"),
                {"i": str(pid), "q": stock, "t": 50})

        # --- gold dim_channel / dim_customer (synthetic, non-PII keys) ---
        for ch in CHANNELS:
            conn.execute(text("INSERT INTO gold.dim_channel(channel_name) VALUES (:n)"), {"n": ch})
        chan_keys = {r[1]: r[0] for r in conn.execute(text("SELECT channel_key, channel_name FROM gold.dim_channel"))}
        # one anonymous aggregate customer bucket (no PII; fact needs a key)
        anon_cust = _uid("customer:anon-aggregate")
        conn.execute(text(
            "INSERT INTO gold.dim_customer(customer_id, country, city, segment, acquisition_source) "
            "VALUES (:i,'FR','Paris','aggregate','mixed')"), {"i": str(anon_cust)})
        cust_key = conn.execute(text("SELECT customer_key FROM gold.dim_customer LIMIT 1")).scalar()

        # --- gold dim_product ---
        for cat in CATEGORIES:
            conn.execute(text(
                "INSERT INTO gold.dim_product(product_id, sku, product_name, category, seasonality_tag) "
                "VALUES (:i,:s,:n,:c,:se)"),
                {"i": str(prod_ids[cat]), "s": f"SKU-{cat[:4].upper()}-001",
                 "n": f"{cat} Signature", "c": cat, "se": CATEGORIES[cat][3]})
        prod_keys = {r[1]: r[0] for r in conn.execute(text("SELECT product_key, category FROM gold.dim_product"))}

        # --- oltp.calendar_events + gold.dim_calendar_event ---
        cal_event_keys = {}
        for name, etype, s, e in build_calendar_rows():
            conn.execute(text(
                "INSERT INTO oltp.calendar_events(event_name, event_type, start_date, end_date) "
                "VALUES (:n,:t,:s,:e)"), {"n": name, "t": etype, "s": s, "e": e})
        for name, etype in {(n, t) for n, t, _, _ in build_calendar_rows()}:
            ceid = _uid(f"cal:{name}")
            conn.execute(text(
                "INSERT INTO gold.dim_calendar_event(calendar_event_id, event_name, event_type) "
                "VALUES (:i,:n,:t)"), {"i": str(ceid), "n": name, "t": etype})
        for r in conn.execute(text("SELECT calendar_event_key, event_name FROM gold.dim_calendar_event")):
            cal_event_keys[r[1]] = r[0]

        # --- dim_date ---
        d = start
        date_keys = {}
        date_rows = []
        while d <= end:
            iso = d.isocalendar()
            date_rows.append({"d": d, "day": d.day, "week": iso.week, "month": d.month,
                              "q": (d.month - 1) // 3 + 1, "y": d.year, "we": d.weekday() >= 5})
            d += timedelta(days=1)
        conn.execute(text(
            "INSERT INTO gold.dim_date(date, day, week, month, quarter, year, is_weekend) "
            "VALUES (:d,:day,:week,:month,:q,:y,:we)"), date_rows)
        for r in conn.execute(text("SELECT date_key, date FROM gold.dim_date")):
            date_keys[r[1]] = r[0]

        # --- fact_sales (category x day, multiple orders/day) ---
        print("Generating fact_sales ...")
        fact_rows = []
        d = start
        while d <= end:
            dk = date_keys[d]
            for cat, (base, price, cost, _s) in CATEGORIES.items():
                units = demand_for(cat, base, d)
                if units <= 0:
                    continue
                # split daily units across a few orders
                n_orders = int(RNG.integers(1, 5))
                remaining = units
                for o in range(n_orders):
                    q = remaining if o == n_orders - 1 else max(1, int(remaining / (n_orders - o)))
                    remaining -= q
                    if q <= 0:
                        continue
                    rev = round(q * price * RNG.uniform(0.92, 1.05), 2)
                    disc = round(rev * RNG.uniform(0.0, 0.12), 2)
                    margin = round(rev - disc - q * cost, 2)
                    fact_rows.append({
                        "oid": str(uuid.uuid4()), "ck": cust_key, "pk": prod_keys[cat],
                        "dk": dk, "chk": int(RNG.choice(list(chan_keys.values()))),
                        "cek": None, "q": int(q), "rev": rev, "disc": disc,
                        "ship": round(RNG.uniform(0, 8), 2), "margin": margin,
                    })
                if remaining > 0:
                    fact_rows[-1]["q"] += int(remaining)
            d += timedelta(days=1)

        # bulk insert in chunks
        ins = text(
            "INSERT INTO gold.fact_sales(order_id, customer_key, product_key, date_key, channel_key, "
            "calendar_event_key, quantity, revenue, discount, shipping_cost, margin) "
            "VALUES (:oid,:ck,:pk,:dk,:chk,:cek,:q,:rev,:disc,:ship,:margin)")
        for i in range(0, len(fact_rows), 2000):
            conn.execute(ins, fact_rows[i:i + 2000])
        print(f"Inserted {len(fact_rows)} fact_sales rows over {(end - start).days + 1} days.")

    with engine.connect() as conn:
        n_fact = conn.execute(text("SELECT count(*) FROM gold.fact_sales")).scalar()
        n_cal = conn.execute(text("SELECT count(*) FROM oltp.calendar_events")).scalar()
        print(f"DONE. gold.fact_sales={n_fact}  oltp.calendar_events={n_cal}")


if __name__ == "__main__":
    main()
