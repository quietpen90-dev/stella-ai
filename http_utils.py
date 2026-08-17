import json


def read_json(handler):
    length = int(handler.headers.get("Content-Length", 0))
    return json.loads(handler.rfile.read(length).decode())


def send_json(handler, data, status=200, cookie=None):
    output = json.dumps(data).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(output)))
    if cookie:
        handler.send_header("Set-Cookie", cookie)
    handler.end_headers()
    handler.wfile.write(output)


def session_token(handler):
    for item in handler.headers.get("Cookie", "").split(";"):
        if item.strip().startswith("stella_session="):
            return item.strip().split("=", 1)[1]
    return None
