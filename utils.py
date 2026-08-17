import json
import re


def image_data(text):
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
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
        if message["role"] == "image":
            data = image_data(message["parts"][0]["text"])
            if data:
                return data
    return None


def voice_context(messages):
    parts = []
    for message in messages[-30:]:
        text = message["parts"][0]["text"]
        if message["role"] in ("user", "model"):
            parts.append(("User: " if message["role"] == "user" else "STELLA: ") + text)
        elif message["role"] == "image":
            data = image_data(text)
            parts.append(
                "STELLA generated an image: " + str(data.get("prompt", ""))
                if data else "STELLA generated an image."
            )
    return "\n".join(parts)
