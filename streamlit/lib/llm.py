"""Shared LLM core for the Streamlit business app (Bloc 4).

One place to build the OpenAI-compatible client and run a grounded chat call.
Works with OpenAI, DeepSeek, xAI Grok or the Hugging Face router (see .env.example):
  * OPENAI_API_KEY   — provider key
  * OPENAI_BASE_URL  — provider endpoint (empty -> OpenAI)
  * OPENAI_MODEL     — model id
  * HF_BILL_TO       — optional: bill HF Inference Providers to an org (X-HF-Bill-To)

Governance (DPIA #2): callers must only ever pass aggregate, category-level data —
never a customer id, name, email or any individual-level field. ``assert_no_pii``
is a belt-and-braces guard for dict payloads.
"""
from __future__ import annotations

import os
from typing import Dict, Iterable

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# These keys must never appear in anything sent to the LLM.
FORBIDDEN_KEYS = {
    "customer_id", "customer_key", "email", "customer_email", "first_name",
    "last_name", "name", "address", "phone", "order_id", "tracking_number",
}


class NotConfigured(RuntimeError):
    """Raised when OPENAI_API_KEY is not set."""


def is_enabled() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def assert_no_pii(rows: Iterable[Dict]) -> None:
    for r in rows:
        leaked = FORBIDDEN_KEYS.intersection({str(k).lower() for k in r})
        if leaked:
            raise ValueError(f"PII forbidden in the LLM payload (DPIA #2): {sorted(leaked)}")


def _client():
    from openai import OpenAI  # imported lazily so pages load without the package
    headers = {}
    bill_to = os.getenv("HF_BILL_TO")
    if bill_to:
        headers["X-HF-Bill-To"] = bill_to  # HF Inference Providers org billing
    return OpenAI(base_url=os.getenv("OPENAI_BASE_URL") or None,
                  default_headers=headers or None)


def chat(system_prompt: str, user_content: str, *, model: str | None = None,
         temperature: float = 0.2, max_tokens: int = 900) -> str:
    """Run a single grounded system+user chat completion and return the text."""
    if not is_enabled():
        raise NotConfigured("OPENAI_API_KEY n'est pas défini.")
    resp = _client().chat.completions.create(
        model=model or OPENAI_MODEL,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    )
    return resp.choices[0].message.content
