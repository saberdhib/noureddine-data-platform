"""AI Marketing Studio (Bloc 4, optional) — generative visuals for campaigns.

Text-to-image (campaign creatives) and image-to-video (social clips) via the Hugging
Face Inference Providers (fal-ai). Reuses the same HF token as the text LLM
(OPENAI_API_KEY) and the same org billing (HF_BILL_TO -> bill_to). No customer data
is involved (marketing content only — no PII).

NOTE: image/video generation costs significantly more than text and video can be slow;
keep an org spending limit set.
"""
from __future__ import annotations

import io
import os

TXT2IMG_MODEL = os.getenv("STUDIO_IMAGE_MODEL", "Qwen/Qwen-Image-2512")
EDIT_MODEL = os.getenv("STUDIO_EDIT_MODEL", "black-forest-labs/FLUX.1-Kontext-dev")
IMG2VID_MODEL = os.getenv("STUDIO_VIDEO_MODEL", "Lightricks/LTX-2")


def is_enabled() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def _client():
    from huggingface_hub import InferenceClient
    return InferenceClient(
        provider="fal-ai",
        api_key=os.environ["OPENAI_API_KEY"],          # reuse the HF token
        bill_to=os.getenv("HF_BILL_TO") or None,        # org billing (ESCP)
    )


def text_to_image(prompt: str, *, model: str | None = None) -> bytes:
    """Generate a campaign visual; returns PNG bytes."""
    img = _client().text_to_image(prompt, model=model or TXT2IMG_MODEL)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def image_to_image(image_bytes: bytes, prompt: str, *, model: str | None = None) -> bytes:
    """Generate a variation/edit from a source image; returns PNG bytes."""
    img = _client().image_to_image(image_bytes, prompt=prompt, model=model or EDIT_MODEL)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def image_to_video(image_bytes: bytes, prompt: str, *, model: str | None = None) -> bytes:
    """Animate an image into a short social clip; returns video bytes (mp4)."""
    return _client().image_to_video(image_bytes, prompt=prompt, model=model or IMG2VID_MODEL)


def campaign_prompt(category: str, event: str, style: str = "") -> str:
    """Brand-aware text-to-image prompt for NOUREDDINE (premium menswear)."""
    base = (f"Premium direct-to-consumer menswear brand NOUREDDINE, {category} product, "
            f"editorial fashion photography, elegant modern Muslim man, refined styling, "
            f"soft studio lighting, high-end e-commerce campaign visual")
    if event and event.lower() not in ("", "évergreen", "evergreen", "aucun"):
        base += f", themed for {event} (tasteful, culturally respectful)"
    if style:
        base += f", {style}"
    return base + ", 4k, photorealistic, no text, no logo"
