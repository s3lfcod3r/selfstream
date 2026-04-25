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
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT NOT NULL,
                    token       TEXT UNIQUE NOT NULL,
                    short_token TEXT UNIQUE,
                    m3u_source  TEXT NOT NULL,
                    active      INTEGER DEFAULT 1,
                    max_streams INTEGER DEFAULT 1,
                    created_at  TEXT DEFAULT (datetime('now')),
                    notes       TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS active_sessions (
                    token      TEXT PRIMARY KEY,
                    channel    TEXT NOT NULL,
                    started_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    ip_address TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS watch_logs (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id          INTEGER NOT NULL,
                    channel          TEXT NOT NULL,
                    stream_url       TEXT,
                    ip_address       TEXT DEFAULT '',
                    started_at       TEXT DEFAULT (datetime('now')),
                    ended_at         TEXT,
                    duration_seconds INTEGER DEFAULT 0,
                    is_catchup       INTEGER DEFAULT 0,
                    catchup_time     TEXT DEFAULT NULL,
                    epg_title        TEXT DEFAULT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
                -- Migration: add is_catchup/catchup_time if missing
                CREATE TABLE IF NOT EXISTS _dummy_wl_migration (id INTEGER);

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
                    tvg_rec    TEXT DEFAULT '',
                    stream_url TEXT NOT NULL,
                    enabled    INTEGER DEFAULT 1,
                    sort_order INTEGER DEFAULT 0,
                    raw_extinf TEXT DEFAULT ''
                );

                -- EPG channel whitelist (which channels to include in filtered EPG)
                CREATE TABLE IF NOT EXISTS epg_channel_filter (
                    tvg_id     TEXT PRIMARY KEY,
                    name       TEXT NOT NULL,
                    enabled    INTEGER DEFAULT 1,
                    sort_order INTEGER DEFAULT 0,
                    icon_url   TEXT DEFAULT ''
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

    SESSION_TTL = 60  # Session gilt als inaktiv nach 60s ohne Segment-Anfrage

    def session_start(self, token: str, channel: str, ip_address: str = "") -> bool:
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
                "INSERT OR REPLACE INTO active_sessions (token, channel, started_at, updated_at, ip_address) VALUES (?, ?, ?, ?, ?)",
                (token, channel, now, now, ip_address)
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
                SELECT s.token, s.channel, s.started_at, s.ip_address, u.name as user_name
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
        allowed = {"name", "m3u_source", "active", "notes", "max_streams"}
        fields = {k: v for k, v in data.items() if k in allowed}
        if not fields:
            return
        sets = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [user_id]
        with self.conn() as con:
            con.execute(f"UPDATE users SET {sets} WHERE id = ?", vals)

    def get_user_by_short_token(self, short_token: str) -> Optional[Dict]:
        with self.conn() as con:
            row = con.execute(
                "SELECT * FROM users WHERE short_token = ?", (short_token,)
            ).fetchone()
            return dict(row) if row else None

    def generate_short_token(self, user_id: int) -> str:
        """Generate a short 8-char alphanumeric token."""
        import random, string
        chars = string.ascii_letters + string.digits
        while True:
            short = ''.join(random.choices(chars, k=8))
            with self.conn() as con:
                exists = con.execute(
                    "SELECT id FROM users WHERE short_token = ?", (short,)
                ).fetchone()
                if not exists:
                    con.execute("UPDATE users SET short_token = ? WHERE id = ?", (short, user_id))
                    return short

    def regenerate_token(self, user_id: int) -> str:
        import uuid
        new_token = str(uuid.uuid4()).replace("-", "")[:24]
        with self.conn() as con:
            con.execute("UPDATE users SET token = ? WHERE id = ?", (new_token, user_id))
        return new_token

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
                    INSERT INTO channels (name, group_title, tvg_id, tvg_logo, tvg_rec, stream_url, enabled, sort_order, raw_extinf)
                    VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
                """, (ch["name"], ch.get("group", ""), ch.get("tvg_id", ""),
                      ch.get("tvg_logo", ""), ch.get("tvg_rec", ""),
                      ch["url"], i, ch.get("raw_extinf", "")))

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

    def get_channel_by_name(self, name: str) -> Optional[Dict]:
        with self.conn() as con:
            row = con.execute(
                "SELECT * FROM channels WHERE name = ? LIMIT 1", (name,)
            ).fetchone()
            return dict(row) if row else None

    def get_channel_by_url(self, stream_url: str) -> Optional[Dict]:
        """Exact URL match – used when we have the full stream URL."""
        # Strip token from URL for matching since tokens change
        base_url = stream_url.split("?")[0]
        with self.conn() as con:
            row = con.execute(
                "SELECT * FROM channels WHERE stream_url LIKE ? LIMIT 1",
                (base_url + "%",)
            ).fetchone()
            return dict(row) if row else None

    def get_channel_by_url_fragment(self, segment_url: str) -> Optional[Dict]:
        """Match channel from a .ts segment URL by extracting the channel path."""
        # Extract /chXXX/ from segment URL like /ch265/2026/04/...
        import re
        m = re.search(r'/(ch\d+)/', segment_url)
        if not m:
            return None
        ch_id = m.group(1)
        with self.conn() as con:
            row = con.execute(
                "SELECT * FROM channels WHERE stream_url LIKE ? LIMIT 1",
                (f"%/{ch_id}/%",)
            ).fetchone()
            return dict(row) if row else None

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

    def start_watch_log(self, user_id: int, channel: str, stream_url: str, ip_address: str = "", is_catchup: int = 0, catchup_time: str = None, epg_title: str = None) -> int:
        with self.conn() as con:
            cur = con.execute(
                "INSERT INTO watch_logs (user_id, channel, stream_url, ip_address, is_catchup, catchup_time, epg_title) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, channel, stream_url, ip_address, is_catchup, catchup_time, epg_title)
            )
            return cur.lastrowid

    def end_watch_log(self, log_id: int, duration_seconds: int, epg_title: str = None):
        with self.conn() as con:
            if epg_title:
                con.execute(
                    "UPDATE watch_logs SET ended_at = datetime('now'), duration_seconds = ?, epg_title = ? WHERE id = ?",
                    (duration_seconds, epg_title, log_id)
                )
            else:
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

    def migrate_watch_logs(self):
        """Add columns if they don't exist yet (upgrade from older version)."""
        try:
            with self.conn() as con:
                cols = [r[1] for r in con.execute("PRAGMA table_info(watch_logs)").fetchall()]
                if "is_catchup" not in cols:
                    con.execute("ALTER TABLE watch_logs ADD COLUMN is_catchup INTEGER DEFAULT 0")
                if "catchup_time" not in cols:
                    con.execute("ALTER TABLE watch_logs ADD COLUMN catchup_time TEXT DEFAULT NULL")
                if "epg_title" not in cols:
                    con.execute("ALTER TABLE watch_logs ADD COLUMN epg_title TEXT DEFAULT NULL")
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"migrate_watch_logs: {e}")

    def get_epg_channels(self) -> List[Dict]:
        with self.conn() as con:
            rows = con.execute(
                "SELECT * FROM epg_channel_filter ORDER BY sort_order, name"
            ).fetchall()
            return [dict(r) for r in rows]

    def upsert_epg_channels(self, channels: list):
        """Bulk insert/update EPG channels from parsed XML."""
        with self.conn() as con:
            for i, ch in enumerate(channels):
                sort_val = ch.get("sort_order", i)
                icon = ch.get("icon_url", "")
                con.execute("""
                    INSERT INTO epg_channel_filter (tvg_id, name, enabled, sort_order, icon_url)
                    VALUES (?, ?, 1, ?, ?)
                    ON CONFLICT(tvg_id) DO UPDATE SET
                        name=excluded.name,
                        sort_order=excluded.sort_order,
                        icon_url=excluded.icon_url
                """, (ch["tvg_id"], ch["name"], sort_val, icon))

    def update_epg_channel(self, tvg_id: str, data: dict):
        allowed = {"enabled", "sort_order"}
        fields = {k: v for k, v in data.items() if k in allowed}
        if not fields:
            return
        sets = ", ".join(f"{k}=?" for k in fields)
        vals = list(fields.values()) + [tvg_id]
        with self.conn() as con:
            con.execute(f"UPDATE epg_channel_filter SET {sets} WHERE tvg_id=?", vals)

    def get_enabled_epg_ids(self) -> set:
        with self.conn() as con:
            rows = con.execute(
                "SELECT tvg_id FROM epg_channel_filter WHERE enabled=1"
            ).fetchall()
            return {r["tvg_id"] for r in rows}

    def clear_logs(self, days: int = 0):
        """Delete logs older than X days. days=0 means delete all."""
        with self.conn() as con:
            if days == 0:
                con.execute("DELETE FROM watch_logs")
            else:
                con.execute(
                    "DELETE FROM watch_logs WHERE started_at < datetime('now', ? || ' days')",
                    (f"-{days}",)
                )

    def get_logs_today_count(self) -> int:
        """Count distinct channel sessions today (min 10s duration or still active)."""
        with self.conn() as con:
            row = con.execute("""
                SELECT COUNT(*) as cnt FROM watch_logs
                WHERE date(started_at) = date('now')
                AND (duration_seconds >= 10 OR duration_seconds IS NULL OR duration_seconds = 0)
            """).fetchone()
            return row["cnt"]


User = Dict[str, Any]
WatchLog = Dict[str, Any]
