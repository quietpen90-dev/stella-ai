import sqlite3
import hashlib
import secrets

DATABASE = "stella.db"


def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def create_database():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS voice_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            conversation_id INTEGER NOT NULL,
            provider TEXT,
            provider_session_id TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ended_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            theme TEXT NOT NULL DEFAULT 'system',
            memory_enabled INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    connection.commit()
    connection.close()


def hash_password(password):
    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        200_000
    )
    return salt.hex() + ":" + password_hash.hex()


def create_user(username, password_hash):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, password_hash)
        )
        user_id = cursor.lastrowid
        cursor.execute(
            "INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)",
            (user_id,)
        )
        connection.commit()
        return user_id
    except sqlite3.IntegrityError:
        return None
    finally:
        connection.close()


def verify_password(password, stored_password):
    salt_hex, stored_hash_hex = stored_password.split(":")
    salt = bytes.fromhex(salt_hex)
    stored_hash = bytes.fromhex(stored_hash_hex)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        200_000
    )
    return secrets.compare_digest(password_hash, stored_hash)


def verify_user(username, password):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT id, password FROM users WHERE username = ?",
        (username,)
    )
    user = cursor.fetchone()
    connection.close()

    if user is None:
        return None

    user_id, stored_password = user
    if verify_password(password, stored_password):
        return user_id
    return None


def create_session(user_id):
    token = secrets.token_urlsafe(32)
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO sessions (token, user_id) VALUES (?, ?)",
        (token, user_id)
    )
    connection.commit()
    connection.close()
    return token


def get_user_from_session(token):
    if not token:
        return None
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT user_id FROM sessions WHERE token = ?",
        (token,)
    )
    result = cursor.fetchone()
    connection.close()
    return result[0] if result else None


def delete_session(token):
    if not token:
        return
    connection = get_connection()
    connection.execute("DELETE FROM sessions WHERE token = ?", (token,))
    connection.commit()
    connection.close()


def get_username(user_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    connection.close()
    return row[0] if row else None


def create_conversation(user_id, title="New chat"):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO conversations (user_id, title) VALUES (?, ?)",
        (user_id, title[:100])
    )
    connection.commit()
    conversation_id = cursor.lastrowid
    connection.close()
    return conversation_id


def get_conversations(user_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT id, title, created_at, updated_at
        FROM conversations
        WHERE user_id = ?
        ORDER BY updated_at DESC, id DESC
        """,
        (user_id,)
    )
    rows = cursor.fetchall()
    connection.close()
    return [
        {"id": r[0], "title": r[1] or "New chat", "created_at": r[2], "updated_at": r[3]}
        for r in rows
    ]


def user_owns_conversation(user_id, conversation_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT 1 FROM conversations WHERE id = ? AND user_id = ?",
        (conversation_id, user_id)
    )
    result = cursor.fetchone()
    connection.close()
    return result is not None


def add_message(conversation_id, role, content):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
        (conversation_id, role, content)
    )
    cursor.execute(
        "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (conversation_id,)
    )
    connection.commit()
    connection.close()


def get_messages(conversation_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT role, content
        FROM messages
        WHERE conversation_id = ?
        ORDER BY id ASC
        """,
        (conversation_id,)
    )
    rows = cursor.fetchall()
    connection.close()
    return [
        {"role": role, "parts": [{"text": content}]}
        for role, content in rows
    ]


def get_user_memory_messages(user_id, limit=40):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT m.role, m.content, m.created_at, c.id, c.title
        FROM messages m
        JOIN conversations c ON c.id = m.conversation_id
        WHERE c.user_id = ?
          AND m.role IN ('user', 'model', 'image', 'voice_call')
        ORDER BY m.id DESC
        LIMIT ?
        """,
        (user_id, limit)
    )
    rows = list(reversed(cursor.fetchall()))
    connection.close()
    return [
        {
            "role": r[0],
            "content": r[1],
            "created_at": r[2],
            "conversation_id": r[3],
            "conversation_title": r[4] or "New chat"
        }
        for r in rows
    ]


def get_user_settings(user_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT theme, memory_enabled FROM user_settings WHERE user_id = ?",
        (user_id,)
    )
    row = cursor.fetchone()
    if row is None:
        cursor.execute(
            "INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)",
            (user_id,)
        )
        connection.commit()
        theme, memory_enabled = "system", 1
    else:
        theme, memory_enabled = row
    connection.close()
    return {"theme": theme, "memory_enabled": bool(memory_enabled)}


def update_user_settings(user_id, theme=None, memory_enabled=None):
    current = get_user_settings(user_id)
    theme = theme if theme in ("system", "light", "dark") else current["theme"]
    if memory_enabled is None:
        memory_enabled = current["memory_enabled"]
    connection = get_connection()
    connection.execute(
        """
        INSERT INTO user_settings (user_id, theme, memory_enabled)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            theme = excluded.theme,
            memory_enabled = excluded.memory_enabled
        """,
        (user_id, theme, 1 if memory_enabled else 0)
    )
    connection.commit()
    connection.close()
    return {"theme": theme, "memory_enabled": bool(memory_enabled)}


def get_media_gallery(user_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT m.role, m.content, m.created_at, c.id, c.title
        FROM messages m
        JOIN conversations c ON c.id = m.conversation_id
        WHERE c.user_id = ? AND m.role IN ('image', 'video')
        ORDER BY m.id DESC
        """,
        (user_id,)
    )
    rows = cursor.fetchall()
    connection.close()
    items = []
    for role, content, created_at, conversation_id, title in rows:
        try:
            data = json.loads(content)
        except Exception:
            data = {"url": content}
        items.append({
            "type": role,
            "url": data.get("url"),
            "prompt": data.get("prompt", ""),
            "created_at": created_at,
            "conversation_id": conversation_id,
            "conversation_title": title or "New chat"
        })
    return items


def set_conversation_title(conversation_id, title):
    connection = get_connection()
    connection.execute(
        "UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (title[:100], conversation_id)
    )
    connection.commit()
    connection.close()


def delete_conversation(user_id, conversation_id):
    connection = get_connection()
    connection.execute(
        "DELETE FROM conversations WHERE id = ? AND user_id = ?",
        (conversation_id, user_id)
    )
    connection.commit()
    connection.close()


def create_voice_call(user_id, conversation_id, provider=None, provider_session_id=None):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO voice_calls
        (user_id, conversation_id, provider, provider_session_id, status)
        VALUES (?, ?, ?, ?, 'active')
        """,
        (user_id, conversation_id, provider, provider_session_id)
    )
    connection.commit()
    call_id = cursor.lastrowid
    connection.close()
    return call_id


def get_voice_call(call_id, user_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT id, conversation_id, provider, provider_session_id, status,
               started_at, ended_at
        FROM voice_calls
        WHERE id = ? AND user_id = ?
        """,
        (call_id, user_id)
    )
    row = cursor.fetchone()
    connection.close()
    if not row:
        return None
    return {
        "id": row[0],
        "conversation_id": row[1],
        "provider": row[2],
        "provider_session_id": row[3],
        "status": row[4],
        "started_at": row[5],
        "ended_at": row[6]
    }


def end_voice_call(call_id, user_id):
    connection = get_connection()
    connection.execute(
        """
        UPDATE voice_calls
        SET status = 'ended', ended_at = CURRENT_TIMESTAMP
        WHERE id = ? AND user_id = ?
        """,
        (call_id, user_id)
    )
    connection.commit()
    connection.close()
