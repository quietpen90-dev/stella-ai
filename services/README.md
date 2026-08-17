# Service extraction map

This directory contains the remaining STELLA server extraction targets. Each refactor branch owns one domain so the monolith can be migrated incrementally without changing behavior in unrelated areas.

- `chat.py` — conversation/model calls
- `media.py` — image detection, image metadata and generation
- `voice.py` — voice context/token lifecycle
- `routing.py` — HTTP request/response routing helpers
