"""
STELLA voice-call backend.

Provider-neutral by design: the actual voice provider is intentionally not
hard-coded yet. Add the provider credentials/model names as environment
variables when a trusted provider is selected, then implement the provider
adapter without changing STELLA's conversation/memory layer.
"""

import os
from database import (
    create_voice_call,
    get_voice_call,
    end_voice_call,
    get_messages,
    add_message,
    user_owns_conversation,
)

VOICE_PROVIDER = os.environ.get("VOICE_PROVIDER", "")
VOICE_API_KEY = os.environ.get("VOICE_API_KEY", "")
VOICE_MODEL = os.environ.get("VOICE_MODEL", "")
VOICE_STT_MODEL = os.environ.get("VOICE_STT_MODEL", "")
VOICE_TTS_MODEL = os.environ.get("VOICE_TTS_MODEL", "")

STELLA_VOICE_SYSTEM_PROMPT = """
You are STELLA.
Keep the same STELLA character, personality and conversational continuity
used by the normal STELLA chat. A voice call is not a new character or a
new memory. Continue naturally from the existing conversation.

The voice layer may use a different underlying model, but the user should
experience one continuous STELLA. Use the supplied conversation context and
any memories already stored in the conversation.
""".strip()


def voice_configured():
    """Return whether a real voice provider has been configured."""
    return bool(VOICE_PROVIDER and VOICE_API_KEY and VOICE_MODEL)


def build_voice_context(user_id, conversation_id):
    """Build the context a voice provider should receive for a call."""
    if not user_owns_conversation(user_id, conversation_id):
        raise ValueError("Invalid conversation.")

    messages = get_messages(conversation_id)
    context = []

    for message in messages:
        role = message.get("role")
        parts = message.get("parts", [])
        text = parts[0].get("text", "") if parts else ""

        if role == "user":
            context.append({"role": "user", "text": text})
        elif role == "model":
            context.append({"role": "assistant", "text": text})
        elif role == "image":
            context.append({
                "role": "assistant",
                "text": "STELLA previously generated an image in this conversation."
            })

    return {
        "system_prompt": STELLA_VOICE_SYSTEM_PROMPT,
        "messages": context,
    }


def start_voice_call(user_id, conversation_id):
    """Create a persistent STELLA voice-call session."""
    if not user_owns_conversation(user_id, conversation_id):
        raise ValueError("Invalid conversation.")

    return create_voice_call(
        user_id,
        conversation_id,
        provider=VOICE_PROVIDER or None,
        provider_session_id=None,
    )


def get_call(user_id, call_id):
    """Return a user's persisted voice-call session."""
    return get_voice_call(call_id, user_id)


def finish_voice_call(user_id, call_id, transcript=None):
    """
    End a call and optionally store its final transcript as normal STELLA
    conversation messages. This is what keeps the conversation continuous
    after the user returns to text chat.
    """
    call = get_voice_call(call_id, user_id)
    if not call:
        raise ValueError("Voice call not found.")

    if transcript:
        for item in transcript:
            role = item.get("role")
            text = str(item.get("text", "")).strip()
            if not text:
                continue
            if role in ("user", "assistant", "model"):
                add_message(
                    call["conversation_id"],
                    "user" if role == "user" else "model",
                    text,
                )

    end_voice_call(call_id, user_id)
    return get_voice_call(call_id, user_id)


def provider_requirements():
    """Return the configuration the future provider adapter needs."""
    return {
        "provider": VOICE_PROVIDER or None,
        "configured": voice_configured(),
        "voice_model": VOICE_MODEL or None,
        "stt_model": VOICE_STT_MODEL or None,
        "tts_model": VOICE_TTS_MODEL or None,
        "requires_websocket_or_webrtc": True,
        "stella_personality_prompt": STELLA_VOICE_SYSTEM_PROMPT,
    }
