import os
import json
import base64
import io
import re
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from huggingface_hub import InferenceClient
from database import (
    create_database, create_user, hash_password, verify_user,
    create_session, get_user_from_session, delete_session,
    get_username, create_conversation, get_conversations,
    user_owns_conversation, add_message, get_messages
)

API_KEY = os.environ.get("GEMINI_API_KEY")
HF_TOKEN = os