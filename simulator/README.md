# NOUREDDINE Data Simulator (Bloc 3)

Generates realistic **synthetic** e-commerce data for the NOUREDDINE platform.
One process, one source of truth: `simulator/run.py` with **stateful catch-up**.

## How it works

The simulator always brings `oltp` (and the `bronze` lake) up to wall-clock `NOW()`:

| State | Behaviour |
|-------|-----------|
| First run (empty `simulator.state`) | **Bootstrap**: upsert the fixed Islamic-calendar windows, create reference customers/products/inventory, and backfill ~3 years of orders (`NOW-3y .. NOW`). |
| Every run after | **Catch-up**: generate only the missing slice `(last_generated_at, NOW]`, then advance the watermark. |

State lives in a singleton row in `simulator.state` (`last_generated_at`,
`bootstrap_completed`). The watermark is advanced **after** the writes commit,
in the same transaction, so a restart resumes exactly where it left off.

**Idempotency** — order/line/shipment IDs are derived deterministically from the
hour bucket (`uuid5`), so re-processing an overlapping window inserts nothing new
(`ON CONFLICT DO NOTHING`). You cannot regenerate the same hour twice.

## Run

```bash
# Loop forever (the compose service): bootstrap then catch up every CATCH_UP_INTERVAL_SECONDS
python -m simulator.run

# Single bootstrap-or-catch-up cycle then exit (cron / CI / demo)
python -m simulator.run --once

# Wipe business tables + reset state, then re-bootstrap
python -m simulator.run --reset --once
```

Via Docker Compose (no `SIM_MODE` any more — it just runs):

```bash
docker compose -f infra/docker-compose.yml up -d simulator
docker logs -f noureddine_simulator        # watch bootstrap / catch-up
```

## Demand model (`seasonality.py`)

All Islamic calendar dates are **fixed** (never computed from Hijri algorithms).
Per-day demand = base × calendar-event multiplier (× product category) × +15%/yr
growth × weekend/payday uplift × ±15% noise, then spread across the day by an
**hour-of-day** weighting (overnight dip, 18:00–22:00 evening peak).

| Event | Window (examples) | Multiplier |
|-------|-------------------|-----------|
| Pre-Eid al-Fitr (14d before) | 2025: Mar 17–30 · 2026: Mar 6–19 | ×4.0 (Qamis/GiftSet) |
| Eid al-Fitr | 2025: Mar 31 · 2026: Mar 20 | ×3.0 |
| Eid al-Adha | 2025: Jun 6 · 2026: May 27 | ×2.8 (Suit/ReadyToWear) |
| Ramadan | 2025: Mar 1–30 · 2026: Feb 18–Mar 19 | ×2.5 (Grooming/Qamis) |
| Black Friday | Last Friday of November | ×3.2 |
| Nikah season | Jun 1–Aug 31 | ×2.2 (Suit/Accessory) |
| Baseline | rest of year | ×1.0 |

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+psycopg2://noureddine_user:change_me_postgres@postgres:5432/noureddine` | SQLAlchemy connection |
| `MINIO_ENDPOINT` | `http://minio:9000` | MinIO S3 endpoint (bronze writes are best-effort, fail-fast) |
| `MINIO_ACCESS_KEY_ID` / `MINIO_SECRET_ACCESS_KEY` | `minio_admin` / `change_me_minio` | MinIO credentials |
| `BRONZE_BUCKET` | `bronze` | Raw-data bucket; objects partitioned `orders/year=YYYY/month=MM/day=DD/` |
| `CATCH_UP_INTERVAL_SECONDS` | `600` | Seconds between catch-up cycles (loop mode) |
| `SIM_BACKFILL_YEARS` | `3` | Bootstrap backfill span |
| `SIM_BASE_DAILY_ORDERS` | `15` | Baseline orders/day before seasonality |
| `SIM_N_CUSTOMERS` / `SIM_N_PRODUCTS` | `8000` / `300` | Reference actors created on bootstrap |

> Replaces the old `generate_history.py` (history) + `drip.py` (drip) two-mode
> design with a single stateful process — see AUDIT_REPORT.md (Fix 1). Calendar
> windows come only from `seasonality.py`.
