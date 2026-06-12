"""
simulator/state.py — persistent state for the stateful catch-up simulator.

A singleton row in `simulator.state` records how far the simulator has generated
data (wall-clock) and whether the 3-year bootstrap backfill has completed, so the
process can resume / catch up to NOW() after any restart without duplicating data.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import text

STATE_DDL = """
CREATE SCHEMA IF NOT EXISTS simulator;
CREATE TABLE IF NOT EXISTS simulator.state (
    id                  SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),  -- singleton
    last_generated_at   TIMESTAMPTZ,
    bootstrap_completed BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
INSERT INTO simulator.state (id) VALUES (1) ON CONFLICT DO NOTHING;
"""


def ensure_state(conn) -> None:
    """Create the state schema/table and the singleton row (idempotent)."""
    for stmt in filter(None, (s.strip() for s in STATE_DDL.split(";"))):
        conn.execute(text(stmt))


def read_state(conn) -> dict:
    row = conn.execute(text(
        "SELECT last_generated_at, bootstrap_completed FROM simulator.state WHERE id = 1"
    )).first()
    if row is None:
        return {"last_generated_at": None, "bootstrap_completed": False}
    return {"last_generated_at": row[0], "bootstrap_completed": row[1]}


def set_last_generated(conn, ts: datetime, bootstrap_completed: bool | None = None) -> None:
    """Advance the watermark. Called AFTER writes succeed, in the same transaction."""
    if bootstrap_completed is None:
        conn.execute(text(
            "UPDATE simulator.state SET last_generated_at = :ts, updated_at = NOW() WHERE id = 1"
        ), {"ts": ts})
    else:
        conn.execute(text(
            "UPDATE simulator.state SET last_generated_at = :ts, bootstrap_completed = :bc, "
            "updated_at = NOW() WHERE id = 1"
        ), {"ts": ts, "bc": bootstrap_completed})


def reset_state(conn) -> None:
    conn.execute(text(
        "UPDATE simulator.state SET last_generated_at = NULL, bootstrap_completed = FALSE, "
        "updated_at = NOW() WHERE id = 1"
    ))
