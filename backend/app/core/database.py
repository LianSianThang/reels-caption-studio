import sqlite3
import hashlib
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from backend.app.core.config import settings

DB_PATH = settings.DATA_DIR / "studio.db"

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=20.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    if not salt:
        salt = os.urandom(16).hex()
    pwd_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    ).hex()
    return pwd_hash, salt

def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    pwd_hash, _ = hash_password(password, salt)
    return pwd_hash == expected_hash

def init_db():
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user',
        gemini_key TEXT DEFAULT '',
        groq_key TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP,
        is_active INTEGER DEFAULT 1
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS media_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_id TEXT UNIQUE NOT NULL,
        user_id INTEGER,
        filename TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_size_bytes INTEGER DEFAULT 0,
        source_type TEXT DEFAULT 'upload',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP NOT NULL,
        status TEXT DEFAULT 'active',
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()

    cursor.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1;")
    admin = cursor.fetchone()
    if not admin:
        admin_email = settings.ADMIN_DEFAULT_EMAIL
        admin_pwd = settings.ADMIN_DEFAULT_PASSWORD
        pwd_hash, salt = hash_password(admin_pwd)
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, salt, role)
            VALUES (?, ?, ?, ?, 'admin');
        """, ("admin", admin_email, pwd_hash, salt))
        conn.commit()
        print(f"[DB] Initialized default admin account: {admin_email}")

    conn.close()

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ? COLLATE NOCASE;", (email,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? COLLATE NOCASE;", (username,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?;", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def create_user(username: str, email: str, password: str, role: str = "user") -> Dict[str, Any]:
    pwd_hash, salt = hash_password(password)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (username, email, password_hash, salt, role)
        VALUES (?, ?, ?, ?, ?);
    """, (username, email, pwd_hash, salt, role))
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return get_user_by_id(user_id)

def update_user_last_login(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?;", (user_id,))
    conn.commit()
    conn.close()

def update_user_password(user_id: int, new_password: str):
    """Securely updates user password with newly generated salt and PBKDF2 hash."""
    pwd_hash, salt = hash_password(new_password)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET password_hash = ?, salt = ? WHERE id = ?;", (pwd_hash, salt, user_id))
    conn.commit()
    conn.close()

def update_user_keys(user_id: int, gemini_key: Optional[str] = None, groq_key: Optional[str] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if gemini_key is not None and groq_key is not None:
        cursor.execute("UPDATE users SET gemini_key = ?, groq_key = ? WHERE id = ?;", (gemini_key, groq_key, user_id))
    elif gemini_key is not None:
        cursor.execute("UPDATE users SET gemini_key = ? WHERE id = ?;", (gemini_key, user_id))
    elif groq_key is not None:
        cursor.execute("UPDATE users SET groq_key = ? WHERE id = ?;", (groq_key, user_id))
    conn.commit()
    conn.close()

def record_media_file(
    video_id: str,
    filename: str,
    file_path: str,
    file_size_bytes: int,
    user_id: Optional[int] = None,
    source_type: str = "upload",
    hours_to_expire: int = 72
) -> int:
    expires_at = datetime.utcnow() + timedelta(hours=hours_to_expire)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO media_files 
        (video_id, user_id, filename, file_path, file_size_bytes, source_type, expires_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'active');
    """, (video_id, user_id, filename, file_path, file_size_bytes, source_type, expires_at.strftime("%Y-%m-%d %H:%M:%S")))
    file_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return file_id

def get_expired_media_files() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        SELECT * FROM media_files 
        WHERE expires_at <= ? AND status = 'active';
    """, (now_str,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def mark_media_purged(file_ids: List[int]):
    if not file_ids:
        return
    conn = get_db_connection()
    cursor = conn.cursor()
    placeholders = ",".join("?" for _ in file_ids)
    cursor.execute(f"UPDATE media_files SET status = 'purged' WHERE id IN ({placeholders});", file_ids)
    conn.commit()
    conn.close()

def get_user_media_files(user_id: int) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM media_files 
        WHERE user_id = ? AND status = 'active'
        ORDER BY created_at DESC;
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_users_with_stats() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            u.id, u.username, u.email, u.role, u.created_at, u.last_login, u.is_active,
            COUNT(m.id) as total_videos,
            COALESCE(SUM(m.file_size_bytes), 0) as total_bytes_used
        FROM users u
        LEFT JOIN media_files m ON u.id = m.user_id AND m.status = 'active'
        GROUP BY u.id
        ORDER BY u.created_at DESC;
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_user_and_files(user_id: int) -> List[str]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT file_path FROM media_files WHERE user_id = ?;", (user_id,))
    file_paths = [r["file_path"] for r in cursor.fetchall()]
    cursor.execute("DELETE FROM media_files WHERE user_id = ?;", (user_id,))
    cursor.execute("DELETE FROM activity_logs WHERE user_id = ?;", (user_id,))
    cursor.execute("DELETE FROM users WHERE id = ?;", (user_id,))
    conn.commit()
    conn.close()
    return file_paths

def purge_user_media_records(user_id: int) -> List[str]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, file_path FROM media_files WHERE user_id = ? AND status = 'active';", (user_id,))
    rows = cursor.fetchall()
    file_paths = [r["file_path"] for r in rows]
    file_ids = [r["id"] for r in rows]
    if file_ids:
        placeholders = ",".join("?" for _ in file_ids)
        cursor.execute(f"UPDATE media_files SET status = 'purged' WHERE id IN ({placeholders});", file_ids)
    conn.commit()
    conn.close()
    return file_paths

def get_admin_system_stats() -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users;")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'user';")
    total_regular_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM media_files WHERE status = 'active';")
    active_media_count = cursor.fetchone()[0]

    cursor.execute("SELECT COALESCE(SUM(file_size_bytes), 0) FROM media_files WHERE status = 'active';")
    active_media_bytes = cursor.fetchone()[0]

    yesterday = (datetime.utcnow() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("SELECT COUNT(*) FROM users WHERE last_login >= ?;", (yesterday,))
    active_users_24h = cursor.fetchone()[0]

    conn.close()
    return {
        "total_users": total_users,
        "total_regular_users": total_regular_users,
        "active_users_24h": active_users_24h,
        "active_media_count": active_media_count,
        "active_media_bytes": active_media_bytes
    }

def log_activity(user_id: Optional[int], action: str, details: Optional[str] = None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO activity_logs (user_id, action, details)
            VALUES (?, ?, ?);
        """, (user_id, action, details))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[ActivityLog Error] {e}")

def get_user_daily_video_count(user_id: int) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(DISTINCT details) FROM activity_logs 
        WHERE user_id = ? AND action = 'transcribe' AND created_at >= date('now', 'start of day');
    """, (user_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def check_user_daily_quota(user: Dict[str, Any], video_id: Optional[str] = None) -> tuple[bool, int, int]:
    """
    Checks if user is within the 3-video-per-day rate limit.
    Admin has unlimited quota.
    Returns (is_allowed, used_today, remaining_today).
    """
    if user.get("role") == "admin":
        return True, 0, 9999

    user_id = user["id"]
    conn = get_db_connection()
    cursor = conn.cursor()

    already_counted = False
    if video_id:
        cursor.execute("""
            SELECT id FROM activity_logs 
            WHERE user_id = ? AND action = 'transcribe' AND details = ? AND created_at >= date('now', 'start of day')
            LIMIT 1;
        """, (user_id, video_id))
        already_counted = cursor.fetchone() is not None

    cursor.execute("""
        SELECT COUNT(DISTINCT details) FROM activity_logs 
        WHERE user_id = ? AND action = 'transcribe' AND created_at >= date('now', 'start of day');
    """, (user_id,))
    used_today = cursor.fetchone()[0]
    conn.close()

    if already_counted:
        return True, used_today, max(0, 3 - used_today)

    remaining = max(0, 3 - used_today)
    allowed = used_today < 3
    return allowed, used_today, remaining
