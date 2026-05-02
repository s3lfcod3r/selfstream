import sqlite3
import os
import time
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

DB_PATH = os.getenv("DB_PATH", "/data/selfstream.db")


class Database:
    def __init__(self):
        self.db_path = DB_PATH
        self._settings_cache: dict = {}

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
                    id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    name           TEXT NOT NULL,
                    token          TEXT UNIQUE NOT NULL,
                    short_token    TEXT UNIQUE,
                    m3u_source     TEXT NOT NULL,
                    provider_id    INTEGER DEFAULT NULL,
                    active         INTEGER DEFAULT 1,
                    max_streams    INTEGER DEFAULT 1,
                    created_at     TEXT DEFAULT (datetime('now')),
                    notes          TEXT DEFAULT '',
                    allowed_groups TEXT DEFAULT NULL
                );

                CREATE TABLE IF NOT EXISTS m3u_providers (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    name          TEXT NOT NULL,
                    source_url    TEXT NOT NULL UNIQUE,
                    source_type   TEXT DEFAULT 'm3u',
                    line_capacity INTEGER DEFAULT 0,
                    active        INTEGER DEFAULT 1,
                    created_at    TEXT DEFAULT (datetime('now'))
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
                    raw_extinf TEXT DEFAULT '',
                    provider_id INTEGER DEFAULT NULL
                );
                CREATE TABLE IF NOT EXISTS segment_events (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts         REAL NOT NULL,
                    user_name  TEXT NOT NULL,
                    channel    TEXT NOT NULL,
                    provider_id INTEGER DEFAULT NULL,
                    type       TEXT NOT NULL,
                    elapsed    REAL NOT NULL,
                    size_kb    REAL DEFAULT 0,
                    mbps       REAL DEFAULT 0,
                    seg        TEXT DEFAULT '',
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_seg_events_ts ON segment_events(ts);

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

                -- Group name mappings (survives M3U refresh)
                CREATE TABLE IF NOT EXISTS group_mappings (
                    original_name TEXT PRIMARY KEY,
                    custom_name   TEXT NOT NULL,
                    created_at    TEXT DEFAULT (datetime('now'))
                );

                -- Custom user groups (independent of provider groups)
                CREATE TABLE IF NOT EXISTS user_groups (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    name       TEXT UNIQUE NOT NULL,
                    sort_order INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now'))
                );

                -- Channels assigned to custom user groups
                CREATE TABLE IF NOT EXISTS user_group_channels (
                    group_id   INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    PRIMARY KEY (group_id, channel_id),
                    FOREIGN KEY (group_id)   REFERENCES user_groups(id) ON DELETE CASCADE,
                    FOREIGN KEY (channel_id) REFERENCES channels(id)    ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_watch_logs_user    ON watch_logs(user_id);
                CREATE INDEX IF NOT EXISTS idx_watch_logs_started ON watch_logs(started_at);
                CREATE INDEX IF NOT EXISTS idx_channels_group     ON channels(group_title);
                CREATE INDEX IF NOT EXISTS idx_channels_enabled   ON channels(enabled);
            """)

    # ── Settings ──────────────────────────────────────────────────────────────

    # ── User Groups ──────────────────────────────────────────────────────────────

    def get_user_groups(self) -> List[Dict]:
        with self.conn() as con:
            rows = con.execute("""
                SELECT ug.*, COUNT(ugc.channel_id) as channel_count
                FROM user_groups ug
                LEFT JOIN user_group_channels ugc ON ugc.group_id = ug.id
                GROUP BY ug.id ORDER BY ug.sort_order, ug.name
            """).fetchall()
            return [dict(r) for r in rows]

    def create_user_group(self, name: str) -> Dict:
        with self.conn() as con:
            cur = con.execute("INSERT INTO user_groups (name) VALUES (?)", (name,))
            return {"id": cur.lastrowid, "name": name, "channel_count": 0}

    def delete_user_group(self, group_id: int):
        with self.conn() as con:
            con.execute("DELETE FROM user_group_channels WHERE group_id = ?", (group_id,))
            con.execute("DELETE FROM user_groups WHERE id = ?", (group_id,))

    def rename_user_group(self, group_id: int, name: str):
        with self.conn() as con:
            con.execute("UPDATE user_groups SET name = ? WHERE id = ?", (name, group_id))

    def reorder_user_groups(self, ordered_ids: List[int]):
        with self.conn() as con:
            for i, gid in enumerate(ordered_ids):
                con.execute("UPDATE user_groups SET sort_order = ? WHERE id = ?", (i, gid))

    def get_user_group_channels(self, group_id: int) -> List[int]:
        with self.conn() as con:
            rows = con.execute(
                "SELECT channel_id FROM user_group_channels WHERE group_id = ?", (group_id,)
            ).fetchall()
            return [r["channel_id"] for r in rows]

    def set_user_group_channels(self, group_id: int, channel_ids: List[int]):
        with self.conn() as con:
            con.execute("DELETE FROM user_group_channels WHERE group_id = ?", (group_id,))
            for cid in channel_ids:
                try:
                    con.execute(
                        "INSERT OR IGNORE INTO user_group_channels (group_id, channel_id) VALUES (?, ?)",
                        (group_id, cid)
                    )
                except Exception:
                    pass

    def add_channel_to_user_group(self, group_id: int, channel_id: int):
        with self.conn() as con:
            con.execute(
                "INSERT OR IGNORE INTO user_group_channels (group_id, channel_id) VALUES (?, ?)",
                (group_id, channel_id)
            )

    def remove_channel_from_user_group(self, group_id: int, channel_id: int):
        with self.conn() as con:
            con.execute(
                "DELETE FROM user_group_channels WHERE group_id = ? AND channel_id = ?",
                (group_id, channel_id)
            )

    def get_channels_for_user_groups(self, group_names: List[str]) -> List[Dict]:
        """Get all channels that belong to any of the given user group names."""
        with self.conn() as con:
            placeholders = ",".join("?" * len(group_names))
            rows = con.execute(f"""
                SELECT DISTINCT c.*
                FROM channels c
                JOIN user_group_channels ugc ON ugc.channel_id = c.id
                JOIN user_groups ug ON ug.id = ugc.group_id
                WHERE ug.name IN ({placeholders}) AND c.enabled = 1
                ORDER BY c.sort_order
            """, group_names).fetchall()
            return [dict(r) for r in rows]

    def get_all_user_group_names(self) -> List[str]:
        with self.conn() as con:
            rows = con.execute("SELECT name FROM user_groups ORDER BY name").fetchall()
            return [r["name"] for r in rows]

    # ── Provider Group Order ─────────────────────────────────────────────────────

    def get_provider_group_order(self) -> dict:
        """Returns {group_name: sort_order} for all saved provider group orderings."""
        with self.conn() as con:
            rows = con.execute("SELECT group_name, sort_order FROM provider_group_order").fetchall()
            return {r["group_name"]: r["sort_order"] for r in rows}

    def set_provider_group_order(self, ordered_names: List[str]):
        """Save provider group sort order."""
        with self.conn() as con:
            con.execute("DELETE FROM provider_group_order")
            for i, name in enumerate(ordered_names):
                con.execute(
                    "INSERT INTO provider_group_order (group_name, sort_order) VALUES (?, ?)",
                    (name, i)
                )

    def get_m3u_refresh_due(self) -> bool:
        """Check if global M3U needs refresh (legacy)."""
        refresh_hours = int(self.get_setting("m3u_refresh_hours", "0") or "0")
        if refresh_hours <= 0:
            return False
        last = self.get_setting("m3u_last_refresh", "0")
        last_ts = float(last) if last else 0
        return (time.time() - last_ts) >= refresh_hours * 3600

    def set_m3u_last_refresh(self):
        self.set_setting("m3u_last_refresh", str(time.time()))

    def get_providers_due_refresh(self) -> List[Dict]:
        """Return all providers whose refresh_hours > 0 and last_refresh is due."""
        now = time.time()
        with self.conn() as con:
            rows = con.execute(
                "SELECT * FROM m3u_providers WHERE refresh_hours > 0 AND source_url NOT LIKE 'local://%'"
            ).fetchall()
        due = []
        for r in rows:
            d = dict(r)
            rh = int(d.get("refresh_hours") or 0)
            last_ts = float(d.get("last_refresh") or 0)
            if rh > 0 and (now - last_ts) >= rh * 3600:
                due.append(d)
        return due

    def set_provider_last_refresh(self, provider_id: int):
        with self.conn() as con:
            con.execute(
                "UPDATE m3u_providers SET last_refresh = ? WHERE id = ?",
                (time.time(), provider_id)
            )

    def get_setting(self, key: str, default: str = None) -> Optional[str]:
        if key in self._settings_cache:
            val = self._settings_cache[key]
            return val if val is not None else default
        with self.conn() as con:
            row = con.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            val = row["value"] if row else None
            self._settings_cache[key] = val
            return val if val is not None else default

    def set_setting(self, key: str, value: str):
        with self.conn() as con:
            con.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value)
            )
        self._settings_cache[key] = value

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
        """Base URL for the IPTV proxy port (8000).
        Priority: PROXY_URL env > proxy_url setting > BASE_URL env > base_url setting"""
        # 1. Environment variable (highest priority, set in docker-compose)
        env_proxy = os.getenv("PROXY_URL", "")
        if env_proxy:
            return env_proxy.rstrip("/")
        # 2. DB setting (set via Admin UI)
        proxy_url = self.get_setting("proxy_url", "")
        if proxy_url:
            return proxy_url.rstrip("/")
        # 3. Fallback to base_url
        return self.get_base_url()

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
                    p.name as provider_name,
                    COUNT(DISTINCT wl.id)                 as total_streams,
                    COALESCE(SUM(wl.duration_seconds), 0) as total_watch_seconds,
                    MAX(wl.started_at)                    as last_seen
                FROM users u
                LEFT JOIN m3u_providers p ON p.id = u.provider_id
                LEFT JOIN watch_logs wl ON wl.user_id = u.id
                GROUP BY u.id ORDER BY u.name
            """).fetchall()
            return [dict(r) for r in rows]

    def get_user_by_token(self, token: str) -> Optional[Dict]:
        with self.conn() as con:
            row = con.execute("SELECT * FROM users WHERE token = ?", (token,)).fetchone()
            return dict(row) if row else None

    def create_user(self, name: str, token: str, m3u_source: str, notes: str = "", provider_id: int = None) -> Dict:
        with self.conn() as con:
            cur = con.execute(
                "INSERT INTO users (name, token, m3u_source, notes, provider_id) VALUES (?, ?, ?, ?, ?)",
                (name, token, m3u_source, notes, provider_id)
            )
            return {"id": cur.lastrowid, "name": name, "token": token,
                    "m3u_source": m3u_source, "active": 1, "provider_id": provider_id}

    def update_user(self, user_id: int, data: Dict):
        allowed = {"name", "m3u_source", "provider_id", "active", "notes", "max_streams", "allowed_groups"}
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

    def get_provider(self, provider_id: int) -> Optional[Dict]:
        with self.conn() as con:
            row = con.execute("SELECT * FROM m3u_providers WHERE id = ?", (provider_id,)).fetchone()
            return dict(row) if row else None

    def get_provider_by_url(self, source_url: str) -> Optional[Dict]:
        with self.conn() as con:
            row = con.execute("SELECT * FROM m3u_providers WHERE source_url = ?", (source_url,)).fetchone()
            return dict(row) if row else None

    def upsert_provider(self, name: str, source_url: str, line_capacity: int = 0, source_type: str = "m3u", refresh_hours: int = 0) -> Dict:
        source_type = (source_type or "m3u").strip().lower()
        if source_type != "m3u":
            source_type = "m3u"
        with self.conn() as con:
            row = con.execute("SELECT id FROM m3u_providers WHERE source_url = ?", (source_url,)).fetchone()
            if row:
                con.execute(
                    "UPDATE m3u_providers SET name = ?, line_capacity = ?, source_type = ?, refresh_hours = ? WHERE id = ?",
                    (name, int(line_capacity or 0), source_type, int(refresh_hours or 0), row["id"])
                )
                pid = row["id"]
            else:
                cur = con.execute(
                    "INSERT INTO m3u_providers (name, source_url, line_capacity, source_type, refresh_hours) VALUES (?, ?, ?, ?, ?)",
                    (name, source_url, int(line_capacity or 0), source_type, int(refresh_hours or 0))
                )
                pid = cur.lastrowid
            out = con.execute("SELECT * FROM m3u_providers WHERE id = ?", (pid,)).fetchone()
            return dict(out) if out else {}

    def update_provider(self, provider_id: int, name: str, source_url: str, line_capacity: int = 0, source_type: str = "m3u", refresh_hours: int = 0) -> Dict:
        source_type = (source_type or "m3u").strip().lower()
        if source_type != "m3u":
            source_type = "m3u"
        with self.conn() as con:
            con.execute(
                "UPDATE m3u_providers SET name = ?, source_url = ?, line_capacity = ?, source_type = ?, refresh_hours = ? WHERE id = ?",
                (name, source_url, int(line_capacity or 0), source_type, int(refresh_hours or 0), provider_id)
            )
            row = con.execute("SELECT * FROM m3u_providers WHERE id = ?", (provider_id,)).fetchone()
            return dict(row) if row else {}

    def delete_provider(self, provider_id: int):
        with self.conn() as con:
            con.execute("UPDATE users SET provider_id = NULL WHERE provider_id = ?", (provider_id,))
            con.execute("DELETE FROM m3u_providers WHERE id = ?", (provider_id,))

    def add_segment_event(self, event: dict):
        """Store a segment timing event in DB for long-term retention."""
        with self.conn() as con:
            con.execute("""
                INSERT INTO segment_events (ts, user_name, channel, provider_id, type, elapsed, size_kb, mbps, seg)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.get("time", 0), event.get("user", ""),
                event.get("channel", ""), event.get("provider_id"),
                event.get("type", ""), event.get("elapsed", 0),
                event.get("size_kb", 0), event.get("mbps", 0),
                event.get("seg", "")
            ))

    def get_segment_events(self, limit: int = 10000, days: int = 30, include_ok: bool = True) -> List[Dict]:
        cutoff = time.time() - (days * 86400)
        type_filter = "" if include_ok else "AND se.type != 'ok'"
        with self.conn() as con:
            rows = con.execute(f"""
                SELECT
                    se.id, se.ts, se.user_name, se.channel,
                    se.provider_id, se.type, se.elapsed,
                    se.size_kb, se.mbps, se.seg,
                    se.created_at,
                    p.name as provider_name
                FROM segment_events se
                LEFT JOIN m3u_providers p ON p.id = se.provider_id
                WHERE se.ts >= ? {type_filter}
                ORDER BY se.ts DESC
                LIMIT ?
            """, (cutoff, limit)).fetchall()
            return [dict(r) for r in rows]

    def get_segment_stats(self, days: int = 30) -> List[Dict]:
        cutoff = time.time() - (days * 86400)
        with self.conn() as con:
            rows = con.execute("""
                SELECT channel,
                    COUNT(*) as total,
                    SUM(CASE WHEN type='slow' THEN 1 ELSE 0 END) as slow,
                    SUM(CASE WHEN type='delayed' THEN 1 ELSE 0 END) as delayed,
                    ROUND(AVG(elapsed), 2) as avg_elapsed,
                    ROUND(AVG(mbps), 1) as avg_mbps,
                    ROUND(MIN(CASE WHEN mbps > 0 THEN mbps ELSE NULL END), 1) as min_mbps
                FROM segment_events
                WHERE ts >= ? AND type != 'ok'
                GROUP BY channel
                ORDER BY slow DESC, delayed DESC
            """, (cutoff,)).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                d["score"] = int(d["slow"] or 0) * 3 + int(d["delayed"] or 0)
                d["min_mbps"] = d["min_mbps"] if d["min_mbps"] is not None else 0
                out.append(d)
            out.sort(key=lambda x: x["score"], reverse=True)
            return out

    def clear_segment_events(self):
        with self.conn() as con:
            con.execute("DELETE FROM segment_events")

    def get_m3u_providers(self) -> List[Dict]:
        with self.conn() as con:
            rows = con.execute("SELECT * FROM m3u_providers ORDER BY name").fetchall()
            return [dict(r) for r in rows]

    def get_provider_capacity(self) -> List[Dict]:
        now = int(time.time())
        cutoff = now - self.SESSION_TTL
        with self.conn() as con:
            rows = con.execute("""
                SELECT
                    p.id,
                    p.name,
                    p.source_url,
                    p.source_type,
                    p.line_capacity,
                    p.refresh_hours,
                    p.last_refresh,
                    COUNT(DISTINCT u.id) as users_count,
                    COALESCE(SUM(CASE WHEN u.max_streams > 0 THEN u.max_streams ELSE 0 END), 0) as assigned_streams,
                    COALESCE(SUM(CASE WHEN u.max_streams = 0 THEN 1 ELSE 0 END), 0) as unlimited_users
                FROM m3u_providers p
                LEFT JOIN users u ON u.provider_id = p.id
                GROUP BY p.id
                ORDER BY p.name
            """).fetchall()
            # Count active sessions per provider via user→provider join
            active_rows = con.execute("""
                SELECT u.provider_id, COUNT(*) as active_count
                FROM active_sessions s
                JOIN users u ON u.token = s.token
                WHERE s.updated_at >= ?
                GROUP BY u.provider_id
            """, (cutoff,)).fetchall()
            active_by_provider = {r["provider_id"]: r["active_count"] for r in active_rows}
            out = []
            for r in rows:
                d = dict(r)
                cap = int(d.get("line_capacity") or 0)
                assigned = int(d.get("assigned_streams") or 0)
                active = int(active_by_provider.get(d["id"], 0))
                d["active_streams"] = active
                d["available_lines"] = cap - active if cap > 0 else None
                d["overbooked_by"] = max(0, active - cap) if cap > 0 else 0
                out.append(d)
            return out

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

    def upsert_channels(self, channels: List[Dict], provider_id: int = None):
        """Replace channels from a provider, preserving group mappings, sort order, enabled state and user group assignments."""
        with self.conn() as con:
            mappings = {r["original_name"]: r["custom_name"]
                        for r in con.execute("SELECT * FROM group_mappings").fetchall()}

            # Preserve existing state by stream_url base (without token query params)
            existing = {}
            for row in con.execute("""
                SELECT c.id, c.stream_url, c.enabled, c.sort_order, c.provider_id, c.group_title
                FROM channels c
            """).fetchall():
                existing[row["stream_url"].split("?")[0]] = {
                    "id": row["id"],
                    "enabled": row["enabled"],
                    "sort_order": row["sort_order"],
                    "provider_id": row["provider_id"],
                    "group_title": row["group_title"],  # preserve custom group renames
                }

            # Preserve user_group_channels by old channel id → stream_url_base
            ug_by_url = {}  # url_base → list of group_ids
            for row in con.execute("""
                SELECT c.stream_url, ugc.group_id
                FROM user_group_channels ugc
                JOIN channels c ON c.id = ugc.channel_id
            """).fetchall():
                url_base = row["stream_url"].split("?")[0]
                ug_by_url.setdefault(url_base, []).append(row["group_id"])

            if provider_id is not None:
                con.execute("DELETE FROM channels WHERE provider_id = ? OR provider_id IS NULL", (provider_id,))
            else:
                con.execute("DELETE FROM channels")

            for i, ch in enumerate(channels):
                orig_group = ch.get("group", "")
                # Apply group mapping if exists
                group = mappings.get(orig_group, orig_group)
                url = ch["url"]
                url_base = url.split("?")[0]
                prev = existing.get(url_base, {})
                enabled = prev.get("enabled", 1)
                sort_order = prev.get("sort_order", i)
                # Preserve custom group_title rename if it differs from original
                if prev.get("group_title") and prev["group_title"] != orig_group:
                    group = prev["group_title"]

                cur = con.execute("""
                    INSERT INTO channels (name, group_title, tvg_id, tvg_logo, tvg_rec, stream_url, enabled, sort_order, raw_extinf, provider_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (ch["name"], group, ch.get("tvg_id", ""),
                      ch.get("tvg_logo", ""), ch.get("tvg_rec", ""),
                      url, enabled, sort_order, ch.get("raw_extinf", ""), provider_id))

                new_id = cur.lastrowid
                # Restore user group assignments for this channel
                for gid in ug_by_url.get(url_base, []):
                    try:
                        con.execute(
                            "INSERT OR IGNORE INTO user_group_channels (group_id, channel_id) VALUES (?, ?)",
                            (gid, new_id)
                        )
                    except Exception:
                        pass

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

    def get_group_mappings(self) -> List[Dict]:
        with self.conn() as con:
            rows = con.execute("SELECT * FROM group_mappings ORDER BY original_name").fetchall()
            return [dict(r) for r in rows]

    def delete_group_mapping(self, original_name: str):
        """Remove mapping and revert channels to original group name."""
        with self.conn() as con:
            con.execute("DELETE FROM group_mappings WHERE original_name = ?", (original_name,))
            con.execute("UPDATE channels SET group_title = ? WHERE group_title IN (SELECT custom_name FROM group_mappings WHERE original_name = ?)",
                        (original_name, original_name))

    def rename_group(self, old_name: str, new_name: str):
        """Rename a group in channels table and update/create mapping."""
        with self.conn() as con:
            con.execute("UPDATE channels SET group_title = ? WHERE group_title = ?", (new_name, old_name))
            # Find original name for this group
            mapping = con.execute(
                "SELECT original_name FROM group_mappings WHERE custom_name = ?", (old_name,)
            ).fetchone()
            original = mapping["original_name"] if mapping else old_name
            if new_name != original:
                con.execute("""
                    INSERT INTO group_mappings (original_name, custom_name)
                    VALUES (?, ?)
                    ON CONFLICT(original_name) DO UPDATE SET custom_name = excluded.custom_name
                """, (original, new_name))
            else:
                con.execute("DELETE FROM group_mappings WHERE original_name = ?", (original,))

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

    def add_epg_source(self, name: str, url: str, provider_id: int = None) -> Dict:
        with self.conn() as con:
            cur = con.execute(
                "INSERT INTO epg_sources (name, url, provider_id) VALUES (?, ?, ?)", (name, url, provider_id)
            )
            return {"id": cur.lastrowid, "name": name, "url": url, "active": 1, "provider_id": provider_id}

    def update_epg_source(self, epg_id: int, data: Dict):
        allowed = {"name", "url", "active", "provider_id"}
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

    def get_user_logs(self, user_id: int, limit: int = 200, offset: int = 0, date_from: str = "", date_to: str = "") -> List[Dict]:
        where = ["user_id = ?"]
        params: List[Any] = [user_id]
        if date_from:
            where.append("date(started_at) >= date(?)")
            params.append(date_from)
        if date_to:
            where.append("date(started_at) <= date(?)")
            params.append(date_to)
        where_sql = " AND ".join(where)
        with self.conn() as con:
            total = con.execute(
                f"SELECT COUNT(*) as cnt FROM watch_logs WHERE {where_sql}", params
            ).fetchone()["cnt"]
            rows = con.execute(
                f"SELECT * FROM watch_logs WHERE {where_sql} ORDER BY started_at DESC LIMIT ? OFFSET ?",
                params + [limit, offset]
            ).fetchall()
            return {"items": [dict(r) for r in rows], "total": total}

    def clear_user_logs(self, user_id: int):
        with self.conn() as con:
            con.execute("DELETE FROM watch_logs WHERE user_id = ?", (user_id,))

    def get_all_logs(self, limit: int = 200) -> List[Dict]:
        with self.conn() as con:
            rows = con.execute("""
                SELECT wl.*, u.name as user_name
                FROM watch_logs wl
                JOIN users u ON u.id = wl.user_id
                ORDER BY wl.started_at DESC LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]

    def query_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        user_query: str = "",
        date_from: str = "",
        date_to: str = ""
    ) -> Dict[str, Any]:
        limit = max(1, min(int(limit), 500))
        offset = max(0, int(offset))
        user_query = (user_query or "").strip()
        date_from = (date_from or "").strip()
        date_to = (date_to or "").strip()

        where = []
        params: List[Any] = []
        if user_query:
            where.append("LOWER(u.name) LIKE ?")
            params.append(f"%{user_query.lower()}%")
        if date_from:
            where.append("date(wl.started_at) >= date(?)")
            params.append(date_from)
        if date_to:
            where.append("date(wl.started_at) <= date(?)")
            params.append(date_to)

        where_sql = (" WHERE " + " AND ".join(where)) if where else ""
        base_from = " FROM watch_logs wl JOIN users u ON u.id = wl.user_id"

        with self.conn() as con:
            total_row = con.execute(
                f"SELECT COUNT(*) as cnt {base_from}{where_sql}",
                params
            ).fetchone()
            stored_total_row = con.execute(
                "SELECT COUNT(*) as cnt FROM watch_logs"
            ).fetchone()
            rows = con.execute(
                f"""
                SELECT wl.*, u.name as user_name
                {base_from}{where_sql}
                ORDER BY wl.started_at DESC
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset]
            ).fetchall()
            oldest_row = con.execute(
                "SELECT MIN(started_at) as oldest, MAX(started_at) as newest FROM watch_logs"
            ).fetchone()

        return {
            "items": [dict(r) for r in rows],
            "total": int(total_row["cnt"] if total_row else 0),
            "stored_total": int(stored_total_row["cnt"] if stored_total_row else 0),
            "oldest": oldest_row["oldest"] if oldest_row else None,
            "newest": oldest_row["newest"] if oldest_row else None,
        }

    def migrate_watch_logs(self):
        """Add columns if they don't exist yet (upgrade from older version)."""
        try:
            with self.conn() as con:
                # watch_logs migrations
                wl_cols = [r[1] for r in con.execute("PRAGMA table_info(watch_logs)").fetchall()]
                if "is_catchup" not in wl_cols:
                    con.execute("ALTER TABLE watch_logs ADD COLUMN is_catchup INTEGER DEFAULT 0")
                if "catchup_time" not in wl_cols:
                    con.execute("ALTER TABLE watch_logs ADD COLUMN catchup_time TEXT DEFAULT NULL")
                if "epg_title" not in wl_cols:
                    con.execute("ALTER TABLE watch_logs ADD COLUMN epg_title TEXT DEFAULT NULL")
                # users migrations
                u_cols = [r[1] for r in con.execute("PRAGMA table_info(users)").fetchall()]
                if "allowed_groups" not in u_cols:
                    con.execute("ALTER TABLE users ADD COLUMN allowed_groups TEXT DEFAULT NULL")
                if "provider_id" not in u_cols:
                    con.execute("ALTER TABLE users ADD COLUMN provider_id INTEGER DEFAULT NULL")
                # epg_sources migration
                epg_cols = [r[1] for r in con.execute("PRAGMA table_info(epg_sources)").fetchall()]
                if "provider_id" not in epg_cols:
                    con.execute("ALTER TABLE epg_sources ADD COLUMN provider_id INTEGER DEFAULT NULL")
                # m3u_providers migration: refresh_hours + last_refresh
                prov_cols = [r[1] for r in con.execute("PRAGMA table_info(m3u_providers)").fetchall()]
                if "refresh_hours" not in prov_cols:
                    con.execute("ALTER TABLE m3u_providers ADD COLUMN refresh_hours INTEGER DEFAULT 0")
                if "last_refresh" not in prov_cols:
                    con.execute("ALTER TABLE m3u_providers ADD COLUMN last_refresh REAL DEFAULT 0")
                # channels migration: provider_id
                ch_cols = [r[1] for r in con.execute("PRAGMA table_info(channels)").fetchall()]
                if "provider_id" not in ch_cols:
                    con.execute("ALTER TABLE channels ADD COLUMN provider_id INTEGER DEFAULT NULL")
                # providers table
                con.execute("""
                    CREATE TABLE IF NOT EXISTS m3u_providers (
                        id            INTEGER PRIMARY KEY AUTOINCREMENT,
                        name          TEXT NOT NULL,
                        source_url    TEXT NOT NULL UNIQUE,
                        source_type   TEXT DEFAULT 'm3u',
                        line_capacity INTEGER DEFAULT 0,
                        active        INTEGER DEFAULT 1,
                        created_at    TEXT DEFAULT (datetime('now'))
                    )
                """)
                # group_mappings table
                con.execute("""
                    CREATE TABLE IF NOT EXISTS group_mappings (
                        original_name TEXT PRIMARY KEY,
                        custom_name   TEXT NOT NULL,
                        created_at    TEXT DEFAULT (datetime('now'))
                    )
                """)
                # user_groups and user_group_channels
                con.execute("""
                    CREATE TABLE IF NOT EXISTS user_groups (
                        id         INTEGER PRIMARY KEY AUTOINCREMENT,
                        name       TEXT UNIQUE NOT NULL,
                        sort_order INTEGER DEFAULT 0,
                        created_at TEXT DEFAULT (datetime('now'))
                    )
                """)
                # add sort_order to user_groups if missing
                ug_cols = [r[1] for r in con.execute("PRAGMA table_info(user_groups)").fetchall()]
                if "sort_order" not in ug_cols:
                    con.execute("ALTER TABLE user_groups ADD COLUMN sort_order INTEGER DEFAULT 0")
                con.execute("""
                    CREATE TABLE IF NOT EXISTS user_group_channels (
                        group_id   INTEGER NOT NULL,
                        channel_id INTEGER NOT NULL,
                        PRIMARY KEY (group_id, channel_id),
                        FOREIGN KEY (group_id)   REFERENCES user_groups(id) ON DELETE CASCADE,
                        FOREIGN KEY (channel_id) REFERENCES channels(id)    ON DELETE CASCADE
                    )
                """)
                con.execute("""
                    CREATE TABLE IF NOT EXISTS provider_group_order (
                        group_name TEXT PRIMARY KEY,
                        sort_order INTEGER DEFAULT 0
                    )
                """)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"migrate: {e}")

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
