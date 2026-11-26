"""PostgreSQL-backed authentication and role-based user management service."""

import base64
from dataclasses import dataclass
from datetime import datetime
import hashlib
import hmac
import json
import logging
import time
from typing import List, Optional
from uuid import uuid4

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from src.config import settings
from src.database.connection import db_manager

logger = logging.getLogger(__name__)

MIN_PASSWORD_LENGTH = 6
ALLOWED_ROLES = {"admin", "user"}
_ARGON2_HASHER = PasswordHasher()


def hash_password(password: str) -> str:
    """Hashes a password using Argon2id (OWASP-recommended memory-hard KDF)."""
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Hasło musi mieć co najmniej {MIN_PASSWORD_LENGTH} znaków.")
    return _ARGON2_HASHER.hash(password)


def verify_password(password: str, stored_hash: str) -> bool:
    """Verifies a plaintext password against an Argon2id or legacy PBKDF2-HMAC-SHA256 hash."""
    if not password or not stored_hash:
        return False

    if stored_hash.startswith("$argon2"):
        try:
            return _ARGON2_HASHER.verify(stored_hash, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False

    if stored_hash.startswith("pbkdf2_sha256$"):
        try:
            scheme, iter_str, salt_hex, hash_hex = stored_hash.split("$", 3)
            if scheme != "pbkdf2_sha256":
                return False
            iterations = int(iter_str)
            salt = bytes.fromhex(salt_hex)
            expected = bytes.fromhex(hash_hex)
        except (ValueError, TypeError):
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(actual, expected)

    return False


def _session_secret() -> bytes:
    raw = f"{settings.POSTGRES_DB}:{settings.POSTGRES_PASSWORD}:gis-session-key"
    return hashlib.sha256(raw.encode("utf-8")).digest()


def _b64url_encode(data: bytes) -> str:
    """Encodes bytes using URL-safe Base64 without padding ('+', '/', '=')."""
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(text: str) -> bytes:
    """Decodes unpadded URL-safe Base64 string into bytes."""
    padded = text + "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def create_session_token(user: "UserRecord", ttl_seconds: int = 43200) -> str:
    """Creates a Base64URL(JSON).Base64URL(HMAC-SHA256) session token for URL-safe F5 persistence."""
    exp = int(time.time()) + ttl_seconds
    payload_dict = {
        "sub": user.id,
        "username": user.username,
        "role": user.role,
        "exp": exp,
    }
    payload_json = json.dumps(payload_dict, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    payload_b64 = _b64url_encode(payload_json)
    sig_bytes = hmac.new(_session_secret(), payload_b64.encode("ascii"), hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig_bytes)
    return f"{payload_b64}.{sig_b64}"


def verify_session_token(token: str) -> Optional["UserRecord"]:
    """Verifies a Base64URL(JSON).Base64URL(HMAC-SHA256) session token and returns UserRecord."""
    if not token or "." not in token:
        return None
    try:
        payload_b64, sig_b64 = token.split(".", 1)
        expected_sig_bytes = hmac.new(_session_secret(), payload_b64.encode("ascii"), hashlib.sha256).digest()
        expected_sig_b64 = _b64url_encode(expected_sig_bytes)
        if not hmac.compare_digest(sig_b64, expected_sig_b64):
            return None
        payload_data = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        if int(payload_data["exp"]) < int(time.time()):
            return None
        return UserRecord(
            id=str(payload_data["sub"]),
            username=str(payload_data["username"]),
            role=str(payload_data["role"]),
            is_active=True,
        )
    except Exception:
        return None


@dataclass
class UserRecord:
    """Authenticated user account representation."""

    id: str
    username: str
    role: str
    is_active: bool = True
    created_at: Optional[datetime] = None


class AuthService:
    """Manages user authentication and admin-only account provisioning in PostgreSQL."""

    DEFAULT_ADMIN_USERNAME = "inspe"
    DEFAULT_ADMIN_PASSWORD = "dfpojk12#$"

    @staticmethod
    def ensure_schema_and_admin() -> None:
        """Ensures the `users` table exists and the default admin (`inspe`) is provisioned."""
        with db_manager.get_cursor(commit=True) as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role VARCHAR(20) NOT NULL DEFAULT 'user',
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            cur.execute("SELECT id FROM users WHERE username = %s LIMIT 1;", (AuthService.DEFAULT_ADMIN_USERNAME,))
            if not cur.fetchone():
                admin_hash = hash_password(AuthService.DEFAULT_ADMIN_PASSWORD)
                cur.execute(
                    """
                    INSERT INTO users (id, username, password_hash, role, is_active)
                    VALUES (%s, %s, %s, %s, %s);
                    """,
                    (str(uuid4()), AuthService.DEFAULT_ADMIN_USERNAME, admin_hash, "admin", True),
                )
                logger.info("Provisioned default admin account '%s'.", AuthService.DEFAULT_ADMIN_USERNAME)

    @staticmethod
    def authenticate(username: str, password: str) -> Optional[UserRecord]:
        """Authenticates a user by username and password. Returns None on failure or inactive account."""
        clean_user = username.strip()
        if not clean_user or not password:
            return None

        with db_manager.get_cursor() as cur:
            cur.execute(
                """
                SELECT id, username, password_hash, role, is_active, created_at
                FROM users
                WHERE username = %s
                LIMIT 1;
                """,
                (clean_user,),
            )
            row = cur.fetchone()

        if not row:
            return None

        user_id, db_username, password_hash, role, is_active, created_at = row
        if not is_active or not verify_password(password, password_hash):
            return None

        return UserRecord(
            id=str(user_id),
            username=str(db_username),
            role=str(role),
            is_active=bool(is_active),
            created_at=created_at,
        )

    @staticmethod
    def _require_admin(actor: UserRecord) -> None:
        if actor.role != "admin":
            raise PermissionError("Tylko administrator może zarządzać kontami użytkowników.")

    @staticmethod
    def list_users(actor: UserRecord) -> List[UserRecord]:
        """Lists all user accounts (admin only)."""
        AuthService._require_admin(actor)
        with db_manager.get_cursor() as cur:
            cur.execute(
                """
                SELECT id, username, role, is_active, created_at
                FROM users
                ORDER BY created_at ASC, username ASC;
                """
            )
            rows = cur.fetchall()
        return [
            UserRecord(
                id=str(r[0]),
                username=str(r[1]),
                role=str(r[2]),
                is_active=bool(r[3]),
                created_at=r[4],
            )
            for r in rows
        ]

    @staticmethod
    def create_user(actor: UserRecord, username: str, password: str, role: str = "user") -> UserRecord:
        """Creates a new user account (admin only; no self-registration)."""
        AuthService._require_admin(actor)
        clean_user = username.strip()
        if len(clean_user) < 3 or " " in clean_user:
            raise ValueError("Login musi mieć co najmniej 3 znaki i nie może zawierać spacji.")
        clean_role = role.strip().lower()
        if clean_role not in ALLOWED_ROLES:
            raise ValueError(f"Nieprawidłowa rola: {role}. Dozwolone: admin, user.")

        pw_hash = hash_password(password)
        new_id = str(uuid4())
        with db_manager.get_cursor(commit=True) as cur:
            cur.execute("SELECT id FROM users WHERE username = %s LIMIT 1;", (clean_user,))
            if cur.fetchone():
                raise ValueError(f"Użytkownik '{clean_user}' już istnieje.")
            cur.execute(
                """
                INSERT INTO users (id, username, password_hash, role, is_active)
                VALUES (%s, %s, %s, %s, %s);
                """,
                (new_id, clean_user, pw_hash, clean_role, True),
            )
        return UserRecord(id=new_id, username=clean_user, role=clean_role, is_active=True)

    @staticmethod
    def update_user_password(actor: UserRecord, target_username: str, new_password: str) -> None:
        """Resets a user's password (admin only)."""
        AuthService._require_admin(actor)
        pw_hash = hash_password(new_password)
        with db_manager.get_cursor(commit=True) as cur:
            cur.execute("SELECT id FROM users WHERE username = %s LIMIT 1;", (target_username.strip(),))
            if not cur.fetchone():
                raise ValueError(f"Nie znaleziono użytkownika '{target_username}'.")
            cur.execute(
                "UPDATE users SET password_hash = %s WHERE username = %s;",
                (pw_hash, target_username.strip()),
            )

    @staticmethod
    def set_user_active(actor: UserRecord, target_username: str, is_active: bool) -> None:
        """Activates or deactivates a user account (admin only, cannot deactivate self)."""
        AuthService._require_admin(actor)
        clean_target = target_username.strip()
        if clean_target == actor.username and not is_active:
            raise ValueError("Administrator nie może dezaktywować własnego konta.")
        with db_manager.get_cursor(commit=True) as cur:
            cur.execute("SELECT id FROM users WHERE username = %s LIMIT 1;", (clean_target,))
            if not cur.fetchone():
                raise ValueError(f"Nie znaleziono użytkownika '{clean_target}'.")
            cur.execute(
                "UPDATE users SET is_active = %s WHERE username = %s;",
                (bool(is_active), clean_target),
            )

    @staticmethod
    def delete_user(actor: UserRecord, target_username: str) -> None:
        """Deletes a non-admin user account (admin only, cannot delete self or admin accounts)."""
        AuthService._require_admin(actor)
        clean_target = target_username.strip()
        if clean_target == actor.username:
            raise ValueError("Administrator nie może usunąć własnego konta.")
        with db_manager.get_cursor(commit=True) as cur:
            cur.execute("SELECT id, role FROM users WHERE username = %s LIMIT 1;", (clean_target,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Nie znaleziono użytkownika '{clean_target}'.")
            if str(row[1]) == "admin":
                raise ValueError("Nie można usunąć konta administratora.")
            cur.execute("DELETE FROM users WHERE username = %s;", (clean_target,))
