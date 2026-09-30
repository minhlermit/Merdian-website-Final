#!/usr/bin/env python3
"""GÓI BỐI CẢNH cho LLM: chỉ những gì cần đọc cho một token, ưu tiên thông tin MỚI.

    python3 context.py 0xTOKEN                  # in JSON gọn
    python3 context.py 0xTOKEN --mark-handled   # sau khi đã viết báo cáo: đánh dấu event đã xử lý

Chi phí AI tỉ lệ với thông tin mới, không tỉ lệ với tổng dữ liệu đã quét.
"""
from __future__ import annotations

import argparse
import json
import time

import store
from ledger import attribution_table


def pick(d: dict | None, keys: list[str]) -> dict:
    return {k: (d or {}).get(k) for k in keys if (d or {}).get(k) is not None}


def build(token: str) -> dict:
    token = token.lower()
    con = store.connect()
    t = con.execute("SELECT * FROM tokens WHERE address=?", (token,)).fetchone()
    snaps = con.execute("SELECT * FROM snapshots WHERE token=? ORDER BY ts DESC LIMIT 2", (token,)).fetchall()
    delta = None
    if len(snaps) == 2:
        a, b = snaps[0], snaps[1]
        delta = {k: (round(100 * (a[k] / b[k] - 1), 1) if a[k] and b[k] else None)
                 for k in ("liq", "vol24", "buyers24", "holders")}
        delta["hours_between"] = round((a["ts"] - b["ts"]) / 3600, 1)
    events = [dict(id=r["id"], type=r["type"], severity=r["severity"], detail=json.loads(r["detail"]),
                   hours_ago=round((time.time() - r["ts"]) / 3600, 1))
              for r in con.execute("SELECT * FROM events WHERE token=? AND handled=0 ORDER BY ts DESC", (token,))]
    fact, fact_ts = store.latest_fact(con, token, "onchain")
    last_report, _ = store.latest_fact(con, token, "report_summary")
    ev = con.execute("SELECT id, url, source, category, author, posted_at, substr(text,1,500) text FROM evidence"
                     " WHERE token=? AND processed=0 ORDER BY id LIMIT 30", (token,)).fetchall()
    seen = con.execute("SELECT COUNT(*) FROM evidence WHERE token=? AND processed=1", (token,)).fetchone()[0]
    claims = [dict(r) for r in con.execute("SELECT id, claim, ctype, arg, status, detail FROM claims WHERE token=?", (token,))]
    brief = {
        "token": token, "symbol": t["symbol"] if t else None, "link": t["link"] if t else None,
        "paired_with": t["paired_with"] if t else None,
        "snapshot_now": pick(dict(snaps[0]) if snaps else None, ["liq", "vol24", "vol1", "buyers24", "sellers24", "fdv", "holders", "top10_eoa", "score"]),
        "change_vs_prev_snapshot_pct": delta,
        "open_events": events,
        "onchain_fact_age_h": round((time.time() - fact_ts) / 3600, 1) if fact_ts else None,
        "onchain": {
            "market": pick((fact or {}).get("market"), ["liq_total_usd", "vol24_total_usd", "turnover24", "sell_share", "avg_trade_usd", "fdv_to_liq", "age_days", "R_stock_per_token", "S_stock_usd"]),
            "history_7d": (fact or {}).get("history_7d"),
            "stock_float": (fact or {}).get("stock_float"),
            "stock_pair": (fact or {}).get("stock_pair"),
            "holders": pick((fact or {}).get("holders"), ["holders_count", "top10_ex_infra_pct", "top10_eoa_pct", "largest_eoa_pct", "burned_pct", "contracts_in_top20"]),
            "holder_growth": (fact or {}).get("holder_growth"),
            "deployer": (fact or {}).get("deployer"),
            "contract": (fact or {}).get("contract"),
            "supply_flows": (fact or {}).get("supply_flows"),
            "profile": (fact or {}).get("profile"),
        } if fact else None,
        "new_evidence": [dict(r) for r in ev],
        "evidence_already_processed": seen,
        "attribution": attribution_table(con, token),
        "claims": claims,
        "previous_report_summary": last_report,
    }
    return brief


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("token")
    ap.add_argument("--mark-handled", action="store_true")
    ap.add_argument("--summary", help="tóm tắt 3-5 câu của báo cáo vừa viết, lưu cho lần sau so sánh")
    a = ap.parse_args()
    if a.mark_handled or a.summary:
        con = store.connect()
        if a.mark_handled:
            con.execute("UPDATE events SET handled=1 WHERE token=?", (a.token.lower(),))
            con.execute("UPDATE evidence SET processed=1 WHERE token=?", (a.token.lower(),))
        if a.summary:
            store.save_fact(con, a.token.lower(), "report_summary", {"text": a.summary, "ts": time.time()})
        con.commit()
        print("ok")
        return
    print(json.dumps(build(a.token), ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
