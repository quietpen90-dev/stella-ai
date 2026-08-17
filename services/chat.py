"""Conversation-domain helpers extracted from the server monolith."""

from ai_service import generate_chat_reply


def build_history(messages):
    """Convert stored STELLA messages into Gemini conversation parts."""
    history = []
    for message in messages:
        if message.get("role") not in ("user", "model"):
            continue
        history.append({
            "role": message["role"],
            "parts": [{"text": message.get("parts", [{"text": ""}])[0].get("text", "")}],
        })
    return history


def reply(messages, prompt):
    """Generate a STELLA reply from stored conversation messages."""
    return generate_chat_reply(build_history(messages), prompt)
