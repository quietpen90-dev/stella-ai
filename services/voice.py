"""Voice-domain helpers extracted from the server monolith."""

from config import PERSONALITY
from voice_service import create_voice_token


def voice_context(messages):
    """Build compact conversational context for a live STELLA call."""
    parts = []
    for message in messages[-30:]:
        role = message.get("role")
        text = message.get("parts", [{"text": ""}])[0].get("text", "")
        if role in ("user", "model"):
            parts.append(("User: " if role == "user" else "STELLA: ") + text)
        elif role == "image":
            parts.append("STELLA generated an image: " + text)
    return "\n".join(parts)


def create_token(messages):
    return create_voice_token(voice_context(messages))
