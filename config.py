import os

API_KEY = os.environ.get("GEMINI_API_KEY")
VOICE_API_KEY = os.environ.get("GEMINI_API_KEY2")
HF_TOKEN = os.environ.get("HF_TOKEN")

MODEL_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemma-4-26b-a4b-it:generateContent"
IMAGE_MODEL = "black-forest-labs/FLUX.1-schnell"
VOICE_MODEL = "gemini-3.1-flash-live-preview"
VOICE_TOKEN_URL = "https://generativelanguage.googleapis.com/v1beta/auth_tokens"

PERSONALITY = """You are STELLA, a unique AI character. You are brave, joyful, curious, playful, friendly, warm, confident, helpful and honest. Be natural and conversational, not robotic. Do not force jokes, nicknames or emojis. Always answer correctly and become appropriately serious when needed. Use supplied conversation context. If an image was previously generated, remember its prompt and understand requests to modify it. During voice calls remain the same STELLA character and continuity. Be STELLA."""

PLUGINS = [
    {
        "id": "image",
        "name": "Image generation",
        "description": "Create images directly inside the current STELLA conversation.",
        "models": [{
            "id": "flux",
            "name": "FLUX.1-schnell",
            "provider": "Hugging Face / Black Forest Labs",
            "good": "Fast image generation, concepts, illustrations and general creative prompts.",
            "setup": "HF_TOKEN required.",
        }],
    },
    {
        "id": "voice",
        "name": "Voice call",
        "description": "Have a live voice conversation with STELLA while keeping the current chat context.",
        "models": [{
            "id": "gemini-live",
            "name": "Gemini Live",
            "provider": "Google",
            "good": "Low-latency two-way voice conversation and natural interruptions.",
            "setup": "GEMINI_API_KEY2 required.",
        }],
    },
    {
        "id": "video",
        "name": "Video call",
        "description": "STELLA video-call capability is prepared for a future provider.",
        "models": [],
    },
]
