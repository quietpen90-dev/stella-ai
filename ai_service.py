import base64
import io
import json
import urllib.request
from huggingface_hub import InferenceClient

from config import API_KEY, HF_TOKEN, IMAGE_MODEL, MODEL_URL, PERSONALITY


def generate_chat_reply(history, message):
    if not API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured on the server.")
    body = {
        "systemInstruction": {"parts": [{"text": PERSONALITY}]},
        "contents": history + [{"role": "user", "parts": [{"text": message}]}],
    }
    req = urllib.request.Request(
        MODEL_URL,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": API_KEY},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as response:
        result = json.loads(response.read().decode())
    return "".join(
        part.get("text", "")
        for part in result["candidates"][0]["content"]["parts"]
        if not part.get("thought", False)
    ) or "I could not generate a response right now."


def generate_image(prompt):
    if not HF_TOKEN:
        raise ValueError("HF_TOKEN is not configured on the server.")
    image = InferenceClient(provider="nscale", api_key=HF_TOKEN).text_to_image(
        prompt, model=IMAGE_MODEL
    )
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
