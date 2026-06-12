"""Seed a punchy "pre-Eid" demo scenario for the soutenance.

Builds the warehouse with data ending ~14 days before **Eid al-Adha 2026
(2026-05-27)** and a **tight inventory**, so that:
  * the J+30 forecast (anchored at end+1) straddles the Eid demand spike,
  * days-of-cover for the Eid-driven categories falls **below the restock lead
    time** → the Stock Pilot / AI Advisor flag "rupture avant livraison" and
    recommend ordering now.

After running this, retrain the model and the Streamlit pages auto-align (they
anchor "today" on the data frontier via db.data_today()):

    python ml/scripts/seed_demo_pre_eid.py
    python ml/src/train.py            # (or trigger the retrain_model DAG)
    # open Streamlit -> 🤖 AI Advisor  (set RESTOCK_LEAD_TIME_DAYS, e.g. 21)

Synthetic + obviously fake data only (governance preserved).
"""
from datetime import date

from generate_demo_data import main

# 14 days before Eid al-Adha 2026 (2026-05-27): data ends 2026-05-13, forecast
# from 2026-05-14 covers the pre-Eid ramp + the Eid spike.
PRE_EID_END = date(2026, 5, 13)

if __name__ == "__main__":
    print(f"Seeding pre-Eid demo: data ends {PRE_EID_END} (Eid al-Adha 2026-05-27), tight inventory.")
    main(end_date=PRE_EID_END, tight_inventory=True)
