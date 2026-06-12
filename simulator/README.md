# NOUREDDINE Data Simulator

Generates realistic synthetic e-commerce data for the NOUREDDINE platform.

## Modes

| Mode | Command | Description |
|------|---------|-------------|
| `history` | `python generate_history.py --reset` | One-shot backfill: ~15k customers, ~300 products, ~20k orders over 3 years (2023-07-01 → today). `--reset` truncates business tables first (keeps `categories` + `calendar_events`). |
| `drip` | `python drip.py` | Continuous: inserts a small batch of new orders every `DRIP_INTERVAL_SECONDS` seconds (default 10). Makes the demo "live". |

Via Docker Compose (profile `simulator`):

```bash
# History mode (default, runs once then exits)
SIM_MODE=history docker compose --profile simulator up simulator

# Drip mode (continuous)
SIM_MODE=drip DRIP_INTERVAL_SECONDS=5 docker compose --profile simulator up simulator
```

## Seasonality logic

All Islamic calendar dates are **fixed** (never computed from Hijri algorithms):

| Event | Dates | Multiplier |
|-------|-------|-----------|
| Pre-Eid al-Fitr (14 days before) | 2024: Mar 27–Apr 9 · 2025: Mar 17–30 · 2026: Mar 6–19 | ×4.0 (Qamis/GiftSet) |
| Eid al-Fitr | 2024: Apr 10 · 2025: Mar 31 · 2026: Mar 20 | ×3.0 |
| Eid al-Adha | 2024: Jun 16 · 2025: Jun 6 · 2026: May 27 | ×2.8 (Suit/ReadyToWear) |
| Ramadan | 2024: Mar 11–Apr 9 · 2025: Mar 1–30 · 2026: Feb 18–Mar 19 | ×2.5 (Grooming/Qamis) |
| Black Friday | Last Friday of November | ×3.2 (all) |
| Nikah season | Jun 1–Aug 31 | ×2.2 (Suit/Accessory) |
| Baseline | rest of year | ×1.0 |

Multipliers are crossed with product category (see `seasonality.py`).
Additional modifiers: +15%/year growth, ±15% noise, weekend/payday uplift.

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+psycopg2://noureddine_user:change_me_postgres@postgres:5432/noureddine` | SQLAlchemy connection string |
| `MINIO_ENDPOINT` | `http://minio:9000` | MinIO S3 endpoint |
| `MINIO_ACCESS_KEY_ID` | `minio_admin` | MinIO access key |
| `MINIO_SECRET_ACCESS_KEY` | `change_me_minio` | MinIO secret key |
| `BRONZE_BUCKET` | `bronze` | S3 bucket for raw data |
| `DRIP_INTERVAL_SECONDS` | `10` | Seconds between drip batches |
| `SIM_N_CUSTOMERS` | `15000` | History mode: number of customers |
| `SIM_N_PRODUCTS` | `300` | History mode: number of products |
| `SIM_N_ORDERS` | `20000` | History mode: number of orders |
