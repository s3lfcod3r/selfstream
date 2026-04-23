import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

DB_PATH = os.getenv("DB_PATH", "/data/iptv.db")


class Database:
    def __init__(self):
        self.db_path = DB_PATH

    @contextmanager
    def conn(self):
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def init(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self.conn() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    m3u_source TEXT NOT NULL,
                    active INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT (datetime('now')),
                    notes TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS watch_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    channel TEXT NOT NULL,
                    stream_url TEXT,
                    started_at TEXT DEFAULT (datetime('now')),
                    ended_at TEXT,
                    duration_seconds INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS playlist_access (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    accessed_at TEXT DEFAULT (datetime('now'))
                );

                CREATE INDEX IF NOT EXISTS idx_watch_logs_user ON watch_logs(user_id);
                CREATE INDEX IF NOT EXISTS idx_watch_logs_started ON watch_logs(started_at);
            """)

    def get_all_users(self) -> List[Dict]:
        with self.conn() as con:
            rows = con.execute("""
                SELECT u.*,
                    COUNT(DISTINCT wl.id) as total_streams,
                    COALESCE(SUM(wl.duration_seconds), 0) as total_watch_seconds,
                    MAX(wl.started_at) as last_seen
                FROM users u
                LEFT JOIN watch_logs wl ON wl.user_id = u.id
                GROUP BY u.id
                ORDER BY u.name
            """).fetchall()
            return [dict(r) for r in rows]

    def get_user_by_token(self, token: str) -> Optional[Dict]:
        with self.conn() as con:
            row = con.execute("SELECT * FROM users WHERE token = ?", (token,)).fetchone()
            return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        with self.conn() as con:
            row = con.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            return dict(row) if row else None

    def create_user(self, name: str, token: str, m3u_source: str) -> Dict:
        with self.conn() as con:
            cur = con.execute(
                "INSERT INTO users (name, token, m3u_source) VALUES (?, ?, ?)",
                (name, token, m3u_source)
            )
            return {"id": cur.lastrowid, "name": name, "token": token, "m3u_source": m3u_source, "active": 1}

    def update_user(self, user_id: int, data: Dict):
        allowed = {"name", "m3u_source", "active", "notes"}
        fields = {k: v for k, v in data.items() if k in allowed}
        if not fields:
            return
        sets = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [user_id]
        with self.conn() as con:
            con.execute(f"UPDATE users SET {sets} WHERE id = ?", vals)

    def delete_user(self, user_id: int):
        with self.conn() as con:
            con.execute("DELETE FROM watch_logs WHERE user_id = ?", (user_id,))
            con.execute("DELETE FROM playlist_access WHERE user_id = ?", (user_id,))
            con.execute("DELETE FROM users WHERE id = ?", (user_id,))

    def start_watch_log(self, user_id: int, channel: str, stream_url: str) -> int:
        with self.conn() as con:
            cur = con.execute(
                "INSERT INTO watch_logs (user_id, channel, stream_url) VALUES (?, ?, ?)",
                (user_id, channel, stream_url)
            )
            return cur.lastrowid

    def end_watch_log(self, log_id: int, duration_seconds: int):
        with self.conn() as con:
            con.execute(
                "UPDATE watch_logs SET ended_at = datetime('now'), duration_seconds = ? WHERE id = ?",
                (duration_seconds, log_id)
            )

    def log_playlist_access(self, user_id: int):
        with self.conn() as con:
            con.execute("INSERT INTO playlist_access (user_id) VALUES (?)", (user_id,))

    def get_user_logs(self, user_id: int) -> List[Dict]:
        with self.conn() as con:
            rows = con.execute("""
                SELECT * FROM watch_logs
                WHERE user_id = ?
                ORDER BY started_at DESC
                LIMIT 200
            """, (user_id,)).fetchall()
            return [dict(r) for r in rows]

    def get_all_logs(self, limit: int = 200) -> List[Dict]:
        with self.conn() as con:
            rows = con.execute("""
                SELECT wl.*, u.name as user_name
                FROM watch_logs wl
                JOIN users u ON u.id = wl.user_id
                ORDER BY wl.started_at DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]

    def get_logs_today_count(self) -> int:
        with self.conn() as con:
            row = con.execute("""
                SELECT COUNT(*) as cnt FROM watch_logs
                WHERE date(started_at) = date('now')
            """).fetchone()
            return row["cnt"]


# Type aliases for documentation
User = Dict[str, Any]
WatchLog = Dict[str, Any]
