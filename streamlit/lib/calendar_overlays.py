"""Islamic-calendar Plotly overlays for the Demand Forecast chart (Bloc 4).

Reads governed windows from ``oltp.calendar_events`` and returns Plotly shapes /
annotations so the signature forecast chart shows demand peaks *in context*:
  - Ramadan        -> gold band (opacity 0.15)
  - Eid al-Fitr    -> red dashed vertical line + annotation
  - Eid al-Adha    -> teal dashed vertical line + annotation
  - Nikah season   -> lighter purple band (opacity 0.10)
  - Black Friday   -> marker / dark dashed line + annotation
"""
from __future__ import annotations

import pandas as pd

STYLES = {
    "ramadan": dict(fillcolor="gold", opacity=0.15, line_width=0),
    "nikah": dict(fillcolor="mediumpurple", opacity=0.10, line_width=0),
    "eid_fitr": dict(color="crimson"),
    "eid_adha": dict(color="teal"),
    "black_friday": dict(color="#222222"),
}


def _classify(name: str, etype: str) -> str | None:
    blob = f"{name} {etype}".lower()
    if "ramadan" in blob:
        return "ramadan"
    if "fitr" in blob:
        return "eid_fitr"
    if "adha" in blob:
        return "eid_adha"
    if "nikah" in blob:
        return "nikah"
    if "black" in blob:
        return "black_friday"
    return None


def build_overlays(events: pd.DataFrame, x_start, x_end):
    """Return (shapes, annotations) lists for events overlapping [x_start, x_end]."""
    x_start, x_end = pd.Timestamp(x_start), pd.Timestamp(x_end)
    shapes, annotations = [], []
    for _, e in events.iterrows():
        kind = _classify(str(e["event_name"]), str(e["event_type"]))
        if kind is None:
            continue
        s, en = pd.Timestamp(e["start_date"]), pd.Timestamp(e["end_date"])
        if en < x_start or s > x_end:
            continue  # outside the visible range
        if kind in ("ramadan", "nikah"):
            st = STYLES[kind]
            shapes.append(dict(type="rect", xref="x", yref="paper", x0=s, x1=en, y0=0, y1=1,
                               fillcolor=st["fillcolor"], opacity=st["opacity"],
                               line_width=st["line_width"], layer="below"))
            annotations.append(dict(x=s, y=1.0, yref="paper", showarrow=False,
                                    text=str(e["event_name"]), font=dict(size=10),
                                    bgcolor="rgba(255,255,255,0.6)"))
        else:
            st = STYLES[kind]
            shapes.append(dict(type="line", xref="x", yref="paper", x0=s, x1=s, y0=0, y1=1,
                               line=dict(color=st["color"], width=2, dash="dash"), layer="above"))
            annotations.append(dict(x=s, y=0.96, yref="paper", showarrow=False,
                                    text=str(e["event_name"]), font=dict(size=10, color=st["color"]),
                                    textangle=-90, xanchor="right"))
    return shapes, annotations


def apply_overlays(fig, events: pd.DataFrame, x_start, x_end):
    """Add the calendar overlays to a Plotly figure in place and return it."""
    shapes, annotations = build_overlays(events, x_start, x_end)
    for s in shapes:
        fig.add_shape(**s)
    for a in annotations:
        fig.add_annotation(**a)
    return fig
