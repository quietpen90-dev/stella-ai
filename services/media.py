"""Image/media-domain helpers extracted from the server monolith."""

import base64
import io
import json
import re

from config import HF_TOKEN, IMAGE_MODEL
from huggingface_hub import InferenceClient


def image_data(text):
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else None
    except (TypeError, ValueError):
        return None


def image_request(text):
    text = text.lower()
    return bool(
        re.search(r"\b(generate|create|draw|make|render|paint|illustrate)\b.{0,100}\b(image|picture|photo|portrait|art)\b", text)
        or re.search(r"\b(update|edit|modify|change|remake|redo)\b.{0,30}\b(it|that|this)\b", text)
    )


def latest_image(messages):
    for message in reversed(messages):
        if message.get("role") != "image":
            continue
        data = image_data(message.get("parts", [{"text": ""}])[0].get("text", ""))
        if data:
            return data
    return None


def generate_image(prompt):
    if not HF_TOKEN:
        raise ValueError("HF_TOKEN is not configured on the server.")
    image = InferenceClient(provider="nscale", api_key=HF_TOKEN).text_to_image(
        prompt, model=IMAGE_MODEL
    )
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
