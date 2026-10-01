"""Kho dữ liệu cục bộ (SQLite) cho Stock Token Scout v2.

Mọi lượt chạy đều ghi vào đây để:
- so snapshot với lần trước (sinh event, không cần stream realtime);
- chỉ đưa bằng chứng MỚI cho LLM (tiết kiệm credit);
- lưu attribution và claim cùng mức tin cậy.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time

import common as c

LEVELS = ("VERIFIED_ONCHAIN", "VERIFIED_OFFCHAIN", "LIKELY", "UNCONFIRMED", "CONFLICT")

SCHEMA = """
CREATE TABLE IF NOT EXISTS tokens(
  address TEXT PRIMARY KEY, symbol TEXT, name TEXT, link TEXT, paired_with TEXT,
  first_seen REAL, last_seen REAL, status TEXT DEFAULT 'watch');
CREATE TABLE IF NOT EXISTS pools(
  pool TEXT PRIMARY KEY, token TEXT, counter_addr TEXT, stock TEXT, dex TEXT,
  first_seen REAL, last_liq REAL);
CREATE TABLE IF NOT EXISTS snapshots(
  id INTEGER PRIMARY KEY AUTOINCREMENT, token TEXT, ts REAL, liq REAL, vol24 REAL, vol1 REAL,
  buys24 INTEGER, sells24 INTEGER, buyers24 INTEGER, sellers24 INTEGER, fdv REAL, price REAL,
  holders INTEGER, top10_eoa REAL, score INTEGER);
CREATE INDEX IF NOT EXISTS snap_tok ON snapshots(token, ts);
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY AUTOINCREMENT, token TEXT, ts REAL, type TEXT, severity INTEGER,
  detail TEXT, handled INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS facts(
  id INTEGER PRIMARY KEY AUTOINCREMENT, token TEXT, ts REAL, kind TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS evidence(
  id INTEGER PRIMARY KEY AUTOINCREMENT, token TEXT, url TEXT, source TEXT, category TEXT,
  author TEXT, posted_at TEXT, text TEXT, hash TEXT, first_seen REAL, processed INTEGER DEFAULT 0,
  UNIQUE(token, hash));
CREATE TABLE IF NOT EXISTS pages(
  url TEXT, token TEXT, hash TEXT, text TEXT, last_checked REAL, PRIMARY KEY(url, token));
CREATE TABLE IF NOT EXISTS bridges(
  id INTEGER PRIMARY KEY AUTOINCREMENT, token TEXT, subject TEXT, entity TEXT, bridge TEXT,
  url TEXT, note TEXT, ts REAL, UNIQUE(token, subject, entity, bridge, url));
CREATE TABLE IF NOT EXISTS claims(
  id INTEGER PRIMARY KEY AUTOINCREMENT, token TEXT, claim TEXT, ctype TEXT, arg TEXT,
  source_url TEXT, status TEXT DEFAULT 'UNCONFIRMED', detail TEXT, ts REAL,
  UNIQUE(token, ctype, arg, claim));
"""


MIGRATIONS = {"snapshots": {"main_liq": "REAL", "n_pools": "INTEGER", "chg24": "REAL", "sell_share": "REAL"}}


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(c.cache_path("scout.db"))
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    for table, cols in MIGRATIONS.items():
        have = {r[1] for r in con.execute(f"PRAGMA table_info({table})")}
        for col, typ in cols.items():
            if col not in have:
                con.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
    return con


def norm_text(t: str) -> str:
    t = re.sub(r"https?://\S+", "", t or "")
    return re.sub(r"\s+", " ", t).strip().lower()


def text_hash(url: str, text: str) -> str:
    """Bài đăng lại (cùng nội dung) hoặc cùng URL đều bị coi là đã thấy."""
    key = (url or "").split("?")[0].rstrip("/").lower() or norm_text(text)[:500]
    return hashlib.sha256(key.encode()).hexdigest()[:24]


def last_snapshot(con, token: str):
    return con.execute("SELECT * FROM snapshots WHERE token=? ORDER BY ts DESC LIMIT 1", (token,)).fetchone()


def add_snapshot(con, token: str, s: dict):
    con.execute(
        "INSERT INTO snapshots(token, ts, liq, vol24, vol1, buys24, sells24, buyers24, sellers24, fdv, price,"
        " holders, top10_eoa, score, main_liq, n_pools, chg24, sell_share) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (token, time.time(), s.get("liq"), s.get("vol24"), s.get("vol1"), s.get("buys24"), s.get("sells24"),
         s.get("buyers24"), s.get("sellers24"), s.get("fdv"), s.get("price"), s.get("holders"),
         s.get("top10_eoa"), s.get("score"), s.get("main_liq"), s.get("n_pools"), s.get("chg24"),
         s.get("sell_share")))


def add_event(con, token: str, etype: str, severity: int, detail: dict):
    # không lặp lại cùng loại event cho cùng token trong 12 giờ
    recent = con.execute("SELECT 1 FROM events WHERE token=? AND type=? AND ts>?",
                         (token, etype, time.time() - 12 * 3600)).fetchone()
    if recent:
        return False
    con.execute("INSERT INTO events(token, ts, type, severity, detail) VALUES(?,?,?,?,?)",
                (token, time.time(), etype, severity, json.dumps(detail, ensure_ascii=False)))
    return True


def save_fact(con, token: str, kind: str, data: dict):
    con.execute("INSERT INTO facts(token, ts, kind, data) VALUES(?,?,?,?)",
                (token, time.time(), kind, json.dumps(data, ensure_ascii=False, default=str)))


def latest_fact(con, token: str, kind: str):
    r = con.execute("SELECT data, ts FROM facts WHERE token=? AND kind=? ORDER BY ts DESC LIMIT 1",
                    (token, kind)).fetchone()
    return (json.loads(r["data"]), r["ts"]) if r else (None, None)
