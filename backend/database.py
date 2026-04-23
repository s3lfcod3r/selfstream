import sqlite3
import os
import time
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

DB_PATH = os.getenv("DB_PATH", "/data/selfstream.db")


class Database:
    def __init__(self):
        self.db_path = DB_PATH

    @contextmanager
    def conn(self):
        con = sqlite3.connect(self.db_path, timeout=10)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA foreign_keys=ON")
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
                CREATE TABLE IF NOT EXISTS settings (
                    key   TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS users (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    name       TEXT NOT NULL,
                    token      TEXT UNIQUE NOT NULL,
                    m3u_source TEXT NOT NULL,
                    active     INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT (datetime('now')),
                    notes      TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS active_sessions (
                    token      TEXT PRIMARY KEY,
                    channel    TEXT NOT NULL,
                    started_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS watch_logs (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id          INTEGER NOT NULL,
                    channel          TEXT NOT NULL,
                    stream_url       TEXT,
                    started_at       TEXT DEFAULT (datetime('now')),
                    ended_at         TEXT,
                    duration_seconds INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS playlist_access (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL,
                    accessed_at TEXT DEFAULT (datetime('now'))
                );

                -- Global channel list parsed from source m3u
                CREATE TABLE IF NOT EXISTS channels (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    name       TEXT NOT NULL,
                    group_title TEXT DEFAULT '',
                    tvg_id     TEXT DEFAULT '',
                    tvg_logo   TEXT DEFAULT '',
                    stream_url TEXT NOT NULL,
                    enabled    INTEGER DEFAULT 1,
                    sort_order INTEGER DEFAULT 0,
                    raw_extinf TEXT DEFAULT ''
                );

                -- EPG sources
                CREATE TABLE IF NOT EXISTS epg_sources (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    name       TEXT NOT NULL,
                    url        TEXT NOT NULL,
                    active     INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE INDEX IF NOT EXISTS idx_watch_logs_user    ON watch_logs(user_id);
                CREATE INDEX IF NOT EXISTS idx_watch_logs_started ON watch_logs(started_at);
                CREATE INDEX IF NOT EXISTS idx_channels_group     ON channels(group_title);
                CREATE INDEX IF NOT EXISTS idx_channels_enabled   ON channels(enabled);
            """)

    # ── Settings ──────────────────────────────────────────────────────────────

    def get_setting(self, key: str, default: str = None) -> Optional[str]:
        with self.conn() as con:
            row = con.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: str):
        with self.conn() as con:
            con.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value)
            )

    def get_all_settings(self) -> Dict:
        with self.conn() as con:
            rows = con.execute("SELECT key, value FROM settings").fetchall()
            return {r["key"]: r["value"] for r in rows}

    def is_setup_done(self) -> bool:
        env_token = os.getenv("ADMIN_TOKEN", "")
        if env_token and env_token not in ("", "setup"):
            return True
        val = self.get_setting("admin_token")
        return bool(val and val.strip())

    def get_admin_token(self) -> Optional[str]:
        env_token = os.getenv("ADMIN_TOKEN", "")
        if env_token and env_token not in ("", "setup"):
            return env_token
        return self.get_setting("admin_token")

    def get_base_url(self) -> str:
        env_url = os.getenv("BASE_URL", "")
        if env_url:
            return env_url.rstrip("/")
        return self.get_setting("base_url", "http://localhost:8000").rstrip("/")

    def get_proxy_url(self) -> str:
        """Base URL for the IPTV proxy port (8000)."""
        base = self.get_base_url()
        # Replace admin port 8080 with proxy port 8000 if needed
        proxy_url = self.get_setting("proxy_url", "")
        if proxy_url:
            return proxy_url.rstrip("/")
        return base

    # ── Sessions ──────────────────────────────────────────────────────────────

    SESSION_TTL = 14400

    def session_start(self, token: str, channel: str) -> bool:
        now = int(time.time())
        cutoff = now - self.SESSION_TTL
        with self.conn() as con:
            con.execute("DELETE FROM active_sessions WHERE updated_at < ?", (cutoff,))
            existing = con.execute(
                "SELECT token FROM active_sessions WHERE token = ? AND updated_at >= ?",
                (token, cutoff)
            ).fetchone()
            if existing:
                return False
            con.execute(
                "INSERT OR REPLACE INTO active_sessions (token, channel, started_at, updated_at) VALUES (?, ?, ?, ?)",
                (token, channel, now, now)
            )
            return True

    def session_refresh(self, token: str):
        now = int(time.time())
        with self.conn() as con:
            con.execute("UPDATE active_sessions SET updated_at = ? WHERE token = ?", (now, token))

    def session_end(self, token: str):
        with self.conn() as con:
            con.execute("DELETE FROM active_sessions WHERE token = ?", (token,))

    def get_active_sessions(self) -> List[Dict]:
        now = int(time.time())
        cutoff = now - self.SESSION_TTL
        with self.conn() as con:
            rows = con.execute("""
                SELECT s.token, s.channel, s.started_at, u.name as user_name
                FROM active_sessions s
                JOIN users u ON u.token = s.token
                WHERE s.updated_at >= ?
            """, (cutoff,)).fetchall()
            return [dict(r) for r in rows]

    # ── Users ─────────────────────────────────────────────────────────────────

    def get_all_users(self) -> List[Dict]:
        with self.conn() as con:
            rows = con.execute("""
                SELECT u.*,
                    COUNT(DISTINCT wl.id)                 as total_streams,
                    COALESCE(SUM(wl.duration_seconds), 0) as total_watch_seconds,
                    MAX(wl.started_at)                    as last_seen
                FROM users u
                LEFT JOIN watch_logs wl ON wl.user_id = u.id
                GROUP BY u.id ORDER BY u.name
            """).fetchall()
            return [dict(r) for r in rows]

    def get_user_by_token(self, token: str) -> Optional[Dict]:
        with self.conn() as con:
            row = con.execute("SELECT * FROM users WHERE token = ?", (token,)).fetchone()
            return dict(row) if row else None

    def create_user(self, name: str, token: str, m3u_source: str, notes: str = "") -> Dict:
        with self.conn() as con:
            cur = con.execute(
                "INSERT INTO users (name, token, m3u_source, notes) VALUES (?, ?, ?, ?)",
                (name, token, m3u_source, notes)
            )
            return {"id": cur.lastrowid, "name": name, "token": token,
                    "m3u_source": m3u_source, "active": 1}

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

    # ── Channels ──────────────────────────────────────────────────────────────

    def get_channels(self, enabled_only: bool = False) -> List[Dict]:
        with self.conn() as con:
            q = "SELECT * FROM channels"
            if enabled_only:
                q += " WHERE enabled = 1"
            q += " ORDER BY sort_order, name"
            return [dict(r) for r in con.execute(q).fetchall()]

    def get_channel_groups(self) -> List[str]:
        with self.conn() as con:
            rows = con.execute(
                "SELECT DISTINCT group_title FROM channels ORDER BY group_title"
            ).fetchall()
            return [r["group_title"] for r in rows]

    def upsert_channels(self, channels: List[Dict]):
        """Replace all channels with fresh parsed list."""
        with self.conn() as con:
            con.execute("DELETE FROM channels")
            for i, ch in enumerate(channels):
                con.execute("""
                    INSERT INTO channels (name, group_title, tvg_id, tvg_logo, stream_url, enabled, sort_order, raw_extinf)
                    VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                """, (ch["name"], ch.get("group", ""), ch.get("tvg_id", ""),
                      ch.get("tvg_logo", ""), ch["url"], i, ch.get("raw_extinf", "")))

    def update_channel(self, channel_id: int, data: Dict):
        allowed = {"enabled", "sort_order", "name", "group_title"}
        fields = {k: v for k, v in data.items() if k in allowed}
        if not fields:
            return
        sets = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [channel_id]
        with self.conn() as con:
            con.execute(f"UPDATE channels SET {sets} WHERE id = ?", vals)

    def set_group_enabled(self, group: str, enabled: int):
        with self.conn() as con:
            con.execute("UPDATE channels SET enabled = ? WHERE group_title = ?", (enabled, group))

    def get_channels_count(self) -> Dict:
        with self.conn() as con:
            row = con.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN enabled=1 THEN 1 ELSE 0 END) as enabled
                FROM channels
            """).fetchone()
            return dict(row)

    # ── EPG Sources ───────────────────────────────────────────────────────────

    def get_epg_sources(self) -> List[Dict]:
        with self.conn() as con:
            return [dict(r) for r in con.execute(
                "SELECT * FROM epg_sources ORDER BY name"
            ).fetchall()]

    def add_epg_source(self, name: str, url: str) -> Dict:
        with self.conn() as con:
            cur = con.execute(
                "INSERT INTO epg_sources (name, url) VALUES (?, ?)", (name, url)
            )
            return {"id": cur.lastrowid, "name": name, "url": url, "active": 1}

    def update_epg_source(self, epg_id: int, data: Dict):
        allowed = {"name", "url", "active"}
        fields = {k: v for k, v in data.items() if k in allowed}
        if not fields:
            return
        sets = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [epg_id]
        with self.conn() as con:
            con.execute(f"UPDATE epg_sources SET {sets} WHERE id = ?", vals)

    def delete_epg_source(self, epg_id: int):
        with self.conn() as con:
            con.execute("DELETE FROM epg_sources WHERE id = ?", (epg_id,))

    # ── Watch Logs ────────────────────────────────────────────────────────────

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
                SELECT * FROM watch_logs WHERE user_id = ?
                ORDER BY started_at DESC LIMIT 200
            """, (user_id,)).fetchall()
            return [dict(r) for r in rows]

    def get_all_logs(self, limit: int = 200) -> List[Dict]:
        with self.conn() as con:
            rows = con.execute("""
                SELECT wl.*, u.name as user_name
                FROM watch_logs wl
                JOIN users u ON u.id = wl.user_id
                ORDER BY wl.started_at DESC LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]

    def get_logs_today_count(self) -> int:
        with self.conn() as con:
            row = con.execute(
                "SELECT COUNT(*) as cnt FROM watch_logs WHERE date(started_at) = date('now')"
            ).fetchone()
            return row["cnt"]


User = Dict[str, Any]
WatchLog = Dict[str, Any]
