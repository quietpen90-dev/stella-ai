import json
import urllib.request
from datetime import datetime, timedelta, timezone

from config import PERSONALITY, VOICE_API_KEY, VOICE_MODEL, VOICE_TOKEN_URL


def create_voice_token(context):
    if not VOICE_API_KEY:
        raise ValueError("GEMINI_API_KEY2 is not configured on the server.")
    now = datetime.now(timezone.utc)
    body = {
        "uses": 1,
        "expireTime": (now + timedelta(minutes=30)).isoformat().replace("+00:00", "Z"),
        "newSessionExpireTime": (now + timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
        "liveConnectConstraints": {
            "model": VOICE_MODEL,
            "config": {
                "responseModalities": ["AUDIO"],
                "sessionResumption": {},
                "systemInstruction": {
                    "parts": [{"text": PERSONALITY + "\nConversation before call:\n" + context}]
                },
            },
        },
    }
    request = urllib.request.Request(
        VOICE_TOKEN_URL,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": VOICE_API_KEY},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode())
