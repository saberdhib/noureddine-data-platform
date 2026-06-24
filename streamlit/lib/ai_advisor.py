"""Optional LLM stock advisor (Bloc 4 — business consumption).

Turns the platform's own numbers — 30-day demand forecast, current inventory,
days of cover and upcoming Islamic-calendar events, AGGREGATED PER CATEGORY — into
an actionable restock briefing in French.

Design:
  * **Grounded**: the model only ever sees the structured numbers we pass; it is
    instructed to invent nothing. The reorder quantities are computed here, not by
    the LLM, so figures are never hallucinated.
  * **No PII (DPIA #2)**: only category-level aggregates are sent — never a
    customer id, name, email or any individual-level field.
  * **Optional / isolated**: enabled only when OPENAI_API_KEY is set; degrades to
    a clear "configure the key" message otherwise. Outside the zero-licence
    baseline — see ADR 0015.
"""
from __future__ import annotations

import json
import os
from typing import List, Dict

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Belt-and-braces: these keys must never appear in the payload sent to the LLM.
_FORBIDDEN_KEYS = {
    "customer_id", "customer_key", "email", "customer_email", "first_name",
    "last_name", "name", "address", "phone", "order_id",
}

SYSTEM_PROMPT = (
    "Tu es analyste supply-chain pour NOUREDDINE, marque e-commerce premium de mode "
    "masculine dont la demande est rythmée par le calendrier culturel islamique "
    "(Ramadan, Aïd al-Fitr, Aïd al-Adha, saison des mariages) et les pics retail "
    "(Black Friday). À partir UNIQUEMENT des données agrégées par catégorie qui te "
    "sont fournies (aucune donnée personnelle), rédige un briefing de "
    "réapprovisionnement actionnable, en français, pour le responsable des "
    "opérations.\n\n"
    "Règle de décision clé : `lead_time_days` est le délai de réapprovisionnement. "
    "Si `rupture_avant_livraison` est vrai (jours de couverture < délai), le stock "
    "sera épuisé AVANT l'arrivée de la commande → il faut commander immédiatement, "
    "surtout si un événement calendaire (Aïd, Ramadan, mariage) tombe dans la "
    "fenêtre. Un fort stock 'aujourd'hui' ne protège pas si le pic + le délai le "
    "dépassent.\n\n"
    "Format attendu :\n"
    "1. **Synthèse** (2-3 phrases) : situation globale, ruptures avant livraison, urgences.\n"
    "2. **Actions prioritaires** : liste ordonnée des catégories à risque — pour "
    "chacune : l'action (🔴 commander maintenant / 🟠 commander bientôt / 🟢 OK), "
    "la **quantité indicative** (reprends `suggested_reorder_units`, n'invente AUCUN "
    "chiffre), et la raison en une phrase (couverture vs délai de réappro vs "
    "événement calendaire).\n\n"
    "Sois concis et opérationnel, pas de remplissage. N'utilise que les chiffres "
    "fournis."
)


class AdvisorNotConfigured(RuntimeError):
    """Raised when OPENAI_API_KEY is not set."""


def is_enabled() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def _assert_no_pii(rows: List[Dict]) -> None:
    for r in rows:
        leaked = _FORBIDDEN_KEYS.intersection({k.lower() for k in r})
        if leaked:
            raise ValueError(f"PII forbidden in the LLM payload (DPIA #2): {sorted(leaked)}")


def build_payload(rows: List[Dict], today_iso: str) -> str:
    """Compact JSON grounding payload (category-level aggregates only)."""
    _assert_no_pii(rows)
    return json.dumps({"date_du_jour": today_iso, "categories": rows},
                      ensure_ascii=False, indent=2)


def generate_briefing(rows: List[Dict], today_iso: str, *, model: str | None = None) -> str:
    """Produce the restock briefing via the shared LLM core. Raises AdvisorNotConfigured if no key."""
    from . import llm  # shared OpenAI-compatible client (OpenAI/DeepSeek/Grok/HF router)
    if not is_enabled():
        raise AdvisorNotConfigured("OPENAI_API_KEY n'est pas défini.")
    payload = build_payload(rows, today_iso)
    return llm.chat(SYSTEM_PROMPT, payload, model=model)
