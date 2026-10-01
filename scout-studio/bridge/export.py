#!/usr/bin/env python3
"""Read-only JSON projection of the bundled Stock Token Scout's existing output.

The research-core remains the authority for scoring and exit-risk rules. This
file never scans a chain, creates synthetic evidence, or modifies the Scout DB.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
CORE = Path(os.getenv("STS_PROJECT_DIR", ROOT / "research-core")).expanduser()
CACHE = Path(os.getenv("STS_CACHE_DIR", Path.home() / ".stock-token-scout")).expanduser()
sys.path.insert(0, str(CORE / ".claude/skills/scout-reader/scripts"))
sys.path.insert(0, str(CORE / ".claude/skills/stock-token-scout/scripts"))
import run_report as rr  # noqa: E402


def table_exists(db: sqlite3.Connection, name: str) -> bool:
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def latest_manifest() -> dict:
    current = CACHE / "runs/current"
    if not current.is_file():
        return {}
    run_id = current.read_text(encoding="utf-8").strip()
    if not run_id.isascii() or not run_id.replace("_", "").replace("-", "").isalnum() or len(run_id) > 40:
        return {}
    manifest = CACHE / "runs" / run_id / "manifest.json"
    try:
        return json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def text_value(value, max_chars: int = 550) -> str:
    if isinstance(value, str):
        return value[:max_chars]
    if isinstance(value, dict):
        return str(value.get("summary") or value.get("text") or value.get("description") or "")[:max_chars]
    return ""


def strings(value, max_items: int = 4) -> list[str]:
    if isinstance(value, str):
        return [value[:240]] if value else []
    if not isinstance(value, list):
        return []
    return [t for x in value[:max_items] if (t := text_value(x, 240))]


def export() -> dict:
    manifest = latest_manifest()
    cycle_start = int(time.time() // 21600) * 21600
    run_id = manifest.get("run_id") if (manifest.get("created") or 0) >= cycle_start else None
    report = Path(os.getenv("STS_REPORT_DIR", CACHE / "reports")) / "latest.html"
    result = {"schema": 1, "generated": time.time(), "source": "local", "runId": run_id,
              "reportAvailable": report.is_file() and report.stat().st_mtime >= cycle_start, "candidates": [], "events": [], "warnings": []}
    queue = CACHE / "queue.json"
    try:
        result["warnings"] = json.loads(queue.read_text(encoding="utf-8")).get("warnings", [])[:8]
    except (OSError, ValueError, TypeError):
        pass
    path = CACHE / "scout.db"
    if not path.is_file():
        result["warnings"].append("No local scout.db found. Run research-core before expecting live candidates.")
        return result
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        if not table_exists(db, "tokens"):
            return result
        rows = db.execute("SELECT address,symbol,name,paired_with,last_seen FROM tokens WHERE last_seen>=? ORDER BY last_seen DESC LIMIT 80", (cycle_start,)).fetchall()
        entries = (manifest.get("tokens") or {}) if run_id else {}
        if not rows:
            result["warnings"].append("No Scout snapshot in the current six-hour window. The candidate board has reset; run a fresh cycle.")
        for row in rows:
            addr = row["address"]
            entry = entries.get(addr) or {}
            fact, fact_ts = rr.onchain_fact(db, addr)
            market = rr.metrics(db, addr)
            potential = rr._potential(entry)
            pair_label, pair_kind = rr.pair_label(fact)
            pair = pair_label.split("/", 1)[-1] if "/" in pair_label else (row["paired_with"] or "?")
            profile = rr.links(fact)
            investor = {}
            if entry.get("research_status") == "COMPLETE" and run_id:
                investor_path = CACHE / "runs" / run_id / "investor" / f"{addr}.json"
                try:
                    investor = json.loads(investor_path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    pass
            history = []
            if table_exists(db, "snapshots"):
                history = [r["liq"] for r in db.execute("SELECT liq FROM (SELECT liq,ts FROM snapshots WHERE token=? AND liq IS NOT NULL ORDER BY ts DESC LIMIT 24) ORDER BY ts", (addr,)).fetchall()]
            evidence = []
            if table_exists(db, "claims"):
                for c in db.execute("SELECT claim,status,detail,source_url FROM claims WHERE token=? ORDER BY ts DESC LIMIT 8", (addr,)):
                    status = c["status"] if c["status"] in rr.store.LEVELS else "UNCONFIRMED"
                    evidence.append({"label": text_value(c["claim"], 160), "level": status,
                                     "detail": text_value(c["detail"], 220), "url": c["source_url"] or None})
            if not evidence and table_exists(db, "evidence"):
                for e in db.execute("SELECT text,url,source FROM evidence WHERE token=? ORDER BY first_seen DESC LIMIT 6", (addr,)):
                    evidence.append({"label": text_value(e["text"], 160) or text_value(e["source"], 160),
                                     "level": "UNCONFIRMED", "url": e["url"] or None})
            risks = strings(investor.get("red_flags")) or strings(investor.get("risks"))
            if not risks:
                risks = strings(market.get("exit_risk_reasons"), 3)
            result["candidates"].append({
                "address": addr, "symbol": fact.get("symbol") or row["symbol"] or addr[:8],
                "name": fact.get("name") or row["name"] or "Unknown token", "pair": pair,
                "isOfficialPair": True if pair_kind == "stock" else False if pair_kind == "fake" else None,
                "researchStatus": entry.get("research_status") or "WATCH", "mode": entry.get("mode"),
                "verdict": potential.get("verdict") or "UNRATED", "conviction": investor.get("conviction"),
                "growth": investor.get("growth_verdict"), "exitRisk": market.get("exit_risk_floor") or "UNKNOWN",
                "liquidity": market.get("liq"), "volume24": market.get("vol24"), "holders": market.get("holders"),
                "top10": market.get("top10_eoa"), "score": potential.get("total") if potential.get("max") else None,
                "scoreMax": potential.get("max") or None, "price": (fact.get("market") or {}).get("price_usd"),
                "liquidityHistory": history, "updated": fact_ts or row["last_seen"],
                "thesis": text_value(investor.get("project_thesis")), "product": text_value(investor.get("product")),
                "growthEngine": text_value(investor.get("growth_engine")), "risks": risks,
                "catalysts": strings(investor.get("catalysts")), "evidence": evidence,
                "links": {"site": (profile["websites"] or [None])[0], "x": profile.get("x"),
                          "explorer": f"https://robinhoodchain.blockscout.com/token/{addr}"},
            })
        if table_exists(db, "events"):
            for e in db.execute("SELECT e.id,e.type,e.token,e.ts,e.severity,e.detail,t.symbol FROM events e LEFT JOIN tokens t ON t.address=e.token WHERE e.ts>=? ORDER BY e.ts DESC LIMIT 40", (cycle_start,)):
                result["events"].append({"id": str(e["id"]), "type": e["type"], "token": e["token"],
                                         "symbol": e["symbol"] or e["token"][:8], "time": e["ts"],
                                         "severity": e["severity"], "detail": text_value(e["detail"], 260)})
        return result
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export Scout's local research state as JSON")
    parser.add_argument("--out", type=Path, help="Write JSON to a file for upload into the hosted interface")
    args = parser.parse_args()
    data = json.dumps(export(), ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(data, encoding="utf-8")
        print(args.out)
    else:
        print(data)
