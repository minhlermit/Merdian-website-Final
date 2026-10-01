#!/usr/bin/env python3
"""MỘT CHU KỲ SCOUT (tất định, không gọi LLM).

discover → snapshot → so với lần trước → sinh event → lập hàng đợi điều tra.

    python3 scripts/scout_cycle.py                 # in tóm tắt, ghi queue.json
    python3 scripts/scout_cycle.py --max-queue 5

Mã thoát: 0 = không có gì đáng điều tra | 10 = có hàng đợi (gọi LLM) | 2 = không lấy được dữ liệu
| 3 = chế độ tải hộ (STS_OFFLINE=1) còn thiếu dữ liệu, chưa ghi gì vào kho.
Dùng mã thoát này trong cron để CHỈ gọi Claude khi có tín hiệu.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import common as c
import store
import discover
from discover import collect, enrich_profiles, quick_score, summarize

# ngưỡng sự kiện (heuristic, chỉnh trong ~/.stock-token-scout/rules.json nếu muốn)
RULES = {
    "min_liq_candidate": 20_000,
    "liq_collapse_pct": 40,
    "liq_expansion_pct": 100,
    "vol_accel_x": 3.0,
    "vol_accel_min_vol24": 20_000,
    "participant_surge_pct": 100,
    "first_run_top_n": 5,
    "severity_to_queue": 2,
    "new_pool_max_age_h": 72,
}
COMPLETE_TOP = int(os.getenv("STS_COMPLETE_TOP", "10"))
SEV = {"NEW_STOCK_PAIRED_POOL": 3, "LIQUIDITY_COLLAPSE": 3, "NEW_CANDIDATE": 2, "VOLUME_ACCELERATION": 2,
       "PARTICIPANT_SURGE": 2, "LIQUIDITY_EXPANSION": 1, "HONEYPOT_PATTERN": 3, "FAKE_STOCK_PAIR": 3}


def diagnose_collapse(prev, s: dict) -> list[dict]:
    """Mô tả sự kiện trước, nguyên nhân sau: gợi ý nguyên nhân bằng heuristic, KHÔNG kết luận.

    Mọi gợi ý ở đây mang mức LIKELY hoặc UNCONFIRMED và phải được kiểm chứng bằng onchain.py / Blockscout.
    """
    hints = []
    chg = s.get("chg24_pct")
    if (s.get("n_pools") or 0) > (prev["n_pools"] or 0):
        hints.append({"cause": "chuyển sang pool/sàn khác hoặc migration", "level": "LIKELY",
                      "why": f"số pool tăng từ {prev['n_pools']} lên {s['n_pools']}"})
    if chg is not None and abs(chg) < 15:
        hints.append({"cause": "LP rút hoặc đổi range thanh khoản tập trung", "level": "LIKELY",
                      "why": f"thanh khoản giảm mạnh trong khi giá 24h chỉ đổi {chg:.1f}%"})
    if chg is not None and chg <= -40 and (s.get("sell_share") or 0) > 0.6:
        hints.append({"cause": "bán tháo kéo cạn phía tài sản quote của pool", "level": "LIKELY",
                      "why": f"giá 24h {chg:.1f}%, tỉ lệ lệnh bán {s['sell_share']:.0%}"})
    if not hints:
        hints.append({"cause": "chưa xác định", "level": "UNCONFIRMED",
                      "why": "không khớp mẫu nào; cần đọc lệnh chuyển của pool trên Blockscout"})
    return hints


def load_rules() -> dict:
    user = c.load_cache("rules.json")
    return {**RULES, **user}


def run(max_queue: int) -> int:
    rules = load_rules()
    con = store.connect()
    wl = c.load_whitelist()
    raw = collect(wl, gt_pages=2)
    # Đủ pool là điều kiện để điểm và thanh khoản đúng. Ở chế độ tải hộ, bắt buộc cho COMPLETE_TOP ứng viên có
    # thanh khoản lớn nhất (không chờ tải hết hàng chục token); phần còn lại và hồ sơ là tuỳ chọn.
    related = sorted((a for a, x in raw.items() if summarize(x)["link"] != "none"),
                     key=lambda a: -summarize(raw[a])["liq_usd"])
    top_n = COMPLETE_TOP if c.OFFLINE else len(related)
    discover.complete_pools(raw, wl, related[:top_n])
    with c.optional_fetch():
        discover.complete_pools(raw, wl, related[top_n:])
        enrich_profiles(raw)
    if c.OFFLINE and c.MISSING_THIS_RUN:
        # chế độ tải hộ: chưa ghi gì vào kho để snapshot thiếu dữ liệu không sinh event sai
        print(f"Còn thiếu {len(set(c.MISSING_THIS_RUN))} phản hồi API. Chạy `fetched.py missing`, tải và lưu, "
              "rồi chạy lại (references/data_fallback.md).")
        return 3
    if not raw and c.WARNINGS:
        print("Không lấy được dữ liệu:", *c.WARNINGS[:5], sep="\n- ")
        return 2
    first_run = con.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 0
    now = time.time()
    fired = []

    rows = []
    for addr, x in raw.items():
        s = summarize(x)
        if s["link"] == "none":
            continue
        s["score"], s["flags"] = quick_score(s)
        rows.append((addr, x, s))
    rows.sort(key=lambda r: -r[2]["score"])

    for rank, (addr, x, s) in enumerate(rows):
        prev = store.last_snapshot(con, addr)
        known = con.execute("SELECT 1 FROM tokens WHERE address=?", (addr,)).fetchone()
        con.execute(
            "INSERT INTO tokens(address, symbol, name, link, paired_with, first_seen, last_seen) VALUES(?,?,?,?,?,?,?)"
            " ON CONFLICT(address) DO UPDATE SET last_seen=excluded.last_seen, link=excluded.link,"
            " paired_with=excluded.paired_with",
            (addr, s["symbol"], s["name"], s["link"], ",".join(s["paired_with"]), now, now))

        def ev(t, detail):
            if store.add_event(con, addr, t, SEV[t], detail):
                fired.append((addr, s["symbol"], t, SEV[t], detail))

        # 1) pool ghép cổ phiếu mới
        for p in x["pools"]:
            if not p.get("pool"):
                continue
            seen = con.execute("SELECT 1 FROM pools WHERE pool=?", (p["pool"].lower(),)).fetchone()
            con.execute("INSERT OR IGNORE INTO pools(pool, token, stock, dex, first_seen, last_liq) VALUES(?,?,?,?,?,?)",
                        (p["pool"].lower(), addr, p.get("stock"), p.get("dex") or p.get("src"), now, p["liq"]))
            fresh = not p.get("created") or now - p["created"] <= rules["new_pool_max_age_h"] * 3600
            if (not seen and p.get("stock") and not first_run and fresh
                    and (p["liq"] or 0) >= c.MIN_STOCK_PAIR_LIQ):
                ev("NEW_STOCK_PAIRED_POOL", {"pool": p["pool"], "stock": p["stock"], "liq": round(p["liq"]),
                                             "age_h": round((now - p["created"]) / 3600, 1) if p.get("created") else None})

        # 2) token mới đạt ngưỡng
        if not known and s["liq_usd"] >= rules["min_liq_candidate"]:
            if not first_run or rank < rules["first_run_top_n"]:
                ev("NEW_CANDIDATE", {"score": s["score"], "liq": s["liq_usd"], "link": s["link"]})

        # 3) so với snapshot trước
        if prev:
            # ít pool hơn lần trước thường là do nguồn dữ liệu thiếu (API lỗi), không phải thanh khoản rút:
            # không so thanh khoản tổng trong trường hợp này để tránh LIQUIDITY_COLLAPSE giả
            pools_dropped = prev["n_pools"] is not None and s["n_pools"] < prev["n_pools"]
            if prev["liq"] and prev["liq"] >= rules["min_liq_candidate"] and not pools_dropped:
                d = 100 * (s["liq_usd"] / prev["liq"] - 1)
                if d <= -rules["liq_collapse_pct"]:
                    ev("LIQUIDITY_COLLAPSE", {"from": round(prev["liq"]), "to": s["liq_usd"], "pct": round(d, 1),
                                              "hours": round((now - prev["ts"]) / 3600, 1),
                                              "description": f"Thanh khoản giảm {abs(d):.0f}% trong "
                                                             f"{(now - prev['ts']) / 3600:.1f} giờ",
                                              "cause_hints": diagnose_collapse(prev, s)})
                elif d >= rules["liq_expansion_pct"]:
                    ev("LIQUIDITY_EXPANSION", {"from": round(prev["liq"]), "to": s["liq_usd"], "pct": round(d, 1)})
            if prev["buyers24"] and s["buyers24"] and 100 * (s["buyers24"] / prev["buyers24"] - 1) >= rules["participant_surge_pct"]:
                ev("PARTICIPANT_SURGE", {"buyers_from": prev["buyers24"], "buyers_to": s["buyers24"]})
        vol1 = s["vol1_usd"]          # tính trên pool đã gộp trùng (một pool có thể lọt 3 danh sách GeckoTerminal)
        if s["vol24_usd"] >= rules["vol_accel_min_vol24"] and vol1 / (s["vol24_usd"] / 24) >= rules["vol_accel_x"]:
            ev("VOLUME_ACCELERATION", {"vol1h": round(vol1), "avg_hour": round(s["vol24_usd"] / 24)})
        if any("honeypot" in f for f in s["flags"]):
            ev("HONEYPOT_PATTERN", {"buys24": s["buys24"], "sells24": s["sells24"]})

        store.add_snapshot(con, addr, {"liq": s["liq_usd"], "vol24": s["vol24_usd"], "vol1": vol1,
                                       "buys24": s["buys24"], "sells24": s["sells24"], "buyers24": s["buyers24"],
                                       "sellers24": s["sellers24"], "fdv": s["fdv_usd"], "score": s["score"],
                                       "main_liq": s.get("main_pool_liq"), "n_pools": s["n_pools"],
                                       "chg24": s.get("chg24_pct"), "sell_share": s.get("sell_share")})

    # stock token giả: pool có "cổ phiếu" trùng ticker nhưng sai địa chỉ
    for fk in discover.FAKE_PAIRS:
        tok = fk["token"]
        con.execute("INSERT INTO tokens(address, symbol, name, link, paired_with, first_seen, last_seen, status)"
                    " VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(address) DO UPDATE SET last_seen=excluded.last_seen",
                    (tok, fk["symbol"], "", "fake-stock", fk["claimed_stock"], now, now, "flagged"))
        if store.add_event(con, tok, "FAKE_STOCK_PAIR", SEV["FAKE_STOCK_PAIR"], fk):
            fired.append((tok, fk["symbol"], "FAKE_STOCK_PAIR", SEV["FAKE_STOCK_PAIR"], fk))

    # hàng đợi: event chưa xử lý, mức nghiêm trọng đủ, gộp theo token
    pending = con.execute(
        "SELECT e.token, t.symbol, MAX(e.severity) sev, GROUP_CONCAT(DISTINCT e.type) types FROM events e"
        " JOIN tokens t ON t.address=e.token WHERE e.handled=0 AND e.severity>=?"
        # cùng mức nghiêm trọng thì ưu tiên điểm định lượng mới nhất, không ưu tiên event ghi sau
        " GROUP BY e.token ORDER BY sev DESC,"
        " COALESCE((SELECT s.score FROM snapshots s WHERE s.token=e.token ORDER BY s.ts DESC LIMIT 1), 0) DESC,"
        " MAX(e.ts) DESC LIMIT ?",
        (rules["severity_to_queue"], max_queue)).fetchall()
    queue = [{"token": r["token"], "symbol": r["symbol"], "severity": r["sev"], "events": r["types"].split(",")}
             for r in pending]
    con.commit()
    c.save_cache("queue.json", {"generated": now, "queue": queue, "warnings": c.WARNINGS})

    print(f"Ứng viên liên quan cổ phiếu: {len(rows)} | Event mới: {len(fired)} | Hàng đợi điều tra: {len(queue)}")
    for addr, sym, t, sev, d in fired:
        print(f"- [{sev}] {t} {sym} {addr[:10]}… {json.dumps(d, ensure_ascii=False)[:160]}")
    if c.WARNINGS:
        print("Cảnh báo dữ liệu:", len(c.WARNINGS))
    return 10 if queue else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-queue", type=int, default=5)
    sys.exit(run(ap.parse_args().max_queue))


if __name__ == "__main__":
    main()
