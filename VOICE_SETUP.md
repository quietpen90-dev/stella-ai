# STELLA Voice Architecture

The voice feature is intentionally provider-neutral until a trusted voice provider is selected.

## Environment variables

Add these to the deployment environment when the provider is chosen:

- `VOICE_PROVIDER`
- `VOICE_API_KEY`
- `VOICE_MODEL`
- `VOICE_STT_MODEL` (optional)
- `VOICE_TTS_MODEL` (optional)

Do not put voice API keys in frontend JavaScript.

## Architecture

```text
STELLA conversation
        |
        v
Shared SQLite memory
        |
        +---- Text chat (Gemma)
        |
        +---- Image generation (FLUX)
        |
        +---- Voice call (future provider)
                 |
                 +-- speech input / STT
                 +-- STELLA context
                 +-- voice model / LLM
                 +-- speech output / TTS
```

`voice.py` is the provider-neutral backend layer. It creates persistent call sessions tied to the authenticated user and the same conversation ID used by text/image chat.

When a call ends, its final transcript can be written back into the same conversation. That means STELLA can continue the discussion in text after the call, and the voice call can use everything already stored before it began.

## Provider adapter

The only provider-specific work left is implementing the actual realtime transport (normally WebRTC/WebSocket), authentication/token exchange, speech input/output, and provider session lifecycle. The STELLA memory and personality layer should not be replaced when doing that.
