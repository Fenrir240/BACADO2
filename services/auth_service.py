import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from pathlib import Path


DB_PATH = Path("data/app.db")
JWT_ALGORITHM = "HS256"
JWT_TTL_SECONDS = 60 * 60 * 24
PBKDF2_ITERATIONS = 120_000
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def init_auth_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
            """
        )
        connection.commit()


def create_user(email: str, password: str, name: str) -> dict:
    init_auth_db()
    email = normalize_email(email)
    name = name.strip() or email.split("@")[0]
    validate_auth_input(email, password)

    try:
        with sqlite3.connect(DB_PATH) as connection:
            cursor = connection.execute(
                """
                INSERT INTO users (email, name, password_hash, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (email, name, hash_password(password), int(time.time())),
            )
            connection.commit()
            user_id = cursor.lastrowid
    except sqlite3.IntegrityError as error:
        raise ValueError("Exista deja un cont cu acest email.") from error

    return {
        "id": user_id,
        "email": email,
        "name": name,
    }


def authenticate_user(email: str, password: str) -> dict:
    init_auth_db()
    email = normalize_email(email)

    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        user = connection.execute(
            "SELECT id, email, name, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()

    if user is None or not verify_password(password, user["password_hash"]):
        raise ValueError("Email sau parola incorecta.")

    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
    }


def create_access_token(user: dict) -> str:
    now = int(time.time())
    payload = {
        "sub": str(user["id"]),
        "email": user["email"],
        "name": user["name"],
        "iat": now,
        "exp": now + JWT_TTL_SECONDS,
    }

    return encode_jwt(payload)


def get_user_from_token(token: str) -> dict | None:
    try:
        payload = decode_jwt(token)
    except ValueError:
        return None

    user_id = payload.get("sub")

    if not user_id:
        return None

    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        user = connection.execute(
            "SELECT id, email, name FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

    if user is None:
        return None

    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
    }


def encode_jwt(payload: dict) -> str:
    header = {
        "alg": JWT_ALGORITHM,
        "typ": "JWT",
    }
    header_part = base64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_part = base64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    unsigned_token = f"{header_part}.{payload_part}"
    signature = sign(unsigned_token)

    return f"{unsigned_token}.{signature}"


def decode_jwt(token: str) -> dict:
    parts = token.split(".")

    if len(parts) != 3:
        raise ValueError("Token JWT invalid.")

    header_part, payload_part, signature = parts
    unsigned_token = f"{header_part}.{payload_part}"
    expected_signature = sign(unsigned_token)

    if not hmac.compare_digest(signature, expected_signature):
        raise ValueError("Semnatura JWT invalida.")

    try:
        header = json.loads(base64url_decode(header_part))
        payload = json.loads(base64url_decode(payload_part))
    except (json.JSONDecodeError, ValueError) as error:
        raise ValueError("Payload JWT invalid.") from error

    if header.get("alg") != JWT_ALGORITHM:
        raise ValueError("Algoritm JWT neacceptat.")

    if int(payload.get("exp", 0)) < int(time.time()):
        raise ValueError("Token JWT expirat.")

    return payload


def sign(unsigned_token: str) -> str:
    digest = hmac.new(
        get_jwt_secret().encode(),
        unsigned_token.encode(),
        hashlib.sha256,
    ).digest()
    return base64url_encode(digest)


def get_jwt_secret() -> str:
    return os.getenv("JWT_SECRET", "dev-jwt-secret-change-me")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt,
        PBKDF2_ITERATIONS,
    )
    return (
        f"pbkdf2_sha256${PBKDF2_ITERATIONS}$"
        f"{base64url_encode(salt)}${base64url_encode(digest)}"
    )


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, digest_text = stored_hash.split("$", 3)
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    iterations = int(iterations_text)
    salt = base64url_decode(salt_text)
    expected_digest = base64url_decode(digest_text)
    actual_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt,
        iterations,
    )

    return hmac.compare_digest(actual_digest, expected_digest)


def validate_auth_input(email: str, password: str) -> None:
    if not EMAIL_PATTERN.match(email):
        raise ValueError("Email invalid.")

    if len(password) < 8:
        raise ValueError("Parola trebuie sa aiba cel putin 8 caractere.")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def base64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)
