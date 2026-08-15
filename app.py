import os
import json
import sqlite3
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from database import (
    create_database, create_user, hash_password, verify_user,
    create_session, get_user_from_session, delete_session,
    get_username, create_conversation, get_conversations,
    user_owns_conversation, add_message, get_messages
)

API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_URL = "https