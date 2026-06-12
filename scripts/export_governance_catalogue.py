#!/usr/bin/env python3
"""Export the dbt governance annotations into a Data Asset Catalogue (v2).

Reads every dbt model schema YAML under dbt/noureddine/models/**/*.yml, extracts
the model-level and column-level ``meta`` blocks (Fix 2 — governance annotations),
and renders a single markdown catalogue at
docs/bloc1-governance/data-asset-catalogue-v2.md.

Pure standard library + PyYAML. Idempotent: re-running overwrites the output.
Run from the repository root:

    python scripts/export_governance_catalogue.py
"""
from __future__ import annotations

import glob
import os
from datetime import date

import yaml

# Resolve paths relative to the repo root (parent of this script's folder),
# so the script works regardless of the current working directory.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_GLOB = os.path.join(REPO_ROOT, "dbt", "noureddine", "models", "**", "*.yml")
OUTPUT_PATH = os.path.join(
    REPO_ROOT, "docs", "bloc1-governance", "data-asset-catalogue-v2.md"
)

# Map quality_tier -> human layer label. quality_tier is the source of truth.
LAYER_LABEL = {"bronze": "bronze", "silver": "silver", "gold": "gold"}
# Sort order for layers in the catalogue.
LAYER_ORDER = {"bronze": 0, "silver": 1, "gold": 2}


def load_models() -> list[dict]:
    """Load and flatten all model definitions from the dbt schema YAMLs."""
    models: list[dict] = []
    for path in sorted(glob.glob(MODELS_GLOB, recursive=True)):
        with open(path, "r", encoding="utf-8") as fh:
            doc = yaml.safe_load(fh) or {}
        for model in doc.get("models", []) or []:
            model["_source_file"] = os.path.relpath(path, REPO_ROOT)
            models.append(model)
    return models


def model_layer(model: dict) -> str:
    return model.get("meta", {}).get("quality_tier", "unknown")


def md_escape(text: str) -> str:
    """Escape pipe characters so table cells stay valid."""
    return str(text).replace("|", "\\|")


def fmt_list(value) -> str:
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value)
    return str(value)


def render() -> str:
    models = load_models()
    models.sort(key=lambda m: (LAYER_ORDER.get(model_layer(m), 9), m.get("name", "")))

    lines: list[str] = []
    lines.append("# NOUREDDINE — Data Asset Catalogue (v2)")
    lines.append("")
    lines.append(
        "> Auto-generated from the dbt model governance annotations "
        "(`meta` blocks) by `scripts/export_governance_catalogue.py`. "
        "Do not edit by hand — re-run the script."
    )
    lines.append("")
    lines.append(f"_Generated: {date.today().isoformat()} · {len(models)} models._")
    lines.append("")
    lines.append(
        "Classification scheme (Bloc 1): **C1** Public · **C2** Internal · "
        "**C3** Confidential (PII) · **C4** Restricted. "
        "PII levels: `none` · `indirect` · `direct`."
    )
    lines.append("")

    # ---- Summary table -----------------------------------------------------
    lines.append("## Summary")
    lines.append("")
    lines.append(
        "| Model | Layer | Classification | PII level | Retention (days) |"
    )
    lines.append("|---|---|---|---|---|")
    for model in models:
        meta = model.get("meta", {})
        lines.append(
            "| `{name}` | {layer} | {cls} | {pii} | {ret} |".format(
                name=model.get("name", ""),
                layer=LAYER_LABEL.get(model_layer(model), model_layer(model)),
                cls=meta.get("classification", "—"),
                pii=meta.get("pii_level", "—"),
                ret=meta.get("retention_days", "—"),
            )
        )
    lines.append("")

    # ---- Per-model detail --------------------------------------------------
    lines.append("## Model detail")
    lines.append("")
    for model in models:
        meta = model.get("meta", {})
        name = model.get("name", "")
        lines.append(f"### `{name}`")
        lines.append("")
        if model.get("description"):
            lines.append(f"_{model['description']}_")
            lines.append("")
        lines.append(f"- **Layer:** {LAYER_LABEL.get(model_layer(model), model_layer(model))}")
        lines.append(f"- **Classification:** {meta.get('classification', '—')}")
        lines.append(f"- **PII level:** {meta.get('pii_level', '—')}")
        lines.append(f"- **Retention (days):** {meta.get('retention_days', '—')}")
        lines.append(f"- **Owner role:** {meta.get('owner_role', '—')}")
        lines.append(f"- **Steward role:** {meta.get('steward_role', '—')}")
        lines.append(f"- **Source systems:** {fmt_list(meta.get('source_systems', '—'))}")
        lines.append(f"- **Update frequency:** {meta.get('update_frequency', '—')}")
        lines.append(f"- **Defined in:** `{model.get('_source_file', '—')}`")
        lines.append("")

        columns = model.get("columns", []) or []
        if columns:
            lines.append(
                "| Column | PII | PII category | Classification | "
                "Business definition | Transformation |"
            )
            lines.append("|---|---|---|---|---|---|")
            for col in columns:
                cmeta = col.get("meta", {}) or {}
                lines.append(
                    "| `{col}` | {pii} | {cat} | {cls} | {defn} | {tx} |".format(
                        col=col.get("name", ""),
                        pii=str(cmeta.get("pii", "—")).lower(),
                        cat=cmeta.get("pii_category", "—"),
                        cls=cmeta.get("classification", "—"),
                        defn=md_escape(cmeta.get("business_definition", "—")),
                        tx=md_escape(cmeta.get("transformation", "—")),
                    )
                )
            lines.append("")
        else:
            lines.append("_No columns annotated._")
            lines.append("")

    return "\n".join(lines) + "\n"


def main() -> None:
    output = render()
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
        fh.write(output)
    rel = os.path.relpath(OUTPUT_PATH, REPO_ROOT)
    print(f"Wrote governance catalogue: {rel} ({len(output)} bytes)")


if __name__ == "__main__":
    main()
