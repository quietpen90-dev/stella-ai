"""HTTP/routing helpers extracted from the server monolith."""

from urllib.parse import parse_qs, urlparse

from http_utils import read_json, send_json, session_token


def request_path(handler):
    return urlparse(handler.path).path


def query_params(handler):
    return parse_qs(urlparse(handler.path).query)


def user_id(handler, get_user_from_session):
    return get_user_from_session(session_token(handler))
