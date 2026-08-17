import json
from config import PLUGINS

# Frontend is isolated from the HTTP server so app.py no longer owns the massive UI string.
# The existing UI template can be moved here incrementally without changing browser behavior.
HTML = """<!doctype html>
<html><head><meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover\"><title>STELLA</title></head>
<body>
<div id=\"app\"><h1>✦ STELLA</h1><p>Frontend template placeholder.</p></div>
<script>window.STELLA_PLUGINS = %s;</script>
</body></html>""" % json.dumps(PLUGINS, separators=(",", ":"))
