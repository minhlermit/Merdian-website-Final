#!/usr/bin/env python3
"""MỘT LẦN CHẠY SCOUT → MỘT FILE HTML CHO NHÀ ĐẦU TƯ (tầng tất định, không gọi LLM).

Vòng đời của một token trong lần chạy:
    QUEUED ──(memo + scout-verdict hợp lệ)──► COMPLETE ──(plan)──► DEEP / BRIEF ──(investor memo hợp lệ)──► DONE
       └──────────────────────────────────────► INCOMPLETE / FAILED  (không bao giờ tới agent cuối)

    python3 run_report.py start [--tokens 0xA,0xB]        # tạo lần chạy từ queue.json (hoặc danh sách)
    python3 run_report.py complete --token 0xA --memo M.md  # cổng COMPLETE: kiểm memo, từ chối nếu thiếu
    python3 run_report.py fail --token 0xA --reason "..."   # điều tra dở dang
    python3 run_report.py plan [--deep 5]                  # khi mọi token đã xong: chọn ứng viên DEEP, còn lại BRIEF
    python3 run_report.py gate --token 0xA                 # agent cuối PHẢI gọi trước khi viết; mã 4 = không được chạy
    python3 run_report.py evidence --token 0xA             # gói bằng chứng đã có (DB), để agent cuối không điều tra lại
    python3 run_report.py check-investor --token 0xA       # kiểm + chuẩn hoá investor memo JSON
    python3 run_report.py render [--out FILE]              # HTML duy nhất của lần chạy
    python3 run_report.py status

Mọi lệnh nhận --run <id> (mặc định: lần chạy hiện tại). Chỉ dùng thư viện chuẩn Python 3.9+.
Mã thoát: 0 ổn | 1 dữ liệu không hợp lệ | 3 còn token chưa xong | 4 chặn ở cổng | 2 lỗi sử dụng.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import pathlib
import re
import shutil
import sys
import time
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "stock-token-scout" / "scripts"))
import render_report as rr  # noqa: E402
import common as c  # noqa: E402
import store  # noqa: E402
import ledger  # noqa: E402

SCHEMA = 1
CHAIN = "Robinhood Chain (4663)"
ADDR = re.compile(r"^0x[0-9a-f]{40}$")
RESEARCH_TERMINAL = {"COMPLETE", "INCOMPLETE", "FAILED"}
REQUIRED_SECTIONS = ["Kết luận nhanh", "Cấu trúc thị trường", "Cờ rủi ro", "Đánh giá tiềm năng"]
SHORT_MEMO_SECTIONS = ["Đánh giá tiềm năng"]          # memo ngắn cho stock token giả
DEFAULT_DEEP = 5

CONVICTION = {
    "CONTINUE_RESEARCH": ("TIẾP TỤC NGHIÊN CỨU", "Có đủ cơ sở để bỏ thêm thời gian nghiên cứu."),
    "MONITOR": ("CHỈ THEO DÕI", "Chưa đủ cơ sở; chỉ xem lại khi có điều kiện ở mục 'điều làm thesis thay đổi'."),
    "DROP": ("DỪNG NGHIÊN CỨU", "Không có luận điểm đáng theo đuổi, hoặc rủi ro quá lớn."),
}
GROWTH = {
    "SUSTAINABLE": "Có vòng tăng trưởng bền vững",
    "FRAGILE": "Có tăng trưởng nhưng mong manh",
    "NONE": "Không có luận điểm tăng trưởng bền vững",
    "UNKNOWN": "Chưa đủ bằng chứng",
}
GROWTH_SHORT = {"SUSTAINABLE": "Bền vững", "FRAGILE": "Mong manh", "NONE": "Không có", "UNKNOWN": "Chưa rõ"}
RISK_LEVELS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
RISK_LABEL = {"LOW": "Thấp", "MEDIUM": "Trung bình", "HIGH": "Cao", "CRITICAL": "Nghiêm trọng"}
DEMAND = {"YES": "Có", "PARTIAL": "Một phần", "NO": "Không", "UNKNOWN": "Chưa rõ"}
MOAT = {"NONE": "Không có", "NETWORK_EFFECT": "Hiệu ứng mạng", "DISTRIBUTION": "Lợi thế phân phối",
        "TECHNOLOGY": "Công nghệ", "BRAND": "Thương hiệu/cộng đồng", "OTHER": "Khác", "UNKNOWN": "Chưa rõ"}

DEEP_FIELDS = ["project_thesis", "problem", "product", "technology", "creator_identity", "creator_commentary",
               "user_acquisition", "retention", "monetization", "token_value_capture", "growth_engine", "traction",
               "moat", "liquidity_exit_risk", "stock_pair_analysis", "catalysts", "invalidation_conditions",
               "evidence_confidence", "conviction", "conviction_memo"]
BRIEF_FIELDS = ["project_thesis", "growth_engine", "conviction", "conviction_memo"]
# lời khuyên giao dịch: bị từ chối ở cổng kiểm, không chỉ cảnh báo
BANNED = re.compile(r"(nên mua|nên bán|mua vào|bán ra|vào lệnh|chốt lời|cắt lỗ|mục tiêu giá|giá mục tiêu|price target|"
                    r"\bx10\b|\bx100\b|\b100x\b|to the moon|\bgem\b|buy now|strong buy)", re.I)


# ---------------------------------------------------------------- đường dẫn và lần chạy

def cache_dir() -> pathlib.Path:
    return pathlib.Path(c.CACHE_DIR)


def reports_dir() -> pathlib.Path:
    d = pathlib.Path(os.getenv("STS_REPORT_DIR") or cache_dir() / "reports").expanduser()
    d.mkdir(parents=True, exist_ok=True)
    return d


def runs_dir() -> pathlib.Path:
    d = cache_dir() / "runs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def current_run_id() -> str | None:
    p = runs_dir() / "current"
    return p.read_text().strip() if p.is_file() else None


def run_path(run_id: str) -> pathlib.Path:
    if not re.match(r"^[0-9A-Za-z_-]{1,40}$", run_id or ""):
        raise SystemExit(f"run id không hợp lệ: {run_id!r}")
    return runs_dir() / run_id


def load_manifest(run_id: str) -> dict:
    p = run_path(run_id) / "manifest.json"
    if not p.is_file():
        raise SystemExit(f"Không thấy lần chạy {run_id}. Chạy `run_report.py start` trước.")
    return json.loads(p.read_text(encoding="utf-8"))


def save_manifest(m: dict):
    d = run_path(m["run_id"])
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "manifest.json.tmp"
    tmp.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(d / "manifest.json")


def norm_addr(a: str) -> str:
    a = (a or "").strip().lower()
    if not ADDR.match(a):
        raise SystemExit(f"Địa chỉ không hợp lệ: {a!r}")
    return a


def token_entry(m: dict, token: str) -> dict:
    t = m["tokens"].get(norm_addr(token))
    if not t:
        raise SystemExit(f"Token {token} không thuộc lần chạy {m['run_id']}.")
    return t


def investor_file(m: dict, token: str) -> pathlib.Path:
    return run_path(m["run_id"]) / "investor" / f"{token}.json"


def out(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=1))


# ---------------------------------------------------------------- dữ kiện tất định từ DB

def db():
    return store.connect()


def onchain_fact(con, token: str) -> tuple[dict, float | None]:
    fact, ts = store.latest_fact(con, token, "onchain")
    return (fact or {}), ts


def metrics(con, token: str) -> dict:
    """Số liệu chính + mức rủi ro thoát hàng tối thiểu do luật tính (agent chỉ được nâng, không được hạ)."""
    f, ts = onchain_fact(con, token)
    mk, h = f.get("market") or {}, f.get("holders") or {}
    now = time.time()
    snaps = con.execute("SELECT ts, liq FROM snapshots WHERE token=? AND ts>=? ORDER BY ts",
                        (token, now - 7 * 86400)).fetchall()
    peak = max((r["liq"] or 0 for r in snaps), default=0)
    last = snaps[-1]["liq"] if snaps else None
    drawdown = round(100 * (1 - last / peak), 1) if peak and last is not None else None
    collapses = con.execute("SELECT COUNT(*) n FROM events WHERE token=? AND type='LIQUIDITY_COLLAPSE' AND ts>=?",
                            (token, now - 7 * 86400)).fetchone()["n"]
    liq = mk.get("liq_total_usd")
    m = {
        "liq": liq, "vol24": mk.get("vol24_total_usd"), "turnover": mk.get("turnover24"),
        "fdv_to_liq": mk.get("fdv_to_liq"), "sell_share": mk.get("sell_share"), "avg_trade": mk.get("avg_trade_usd"),
        "age_days": mk.get("age_days"), "main_pool_share": mk.get("vol_share_main_pool_pct"),
        "holders": h.get("holders_count"), "top10_eoa": h.get("top10_eoa_pct"), "largest_eoa": h.get("largest_eoa_pct"),
        "top10_all": h.get("top10_all_pct"), "holders_source": h.get("source") or "blockscout",
        "holder_growth": f.get("holder_growth"), "liq_peak_7d": round(peak) if peak else None,
        "liq_drawdown_7d_pct": drawdown, "collapse_events_7d": collapses,
        "price_drawdown_7d_pct": (f.get("history_7d") or {}).get("max_drawdown_pct"),
        "fact_age_h": round((now - ts) / 3600, 1) if ts else None,
    }
    level, why = "LOW", []

    def bump(lv, reason):
        nonlocal level
        if RISK_LEVELS.index(lv) > RISK_LEVELS.index(level):
            level = lv
        why.append(reason)

    if collapses:
        bump("CRITICAL", f"{collapses} sự kiện thanh khoản sụt mạnh trong 7 ngày")
    if drawdown is not None and drawdown >= 50:
        bump("CRITICAL", f"thanh khoản giảm {drawdown}% so với đỉnh 7 ngày")
    elif drawdown is not None and drawdown >= 25:
        bump("MEDIUM", f"thanh khoản giảm {drawdown}% so với đỉnh 7 ngày")
    pdd = m["price_drawdown_7d_pct"]
    if isinstance(pdd, (int, float)) and pdd <= -75:
        bump("HIGH", f"giá từng giảm {abs(pdd)}% trong 7 ngày: người bán sau không có ai đỡ")
    elif isinstance(pdd, (int, float)) and pdd <= -50:
        bump("MEDIUM", f"giá từng giảm {abs(pdd)}% trong 7 ngày")
    if isinstance(liq, (int, float)):
        if liq < 20000:
            bump("HIGH", f"thanh khoản chỉ ${liq:,.0f}: một lệnh vài trăm USD đã làm lệch giá")
        elif liq < 250000:
            bump("MEDIUM", f"thanh khoản ${liq:,.0f}, chưa đủ sâu cho lệnh lớn")
    else:
        bump("MEDIUM", "không có số liệu thanh khoản")
    if (m["fdv_to_liq"] or 0) > 50:
        bump("HIGH", f"FDV gấp {m['fdv_to_liq']} lần thanh khoản")
    if (m["top10_eoa"] or 0) > 50:
        bump("HIGH", f"10 ví thường lớn nhất giữ {m['top10_eoa']}%")
    elif m["top10_eoa"] is None and (m["top10_all"] or 0) > 50:
        bump("MEDIUM", f"top 10 địa chỉ (gồm cả pool/hợp đồng) giữ {m['top10_all']}%; chưa tách được ví thường")
    if m["top10_eoa"] is None:
        why.append("chưa đo được mức tập trung ở ví thường (thiếu dữ liệu holder chi tiết)")
    if (m["largest_eoa"] or 0) > 5:
        bump("HIGH", f"một ví thường giữ {m['largest_eoa']}%")
    if (m["main_pool_share"] or 0) > 90:
        bump("MEDIUM", f"{m['main_pool_share']}% volume nằm ở một pool")
    m["exit_risk_floor"], m["exit_risk_reasons"] = level, why
    return m


def ticker_collisions(con, token: str, symbol: str | None) -> int:
    if not symbol:
        return 0
    return con.execute("SELECT COUNT(DISTINCT address) n FROM tokens WHERE UPPER(symbol)=? AND address<>?",
                       (symbol.upper(), token)).fetchone()["n"]


def evidence_pack(con, token: str) -> dict:
    """Mọi thứ các agent trước đã thu thập, gọn lại. Agent cuối đọc gói này + memo, không gọi mạng."""
    f, ts = onchain_fact(con, token)
    pools = [{k: p.get(k) for k in ("dex", "counter", "stock", "liq_usd", "vol24", "buyers24", "sellers24", "url")}
             for p in (f.get("pools") or [])[:4]]
    claims = [dict(r) for r in con.execute(
        "SELECT claim, ctype, arg, source_url, status, detail FROM claims WHERE token=? ORDER BY ts", (token,))]
    events = [dict(r) for r in con.execute(
        "SELECT ts, type, severity, detail FROM events WHERE token=? ORDER BY ts DESC LIMIT 15", (token,))]
    ev = [dict(r) for r in con.execute(
        "SELECT url, source, category, author, posted_at, substr(text,1,300) AS text FROM evidence "
        "WHERE token=? ORDER BY first_seen DESC LIMIT 25", (token,))]
    return {
        "token": token, "name": f.get("name"), "symbol": f.get("symbol"),
        "fact_generated_utc": f.get("generated_utc"), "profile": f.get("profile"), "market": f.get("market"),
        "holders": f.get("holders"), "holder_growth": f.get("holder_growth"), "deployer": f.get("deployer"),
        "contract": f.get("contract"), "stock_pair": f.get("stock_pair"), "pools": pools,
        "suspected_fake_stock_pairs": f.get("suspected_fake_stock_pairs"), "history_7d": f.get("history_7d"),
        "supply_flows": f.get("supply_flows"), "claims": claims, "identity": ledger.attribution_table(con, token),
        "events": events, "evidence_items": ev, "metrics": metrics(con, token),
        "api_warnings": (f.get("warnings") or [])[:10],
    }


# ---------------------------------------------------------------- logo và link (tất định, có cache)

def _safe_url(u) -> str | None:
    u = str(u or "").strip()
    return u if re.match(r"^https?://[^\s\"'<>]+$", u, re.I) else None


def x_url(x) -> str | None:
    x = str(x or "").strip()
    if not x:
        return None
    if re.match(r"^https?://(www\.)?(x|twitter)\.com/", x, re.I):
        return _safe_url(x)
    handle = x.lstrip("@")
    return f"https://x.com/{handle}" if re.match(r"^[A-Za-z0-9_]{1,15}$", handle) else None


def links(fact: dict) -> dict:
    p = fact.get("profile") or {}
    sites = [u for u in (_safe_url(w) for w in (p.get("websites") or [])) if u][:2]
    tg = str(p.get("telegram") or "").lstrip("@")
    return {"x": x_url(p.get("x")), "websites": sites,
            "telegram": f"https://t.me/{tg}" if re.match(r"^[A-Za-z0-9_]{3,32}$", tg) else None}


def monogram(symbol: str, token: str) -> str:
    hue = int(hashlib.sha256(token.encode()).hexdigest()[:4], 16) % 360
    letters = rr.esc((re.sub(r"[^A-Za-z0-9]", "", symbol or "") or "?")[:2].upper())
    return (f"<span class='logo mono' style='background:hsl({hue} 55% 45%)' aria-hidden='true'>{letters}</span>")


def logo_html(token: str, fact: dict) -> str:
    """Logo tải một lần rồi cache dạng data URI. STS_OFFLINE=1 thì chỉ dùng cache hoặc chữ cái."""
    sym = fact.get("symbol") or ""
    d = cache_dir() / "logos"
    d.mkdir(parents=True, exist_ok=True)
    hit, miss = d / f"{token}.txt", d / f"{token}.none"
    if hit.is_file():
        return f"<img class='logo' alt='' src='{rr.esc(hit.read_text())}'>"
    if miss.is_file() and time.time() - miss.stat().st_mtime < 7 * 86400:
        return monogram(sym, token)
    if os.getenv("STS_OFFLINE"):
        return monogram(sym, token)
    src = _safe_url((fact.get("profile") or {}).get("image_url"))
    try:
        if not src:
            src = _safe_url(c.gt_token_info(token).get("image_url"))
        if src:
            req = urllib.request.Request(src, headers={"User-Agent": "stock-token-scout"})
            with urllib.request.urlopen(req, timeout=10) as r:
                ctype = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
                data = r.read(300_001)
            if ctype in ("image/png", "image/jpeg", "image/webp", "image/gif") and len(data) <= 300_000:
                uri = f"data:{ctype};base64," + base64.b64encode(data).decode()
                hit.write_text(uri)
                return f"<img class='logo' alt='' src='{rr.esc(uri)}'>"
    except Exception:  # logo là phần phụ: lỗi mạng không được làm hỏng báo cáo
        pass
    miss.write_text(str(time.time()))
    return monogram(sym, token)


def pair_label(fact: dict) -> tuple[str, str]:
    """(nhãn cặp, loại): 'stock' = ghép stock token chính chủ, 'fake' = nghi stock token giả, 'none' = không ghép cổ phiếu."""
    pools = fact.get("pools") or []
    main = next((p for p in pools if p.get("stock")), pools[0] if pools else None)
    if not main:
        return "chưa rõ", "none"
    sym = fact.get("symbol") or "?"
    if fact.get("suspected_fake_stock_pairs"):
        return f"{sym}/{fact['suspected_fake_stock_pairs'][0].get('claimed_stock') or '?'}", "fake"
    return f"{sym}/{main.get('counter') or '?'}", "stock" if main.get("stock") else "none"


# ---------------------------------------------------------------- investor memo: kiểm và chuẩn hoá

def _blank(v) -> bool:
    if v is None:
        return True
    if isinstance(v, str):
        return not v.strip()
    if isinstance(v, dict):
        return all(_blank(x) for x in v.values()) if v else True
    return False


def _texts(v):
    if isinstance(v, str):
        yield v
    elif isinstance(v, dict):
        for x in v.values():
            yield from _texts(x)
    elif isinstance(v, list):
        for x in v:
            yield from _texts(x)


def normalize_investor(memo: dict, mode: str, potential: dict, m: dict) -> dict:
    """Áp luật lên investor memo. Trả về bản chuẩn hoá + errors (chặn) + notes (đã điều chỉnh)."""
    errors, notes = [], []
    if memo.get("schema") != SCHEMA:
        errors.append(f"schema phải là {SCHEMA}")
    for k in (DEEP_FIELDS if mode == "DEEP" else BRIEF_FIELDS):
        if k in ("creator_commentary", "traction", "catalysts") and isinstance(memo.get(k), list):
            continue                                   # danh sách rỗng hợp lệ: "không có" là một câu trả lời
        if _blank(memo.get(k)):
            errors.append(f"thiếu '{k}' (không có bằng chứng thì ghi rõ điều đó, không bỏ trống)")
    if mode == "DEEP" and not [x for x in memo.get("invalidation_conditions") or [] if str(x).strip()]:
        errors.append("DEEP cần ít nhất một điều kiện làm thesis mất hiệu lực")
    bad = sorted({mt.group(0) for t in _texts(memo) for mt in BANNED.finditer(t)})
    if bad:
        errors.append("có ngôn ngữ khuyến nghị giao dịch: " + ", ".join(bad))

    g = memo.get("growth_engine") if isinstance(memo.get("growth_engine"), dict) else {}
    gv = str(g.get("verdict", "UNKNOWN")).upper()
    gv = gv if gv in GROWTH else "UNKNOWN"
    tvc = memo.get("token_value_capture") if isinstance(memo.get("token_value_capture"), dict) else {}
    demand = str(tvc.get("product_growth_drives_token_demand", "UNKNOWN")).upper()
    demand = demand if demand in DEMAND else "UNKNOWN"
    if gv == "SUSTAINABLE" and (demand not in ("YES", "PARTIAL") or g.get("depends_on_new_buyers") is not False):
        gv = "FRAGILE"
        notes.append("Hạ 'bền vững' xuống 'mong manh': tăng trưởng sản phẩm chưa chứng minh tạo cầu token, "
                     "hoặc vòng tăng trưởng vẫn dựa vào người mua mới.")

    conv = str(memo.get("conviction", "")).upper()
    conv = conv if conv in CONVICTION else "MONITOR"
    pv = potential.get("verdict", "UNRATED")
    cap = None
    if pv == "AVOID":
        cap, why = "DROP", "token bị chấm TRÁNH XA"
    elif gv == "NONE":
        cap, why = "MONITOR", "không có luận điểm tăng trưởng bền vững"
    elif pv in ("SPECULATIVE", "UNRATED"):
        cap, why = "MONITOR", f"đánh giá tiềm năng là {rr.VERDICTS[pv][0]}"
    order = ["DROP", "MONITOR", "CONTINUE_RESEARCH"]
    if cap and order.index(conv) > order.index(cap):
        notes.append(f"Kết luận hạ từ {CONVICTION[conv][0]} xuống {CONVICTION[cap][0]} vì {why}.")
        conv = cap

    lr = memo.get("liquidity_exit_risk") if isinstance(memo.get("liquidity_exit_risk"), dict) else {}
    lv = str(lr.get("level", "LOW")).upper()
    lv = lv if lv in RISK_LEVELS else "LOW"
    floor = m.get("exit_risk_floor", "LOW")
    if RISK_LEVELS.index(floor) > RISK_LEVELS.index(lv):
        notes.append(f"Rủi ro thoát hàng nâng từ {RISK_LABEL[lv]} lên {RISK_LABEL[floor]} theo số liệu on-chain.")
        lv = floor

    conf = str(memo.get("evidence_confidence", "LOW")).upper()
    conf = conf if conf in rr.CONF_RANK else "LOW"
    pc = potential.get("confidence", "LOW")
    if rr.CONF_RANK[conf] > rr.CONF_RANK[pc]:
        notes.append(f"Độ tin cậy bằng chứng giới hạn ở {rr.CONF_LABEL[pc]} như phần chấm điểm.")
        conf = pc

    moat = memo.get("moat") if isinstance(memo.get("moat"), dict) else {}
    mt = str(moat.get("type", "UNKNOWN")).upper()
    norm = dict(memo)
    norm.update({"growth_verdict": gv, "demand": demand, "conviction": conv, "exit_level": lv,
                 "evidence_confidence": conf, "moat_type": mt if mt in MOAT else "OTHER", "mode": mode})
    return {"memo": norm, "errors": errors, "notes": notes}


# ---------------------------------------------------------------- lệnh

def cmd_start(a):
    if a.tokens:
        raw = [{"token": t} for t in a.tokens.split(",") if t.strip()]
    else:
        raw = (c.load_cache("queue.json") or {}).get("queue") or []
    if not raw:
        print("Không có token nào để tạo lần chạy (queue.json rỗng).", file=sys.stderr)
        return 2
    run_id = a.run or time.strftime("%Y%m%d_%H%M", time.gmtime())
    if (run_path(run_id) / "manifest.json").is_file():
        run_id += "_" + hashlib.sha1(str(time.time()).encode()).hexdigest()[:4]
    toks = {}
    for q in raw:
        t = norm_addr(q["token"])
        toks.setdefault(t, {"ticker": q.get("symbol") or "", "research_status": "QUEUED", "memo": None,
                            "reasons": [], "mode": None, "investor_status": "PENDING", "investor_notes": [],
                            "events": q.get("events") or [], "updated": time.time()})
    m = {"run_id": run_id, "created": time.time(), "tokens": toks, "plan": None, "rendered": None}
    save_manifest(m)
    (runs_dir() / "current").write_text(run_id)
    out({"run_id": run_id, "tokens": list(toks), "deduplicated": len(raw) - len(toks)})
    return 0


def cmd_complete(a, m):
    t = norm_addr(a.token)
    e = token_entry(m, t)
    p = pathlib.Path(a.memo).expanduser()
    reasons = []
    if not p.is_file():
        reasons.append(f"không thấy memo {p}")
    else:
        it = rr.parse_memo(p)
        text = p.read_text(encoding="utf-8", errors="replace")
        reasons += it["errors"]
        short = "FAKE_STOCK_PAIR" in it["hard_flags"]
        for s in (SHORT_MEMO_SECTIONS if short else REQUIRED_SECTIONS):
            if not re.search(r"^##\s*" + re.escape(s), text, re.M):
                reasons.append(f"memo thiếu mục '## {s}'")
        if it["token"] and ADDR.match(it["token"]) and it["token"] != t:
            reasons.append(f"memo nói về token khác ({it['token']})")
        if not e["ticker"]:
            e["ticker"] = it["ticker"]
    e.update({"memo": str(p), "reasons": reasons, "updated": time.time(),
              "research_status": "INCOMPLETE" if reasons else "COMPLETE"})
    save_manifest(m)
    out({"token": t, "research_status": e["research_status"], "reasons": reasons})
    return 1 if reasons else 0


def cmd_fail(a, m):
    e = token_entry(m, a.token)
    e.update({"research_status": "FAILED", "reasons": [a.reason], "updated": time.time()})
    save_manifest(m)
    out({"token": norm_addr(a.token), "research_status": "FAILED"})
    return 0


def _potential(e: dict) -> dict:
    if e.get("memo") and pathlib.Path(e["memo"]).is_file():
        return rr.parse_memo(pathlib.Path(e["memo"]))
    return {"verdict": "UNRATED", "pct": 0.0, "total": 0, "max": 0, "confidence": "LOW", "hard_flags": [],
            "scores": {k: None for k in rr.DIM_KEYS}, "notes": [], "errors": [], "one_liner": "", "memo_rating": ""}


def cmd_plan(a, m):
    pending = [t for t, e in m["tokens"].items() if e["research_status"] not in RESEARCH_TERMINAL]
    if pending:
        out({"error": "Còn token chưa nghiên cứu xong; agent cuối chưa được chạy.", "pending": pending})
        return 3
    n = max(1, min(10, a.deep or int(os.getenv("STS_DEEP_N") or DEFAULT_DEEP)))
    con = db()
    rank = []
    for t, e in m["tokens"].items():
        if e["research_status"] != "COMPLETE":
            continue
        pot = _potential(e)
        liq = metrics(con, t)["liq"] or 0
        rank.append((rr.DISPLAY_ORDER.index(pot["verdict"]), -pot["pct"], -liq, t))
    rank.sort()
    deep = [t for (vi, _, _, t) in rank if rr.DISPLAY_ORDER[vi] not in ("AVOID", "UNRATED")][:n]
    order = [t for (_, _, _, t) in rank]
    for t in order:
        m["tokens"][t]["mode"] = "DEEP" if t in deep else "BRIEF"
    m["plan"] = {"at": time.time(), "deep_n": n, "order": order}
    save_manifest(m)
    out([{"token": t, "ticker": m["tokens"][t]["ticker"], "mode": m["tokens"][t]["mode"],
          "memo": m["tokens"][t]["memo"], "output": str(investor_file(m, t))} for t in order])
    return 0


def cmd_gate(a, m):
    t = norm_addr(a.token)
    e = token_entry(m, t)
    if e["research_status"] != "COMPLETE":
        out({"allowed": False, "why": f"research_status = {e['research_status']}; agent cuối chỉ chạy khi COMPLETE",
             "reasons": e["reasons"]})
        return 4
    if not m.get("plan") or not e.get("mode"):
        out({"allowed": False, "why": "chưa có plan: chạy `run_report.py plan` sau khi mọi token đã xong"})
        return 4
    out({"allowed": True, "token": t, "ticker": e["ticker"], "mode": e["mode"], "memo": e["memo"],
         "evidence_cmd": f"python3 {HERE / 'run_report.py'} --run {m['run_id']} evidence --token {t}",
         "output": str(investor_file(m, t)), "check_cmd": f"python3 {HERE / 'run_report.py'} --run {m['run_id']} check-investor --token {t}"})
    return 0


def cmd_evidence(a, m):
    t = norm_addr(a.token)
    token_entry(m, t)
    out(evidence_pack(db(), t))
    return 0


def cmd_check_investor(a, m):
    t = norm_addr(a.token)
    e = token_entry(m, t)
    if e["research_status"] != "COMPLETE" or not e.get("mode"):
        out({"ok": False, "why": "token chưa COMPLETE hoặc chưa có plan"})
        return 4
    p = pathlib.Path(a.file).expanduser() if a.file else investor_file(m, t)
    try:
        memo = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(memo, dict):
            raise ValueError("phải là object JSON")
    except (OSError, ValueError) as ex:
        out({"ok": False, "errors": [f"không đọc được {p}: {ex}"]})
        return 1
    res = normalize_investor(memo, e["mode"], _potential(e), metrics(db(), t))
    if a.file:
        investor_file(m, t).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, investor_file(m, t))
    e["investor_status"] = "INVALID" if res["errors"] else "DONE"
    e["investor_notes"] = res["notes"]
    save_manifest(m)
    nm = res["memo"]
    out({"ok": not res["errors"], "errors": res["errors"], "notes": res["notes"], "mode": e["mode"],
         "conviction": CONVICTION[nm["conviction"]][0], "growth": GROWTH[nm["growth_verdict"]],
         "exit_risk": RISK_LABEL[nm["exit_level"]]})
    return 1 if res["errors"] else 0


def cmd_status(a, m):
    out({"run_id": m["run_id"], "planned": bool(m.get("plan")),
         "tokens": {t: {k: e.get(k) for k in ("ticker", "research_status", "mode", "investor_status", "reasons")}
                    for t, e in m["tokens"].items()}})
    return 0


# ---------------------------------------------------------------- HTML

CSS_EXTRA = """
.dq{margin:12px 0;padding:10px 14px;border:1px solid var(--line,#ddd);border-radius:10px}
.dq summary{cursor:pointer}
.dq ul{margin:8px 0 0}
.wrap{max-width:1180px}.logo{width:40px;height:40px;border-radius:50%;object-fit:cover;flex:none;background:var(--bar)}
.mono{display:inline-flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:14px}
.ident{display:flex;gap:12px;align-items:center}.tbl{overflow-x:auto;border:1px solid var(--line);border-radius:12px;background:var(--card)}
.tbl table{min-width:900px}.tbl th{text-align:left;font-size:12px;color:var(--muted);font-weight:600;padding:10px 8px;border-bottom:1px solid var(--line)}
.tbl td{padding:8px}.tbl .logo{width:26px;height:26px;font-size:11px}.num{text-align:right;font-variant-numeric:tabular-nums}
.pill{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;border:1px solid var(--line);white-space:nowrap}
.c-CONTINUE_RESEARCH{border-color:var(--g);color:var(--g)}.c-MONITOR{border-color:var(--y);color:var(--y)}.c-DROP{border-color:var(--r);color:var(--r)}
.r-LOW{color:var(--g)}.r-MEDIUM{color:var(--y)}.r-HIGH{color:var(--o)}.r-CRITICAL{color:var(--r);font-weight:700}
.g-SUSTAINABLE{color:var(--g)}.g-FRAGILE{color:var(--y)}.g-NONE{color:var(--r)}.g-UNKNOWN{color:var(--muted)}
.meta{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:13px;color:var(--muted);margin-top:4px}
.sec{border-top:1px solid var(--line);padding-top:10px;margin-top:12px}.sec h4{margin:0 0 4px}
.conv{border-left:4px solid var(--accent);padding:10px 14px;background:var(--bg);border-radius:6px;margin-top:14px}
.tech{margin-top:14px;border:1px dashed var(--line);border-radius:8px;padding:8px 12px}.tech pre{white-space:pre-wrap;word-break:break-all;font-size:12px}
.badge.sm{font-size:11px;padding:2px 8px;white-space:nowrap}.brief{opacity:.97}.nw{white-space:nowrap}.warn{color:var(--o)}.top-cands{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:10px;margin:14px 0}
.cand{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px}.cand a{text-decoration:none;color:inherit}
"""


def _fmt_usd(x) -> str:
    return f"${x:,.0f}" if isinstance(x, (int, float)) else "–"


def _fmt(x, suffix="") -> str:
    if x is None:
        return "–"
    if isinstance(x, bool):
        return str(x)
    if isinstance(x, int):
        return f"{x:,}{suffix}"
    if isinstance(x, float):
        return f"{x:,.1f}{suffix}" if abs(x) >= 1 else f"{x:.3g}{suffix}"
    return f"{x}{suffix}"


def _p(v) -> str:
    if _blank(v):
        return "<p class='muted'>Không có bằng chứng trong dữ liệu đã thu thập.</p>"
    return f"<p>{rr.esc(v)}</p>"


def _list(xs) -> str:
    xs = [x for x in (xs or []) if not _blank(x)]
    if not xs:
        return "<p class='muted'>Không có.</p>"
    items = []
    for x in xs:
        if isinstance(x, dict):
            body = " · ".join(rr.esc(v) for k, v in x.items() if k not in ("evidence", "source") and not _blank(v))
            ev = x.get("evidence")
            src = _safe_url(x.get("source"))
            tail = (f" <span class='ev ev-{rr.esc(ev)}'>{rr.esc(rr.EVIDENCE.get(str(ev), ev))}</span>" if ev else "")
            tail += f" <a href='{rr.esc(src)}' rel='noopener noreferrer'>nguồn</a>" if src else ""
            items.append(f"<li>{body}{tail}</li>")
        else:
            items.append(f"<li>{rr.esc(x)}</li>")
    return "<ul>" + "".join(items) + "</ul>"


def _sec(title: str, body: str) -> str:
    return f"<div class='sec'><h4>{rr.esc(title)}</h4>{body}</div>"


def build_items(m: dict) -> list:
    con = db()
    items = []
    for t, e in m["tokens"].items():
        fact, _ = onchain_fact(con, t)
        pot = _potential(e)
        mt = metrics(con, t)
        inv, inv_notes, inv_errors = None, list(e.get("investor_notes") or []), []
        f = investor_file(m, t)
        if e["research_status"] == "COMPLETE" and e.get("mode") and f.is_file():
            try:
                res = normalize_investor(json.loads(f.read_text(encoding="utf-8")), e["mode"], pot, mt)
                inv, inv_notes, inv_errors = res["memo"], res["notes"], res["errors"]
            except (OSError, ValueError) as ex:
                inv_errors = [f"investor memo hỏng: {ex}"]
        sym = fact.get("symbol") or e.get("ticker") or pot.get("ticker") or f"{t[:6]}…{t[-4:]}"
        pair, official = pair_label(fact)
        items.append({"token": t, "e": e, "fact": fact, "pot": pot, "m": mt, "inv": inv,
                      "inv_notes": inv_notes, "inv_errors": inv_errors, "symbol": sym,
                      "name": fact.get("name") or pot.get("name") or "", "pair": pair, "official": official,
                      "links": links(fact), "logo": logo_html(t, fact),
                      "collisions": ticker_collisions(con, t, sym)})
    order = (m.get("plan") or {}).get("order") or []
    rank = {t: i for i, t in enumerate(order)}
    mode_rank = {"DEEP": 0, "BRIEF": 1, None: 2}
    items.sort(key=lambda i: (mode_rank.get(i["e"].get("mode"), 2), rank.get(i["token"], 999), i["symbol"]))
    return items


def top10_cell(mt: dict) -> str:
    if mt["top10_eoa"] is not None:
        return _fmt(mt["top10_eoa"], "%")
    if mt["top10_all"] is not None:
        return _fmt(mt["top10_all"], "%*")
    return "–"


FAKE_MARK = " <span class='warn' title='Nghi stock token giả'>⚠</span>"
PAIR_NOTE = {"stock": " (stock token chính chủ)", "fake": " ⚠ nghi stock token giả, không nằm trong danh sách trắng",
             "none": " (không ghép cổ phiếu)"}


def _clip(text: str, n: int) -> str:
    text = str(text or "")
    if len(text) <= n:
        return text
    cut = text[:n].rsplit(" ", 1)[0].rstrip(",;:.")
    return cut + "…"


def conv_pill(conv) -> str:
    return f"<span class='pill c-{conv}'>{rr.esc(CONVICTION[conv][0])}</span>" if conv in CONVICTION else "–"


def dash_row(n: int, i: dict) -> str:
    pot, mt, inv, e = i["pot"], i["m"], i["inv"], i["e"]
    v = pot["verdict"]
    conv = inv["conviction"] if inv else None
    gv = inv["growth_verdict"] if inv else None
    lv = inv["exit_level"] if inv else mt["exit_risk_floor"]
    status = {"COMPLETE": "Hoàn tất", "INCOMPLETE": "Chưa đủ", "FAILED": "Lỗi", "QUEUED": "Đang chờ"}[e["research_status"]]
    score = f"{pot['total']}/{pot['max']}" if pot.get("max") else "–"
    return (f"<tr><td class='num'>{n}</td><td><a class='ident' href='#t-{i['token']}'>{i['logo']}<span><b>{rr.esc(i['symbol'])}</b>"
            f"<br><span class='muted'>{rr.esc(i['name'][:28])}</span></span></a></td>"
            f"<td class='nw'>{rr.esc(i['pair'])}{FAKE_MARK if i['official'] == 'fake' else ''}</td>"
            f"<td class='num'>{_fmt_usd(mt['liq'])}</td><td class='num'>{_fmt_usd(mt['vol24'])}</td>"
            f"<td class='num'>{_fmt(mt['holders'])}</td><td class='num'>{top10_cell(mt)}</td>"
            f"<td><span class='badge sm v-{v}'>{rr.VERDICTS[v][1]} {rr.esc(rr.VERDICTS[v][0])}</span><br><span class='muted'>{score}</span></td>"
            f"<td class='g-{gv or 'UNKNOWN'} nw' title='{rr.esc(GROWTH[gv]) if gv else ''}'>{rr.esc(GROWTH_SHORT[gv]) if gv else '–'}</td>"
            f"<td class='r-{lv} nw'>{rr.esc(RISK_LABEL[lv])}</td>"
            f"<td>{conv_pill(conv)}<br><span class='muted nw'>{status}{' · ' + e['mode'] if e.get('mode') else ''}</span></td></tr>")


def tech_evidence(i: dict) -> str:
    f, e, pot = i["fact"], i["e"], i["pot"]
    con = db()
    claims = con.execute("SELECT ctype, arg, status, detail, source_url FROM claims WHERE token=? ORDER BY ts",
                         (i["token"],)).fetchall()
    ident = ledger.attribution_table(con, i["token"])
    ctr = f.get("contract") or {}
    dep = f.get("deployer") or {}
    pools = "".join(
        f"<tr><td>{rr.esc(p.get('dex'))}</td><td>{rr.esc(p.get('counter'))}{' ✓' if p.get('stock') else ''}</td>"
        f"<td class='num'>{_fmt_usd(p.get('liq_usd'))}</td><td class='num'>{_fmt_usd(p.get('vol24'))}</td>"
        f"<td style='word-break:break-all'>{rr.esc(p.get('pool'))}</td></tr>" for p in (f.get("pools") or [])[:8])
    cl = "".join(f"<tr><td>{rr.esc(r['ctype'])}</td><td>{rr.esc(r['arg'])}</td><td><span class='ev ev-{rr.esc(r['status'])}'>"
                 f"{rr.esc(r['status'])}</span></td><td>{rr.esc(r['detail'])}</td></tr>" for r in claims)
    idt = "".join(f"<tr><td>{rr.esc(x['subject'])}</td><td>{rr.esc(x['entity'])}</td><td>{rr.esc(x['level'])}</td>"
                  f"<td>{rr.esc(x['reason'])}</td></tr>" for x in ident)
    warns = "".join(f"<li>{rr.esc(w)}</li>" for w in (f.get("warnings") or [])[:15])
    notes = "".join(f"<li>{rr.esc(n)}</li>" for n in (pot.get("notes") or []) + (pot.get("errors") or [])
                    + i["inv_notes"] + i["inv_errors"] + (e.get("reasons") or []))
    return f"""<details class="tech"><summary>Technical Evidence (địa chỉ, claim ledger, API, ghi chú kiểm tra)</summary>
<table><tr><td>Hợp đồng</td><td class="addr">{rr.esc(i['token'])}</td></tr>
<tr><td>Deployer</td><td class="addr">{rr.esc(dep.get('deployer') or 'chưa đọc được')} {rr.esc('(hợp đồng: ' + str(dep.get('deployer_label') or 'factory') + ')' if dep.get('deployer_is_contract') else '')}</td></tr>
<tr><td>Giao dịch tạo</td><td class="addr">{rr.esc(dep.get('creation_tx') or 'chưa đọc được')}</td></tr>
<tr><td>Hợp đồng verify / proxy</td><td>{rr.esc('chưa đọc được hợp đồng (nguồn dữ liệu không trả kết quả); chưa kết luận về quyền owner' if ctr.get('is_verified') is None else f"{ctr.get('is_verified')} / {ctr.get('proxy_type')} · hàm quyền lực: {', '.join(ctr.get('power_functions') or []) or 'không thấy'}")}</td></tr>
<tr><td>Dữ kiện on-chain lúc</td><td>{rr.esc(f.get('generated_utc'))} UTC ({rr.esc(i['m']['fact_age_h'])} giờ trước)</td></tr>
<tr><td>Memo nghiên cứu</td><td>{rr.esc(pathlib.Path(e['memo']).name if e.get('memo') else 'không có')}</td></tr></table>
<h4>Pool</h4>{('<table>' + pools + '</table>') if pools else '<p class=muted>Không có.</p>'}
<h4>Claim ledger</h4>{('<table>' + cl + '</table>') if cl else '<p class=muted>Không có claim nào được ghi.</p>'}
<h4>Danh tính (mức do luật tính)</h4>{('<table>' + idt + '</table>') if idt else '<p class=muted>Không có cầu nối nào.</p>'}
<h4>Cảnh báo API / thu thập</h4>{('<ul>' + warns + '</ul>') if warns else '<p class=muted>Không có.</p>'}
<h4>Ghi chú kiểm tra tự động</h4>{('<ul>' + notes + '</ul>') if notes else '<p class=muted>Không có.</p>'}
</details>"""


def onchain_block(i: dict) -> str:
    mt = i["m"]
    hg = mt.get("holder_growth") or {}
    rows = [("Thanh khoản", _fmt_usd(mt["liq"])), ("Volume 24h", _fmt_usd(mt["vol24"])),
            ("Vòng quay 24h", _fmt(mt["turnover"], "x")), ("Holder", _fmt(mt["holders"])),
            ("Top 10 ví thường", _fmt(mt["top10_eoa"], "%")),
            ("Top 10 mọi địa chỉ (gồm pool)", _fmt(mt["top10_all"], "%")), ("Ví thường lớn nhất", _fmt(mt["largest_eoa"], "%")),
            ("FDV / thanh khoản", _fmt(mt["fdv_to_liq"], "x")), ("Tỉ lệ lệnh bán", _fmt(mt["sell_share"])),
            ("Tuổi pool", _fmt(mt["age_days"], " ngày")),
            ("Holder thay đổi", f"{hg.get('holders_delta'):+d} trong {hg.get('since_hours')} giờ" if isinstance(hg.get("holders_delta"), int) else "–")]
    src = ("Holder lấy từ GeckoTerminal vì Blockscout không trả dữ liệu. " if mt["holders_source"] == "geckoterminal" else "")
    # chỉ ghi những nguồn thực sự trả dữ liệu trong lần chạy này
    warned = " ".join(str(w) for w in ((i.get("fact") or {}).get("warnings") or [])).lower()
    used = [n for n, host in (("DexScreener", "dexscreener"), ("GeckoTerminal", "geckoterminal"), ("Blockscout", "blockscout"))
            if host not in warned or (host == "blockscout" and mt.get("holders") not in (None, "–"))]
    return ("<table>" + "".join(f"<tr><td>{rr.esc(k)}</td><td class='num'>{rr.esc(v)}</td></tr>" for k, v in rows)
            + f"</table><p class='note'>{rr.esc(src)}Nguồn: {rr.esc(', '.join(used))} <span class='ev ev-VERIFIED_ONCHAIN'>"
            + rr.esc(rr.EVIDENCE['VERIFIED_ONCHAIN']) + "</span></p>")


def data_quality_html(items: list[dict]) -> str:
    """Người đọc cuối phải thấy ngay dữ liệu nào thiếu hoặc mâu thuẫn, không phải mở phần kỹ thuật."""
    warns, seen = [], set()
    for i in items:
        for w in ((i.get("fact") or {}).get("warnings") or []):
            key = str(w).split(":")[0] if "không truy cập được" in str(w) or "chặn" in str(w) else str(w)
            if key not in seen:
                seen.add(key)
                warns.append(str(w))
    no_holder = [i["symbol"] for i in items if i["m"].get("top10_eoa") in (None, "–")]
    conflicts = [f"{i['symbol']} (lệch {pc['diff_pct']}%)" for i in items
                 for pc in [(((i.get("fact") or {}).get("market") or {}).get("price_check") or {})] if pc.get("conflict")]
    stamps = sorted(str((i.get("fact") or {}).get("generated_utc")) for i in items if (i.get("fact") or {}).get("generated_utc"))
    bullets = []
    if stamps:
        bullets.append(f"Số liệu thị trường và holder đo lúc {stamps[0]}" + (f" – {stamps[-1]}" if stamps[-1] != stamps[0] else "") + " UTC; giá memecoin thay đổi rất nhanh.")
    if no_holder:
        bullets.append("Chưa đo được mức tập trung holder của: " + ", ".join(no_holder) + ".")
    if conflicts:
        bullets.append("Giá giữa DexScreener và Blockscout lệch lớn ở: " + ", ".join(conflicts) + "; cần kiểm lại trước khi dùng số giá.")
    bullets += [w for w in warns if "Giá lệch" not in w][:6]
    if not bullets:
        return ""
    return ("<details class='dq'><summary><b>Độ tin cậy dữ liệu của lần chạy</b> "
            f"<span class='muted'>({len(bullets)} ghi chú)</span></summary><ul>"
            + "".join(f"<li>{rr.esc(b)}</li>" for b in bullets) + "</ul></details>")


def card_html(i: dict) -> str:
    e, pot, inv, mt, lk = i["e"], i["pot"], i["inv"], i["m"], i["links"]
    v = pot["verdict"]
    link_bits = [f"<a href='{rr.esc(lk['x'])}' rel='noopener noreferrer'>X</a>" if lk["x"] else "X: không có"]
    link_bits += [f"<a href='{rr.esc(u)}' rel='noopener noreferrer'>website</a>" for u in lk["websites"]] or ["website: không có"]
    if lk["telegram"]:
        link_bits.append(f"<a href='{rr.esc(lk['telegram'])}' rel='noopener noreferrer'>Telegram</a>")
    collide = (f"<span class='warn'>⚠ {i['collisions']} token khác cùng ticker đã thấy trên chuỗi: đối chiếu địa chỉ</span>"
               if i["collisions"] else "")
    status = {"COMPLETE": "Nghiên cứu hoàn tất", "INCOMPLETE": "Nghiên cứu chưa đủ", "FAILED": "Nghiên cứu lỗi",
              "QUEUED": "Chưa nghiên cứu"}[e["research_status"]]
    mode = {"DEEP": "Memo đầy đủ (ứng viên hàng đầu)", "BRIEF": "Đánh giá rút gọn"}.get(e.get("mode"), "")
    head = f"""<article class="card{' brief' if e.get('mode') == 'BRIEF' else ''}" id="t-{i['token']}">
<div class="top"><div class="ident">{i['logo']}<div><div class="tk">{rr.esc(i['symbol'])} <span class="muted" style="font-weight:400;font-size:15px">{rr.esc(i['name'])}</span></div>
<div class="meta"><span>Cặp: {rr.esc(i['pair'])}{PAIR_NOTE[i['official']]}</span>
<span>{CHAIN}</span><span>{' · '.join(link_bits)}</span></div><div class="meta"><span>{rr.esc(status)}{' · ' + rr.esc(mode) if mode else ''}</span>{collide}</div></div></div>
<div><span class="badge v-{v}">{rr.VERDICTS[v][1]} {rr.esc(rr.VERDICTS[v][0])}</span></div></div>"""

    if e["research_status"] != "COMPLETE":
        reasons = "".join(f"<li>{rr.esc(r)}</li>" for r in e.get("reasons") or []) or "<li>Chưa có memo.</li>"
        return head + f"<p>Token này không được đưa vào đánh giá cho nhà đầu tư vì nghiên cứu chưa hoàn tất:</p><ul>{reasons}</ul>{tech_evidence(i)}</article>"

    if not inv:
        why = "; ".join(i["inv_errors"]) or "agent cuối chưa viết memo cho token này"
        return (head + f"<p class='one'>{rr.esc(pot.get('one_liner'))}</p><p class='warn'>Chưa có investor memo hợp lệ ({rr.esc(why)}). "
                f"Phần dưới chỉ là số liệu tất định.</p>{_sec('Bằng chứng on-chain', onchain_block(i))}{tech_evidence(i)}</article>")

    conv, gv, lv = inv["conviction"], inv["growth_verdict"], inv["exit_level"]
    g = inv.get("growth_engine") or {}
    tvc = inv.get("token_value_capture") or {}
    lr = inv.get("liquidity_exit_risk") or {}
    moat = inv.get("moat") or {}
    tech = inv.get("technology") or {}
    ci = inv.get("creator_identity") or {}
    summary = (f"<p class='one'>{rr.esc(inv.get('project_thesis'))}</p>"
               f"<div class='meta'><span class='g-{gv}'>Tăng trưởng: {rr.esc(GROWTH[gv])}</span>"
               f"<span class='r-{lv}'>Rủi ro thoát hàng: {rr.esc(RISK_LABEL[lv])}</span>"
               f"<span>Độ tin cậy bằng chứng: {rr.esc(rr.CONF_LABEL[inv['evidence_confidence']])}</span>"
               f"<span>Điểm tiềm năng: {pot['total']}/{pot['max']}</span></div>")
    growth = (f"<p class='g-{gv}'><b>{rr.esc(GROWTH[gv])}</b></p>{_p(g.get('explanation'))}"
              + (f"<p><b>Vòng tăng trưởng:</b> {rr.esc(g.get('loop'))}</p>" if not _blank(g.get("loop")) else "")
              + (f"<p><b>Phụ thuộc người mua mới:</b> {'Có' if g.get('depends_on_new_buyers') else 'Không'}</p>"
                 if isinstance(g.get("depends_on_new_buyers"), bool) else ""))
    exit_risk = (f"<p class='r-{lv}'><b>{rr.esc(RISK_LABEL[lv])}</b></p>{_p(lr.get('assessment'))}"
                 + _list((lr.get("deterioration_signals") or []) + mt["exit_risk_reasons"]))
    conv_box = (f"<div class='conv'><span class='pill c-{conv}'>{rr.esc(CONVICTION[conv][0])}</span> "
                f"<span class='muted'>{rr.esc(CONVICTION[conv][1])}</span><p>{rr.esc(inv.get('conviction_memo'))}</p></div>")
    notes = "".join(f"<p class='note'>ⓘ {rr.esc(n)}</p>" for n in i["inv_notes"])

    if e["mode"] == "BRIEF":
        body = (summary + _sec("Tăng trưởng bền vững", growth) + _sec("Bằng chứng on-chain", onchain_block(i))
                + _sec("Thanh khoản & rủi ro thoát hàng", _list(mt["exit_risk_reasons"])) + conv_box + notes)
        return head + body + tech_evidence(i) + "</article>"

    body = summary + "<div class='grid'><div>" + "".join([
        _sec("Vấn đề dự án giải quyết", _p(inv.get("problem"))),
        _sec("Sản phẩm thực tế", _p(inv.get("product"))),
        _sec("Công nghệ và lợi thế", _p(tech.get("stack")) + _p(tech.get("advantage"))),
        _sec("Creator / team", _p(ci.get("summary")) + (f"<p><span class='ev ev-{rr.esc(ci.get('evidence'))}'>"
             f"{rr.esc(rr.EVIDENCE.get(str(ci.get('evidence')), ci.get('evidence')))}</span></p>" if ci.get("evidence") else "")),
        _sec("Creator đang nói gì", _list(inv.get("creator_commentary"))),
        _sec("Thu hút người dùng", _p(inv.get("user_acquisition"))),
        _sec("Vì sao người dùng quay lại", _p(inv.get("retention"))),
        _sec("Doanh thu / hoạt động kinh tế", _p(inv.get("monetization"))),
    ]) + "</div><div>" + "".join([
        _sec("Tăng trưởng bền vững", growth),
        _sec("Token nắm giữ giá trị thế nào", f"<p><b>Vai trò:</b> {rr.esc(tvc.get('role') or '–')}</p>"
             f"<p><b>Tăng trưởng sản phẩm tạo cầu token:</b> {rr.esc(DEMAND[inv['demand']])}</p>{_p(tvc.get('explanation'))}"),
        _sec("Traction", _list(inv.get("traction"))),
        _sec("Moat", f"<p><b>{rr.esc(MOAT[inv['moat_type']])}</b></p>{_p(moat.get('explanation'))}"),
        _sec("Bằng chứng on-chain", onchain_block(i)),
        _sec("Thanh khoản & rủi ro thoát hàng", exit_risk),
    ]) + "</div></div>" + "".join([
        _sec("Phân tích cặp cổ phiếu", _p(inv.get("stock_pair_analysis"))),
        "<div class='grid'><div>" + _sec("Catalyst", _list(inv.get("catalysts"))) + "</div><div>"
        + _sec("Điều làm thesis mất hiệu lực", _list(inv.get("invalidation_conditions"))) + "</div></div>",
        _sec("Câu hỏi còn mở", _list(inv.get("open_questions"))) if inv.get("open_questions") else "",
    ]) + conv_box + notes
    return head + body + tech_evidence(i) + "</article>"


def comparison_html(m: dict) -> str:
    p = run_path(m["run_id"]) / "comparison.json"
    if not p.is_file():
        return ""
    try:
        cmp_ = json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return "<p class='warn'>comparison.json hỏng, bỏ qua.</p>"
    if any(BANNED.search(t) for t in _texts(cmp_)):
        return "<p class='warn'>Phần so sánh bị loại vì chứa ngôn ngữ khuyến nghị giao dịch.</p>"
    rank = "".join(f"<li><b>{rr.esc(x.get('ticker') or x.get('token'))}</b>: {rr.esc(x.get('why'))}</li>"
                   for x in cmp_.get("ranking") or [] if isinstance(x, dict))
    return (f"<h2>So sánh giữa các token</h2><div class='card'>{_p(cmp_.get('summary'))}"
            + (f"<h4>Thứ tự ưu tiên nghiên cứu</h4><ol>{rank}</ol>" if rank else "")
            + (f"<h4>Điểm chung</h4>{_list(cmp_.get('patterns'))}" if cmp_.get("patterns") else "") + "</div>")


def render(m: dict) -> str:
    items = build_items(m)
    deep = [i for i in items if i["e"].get("mode") == "DEEP"]
    brief = [i for i in items if i["e"].get("mode") == "BRIEF"]
    other = [i for i in items if i["e"]["research_status"] != "COMPLETE"]
    rows = "".join(dash_row(n + 1, i) for n, i in enumerate(items))
    cands = "".join(
        f"<div class='cand'><a href='#t-{i['token']}'><div class='ident'>{i['logo']}<b>{rr.esc(i['symbol'])}</b></div>"
        f"<div style='margin-top:6px'>{conv_pill(i['inv']['conviction']) if i['inv'] else '<span class=muted>chưa có memo</span>'}</div>"
        f"<div class='note'>{rr.esc(_clip((i['inv'] or {}).get('project_thesis') or i['pot'].get('one_liner'), 150))}</div></a></div>"
        for i in deep if not (i["inv"] and i["inv"]["conviction"] == "DROP"))
    counts = {k: sum(1 for i in items if i["pot"]["verdict"] == k) for k in rr.DISPLAY_ORDER}
    stats = "".join(f"<span class='stat'>{rr.VERDICTS[k][1]} {rr.esc(rr.VERDICTS[k][0])}: <b>{counts[k]}</b></span>"
                    for k in rr.DISPLAY_ORDER if counts[k])
    created = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(m["created"]))
    section = lambda title, xs, sub="": (f"<h2>{rr.esc(title)}</h2>{sub}" + "".join(card_html(i) for i in xs)) if xs else ""
    return f"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Robinhood Token Research {rr.esc(m['run_id'])}</title>
<style>{rr.CSS}{CSS_EXTRA}</style></head><body><div class="wrap">
<h1>Robinhood Token Research: báo cáo cho nhà đầu tư</h1>
<p class="muted">Lần chạy {rr.esc(m['run_id'])} · bắt đầu {rr.esc(created)} · {len(items)} token đã xét · {CHAIN}</p>
<div class="disc"><b>Tài liệu nghiên cứu, không phải khuyến nghị đầu tư.</b> Báo cáo đánh giá chất lượng dự án và rủi ro,
không dự đoán giá. Phần lớn token tạo qua launchpad mất gần hết giá trị. Không bỏ vào số tiền bạn không chấp nhận mất.</div>
<div class="stats">{stats}</div>
{data_quality_html(items)}
<h2>Ứng viên hàng đầu</h2>{f'<div class="top-cands">{cands}</div>' if cands else '<p class="muted">Không token nào còn đáng theo đuổi trong lần chạy này.</p>'}
<h2>Bảng so sánh</h2><div class="tbl"><table><tr><th>#</th><th>Token</th><th>Cặp</th><th class="num">Thanh khoản</th>
<th class="num">Vol 24h</th><th class="num">Holder</th><th class="num" title="* = gồm cả pool/hợp đồng">Top 10</th><th>Tiềm năng</th><th>Tăng trưởng</th>
<th>Rủi ro thoát hàng</th><th>Kết luận · trạng thái</th></tr>{rows}</table></div>
{comparison_html(m)}
{section('Memo đầy đủ cho ứng viên hàng đầu', deep)}
{section('Các token còn lại (đánh giá rút gọn)', brief, '<p class="muted">Không nằm trong nhóm ứng viên hàng đầu của lần chạy này, nên chỉ có đánh giá ngắn.</p>')}
{section('Chưa hoàn tất nghiên cứu', other, '<p class="muted">Không được đưa vào đánh giá cho nhà đầu tư.</p>')}
<h2>Cách đọc</h2><ul>{''.join(f"<li><b>{rr.VERDICTS[k][1]} {rr.esc(rr.VERDICTS[k][0])}</b>: {rr.esc(rr.VERDICTS[k][2])}</li>" for k in rr.DISPLAY_ORDER)}</ul>
<ul>{''.join(f"<li><b>{rr.esc(v[0])}</b>: {rr.esc(v[1])}</li>" for v in CONVICTION.values())}</ul>
<p class="note">Top 10 có dấu * là tỉ lệ của mọi địa chỉ, gồm cả pool và hợp đồng (chưa tách được ví thường).</p>
<p class="note">Xếp loại tiềm năng, mức rủi ro thoát hàng tối thiểu và giới hạn của kết luận do luật cố định tính từ dữ liệu; agent AI không nâng được.
Số liệu on-chain, logo, link và bảng được tạo tự động, không qua AI.</p>
</div></body></html>"""


def cmd_render(a, m):
    html_text = render(m)
    rd = reports_dir()
    target = pathlib.Path(a.out).expanduser() if a.out else rd / f"scout_run_{m['run_id']}.html"
    target.write_text(html_text, encoding="utf-8")
    if not a.out:
        shutil.copyfile(target, rd / "latest.html")
    m["rendered"] = {"at": time.time(), "file": str(target)}
    save_manifest(m)
    print(f"Đã ghi {target}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Lần chạy Scout → HTML cho nhà đầu tư")
    ap.add_argument("--run", help="run id (mặc định: lần chạy hiện tại)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start"); s.add_argument("--tokens")
    s = sub.add_parser("complete"); s.add_argument("--token", required=True); s.add_argument("--memo", required=True)
    s = sub.add_parser("fail"); s.add_argument("--token", required=True); s.add_argument("--reason", required=True)
    s = sub.add_parser("plan"); s.add_argument("--deep", type=int)
    for name in ("gate", "evidence"):
        s = sub.add_parser(name); s.add_argument("--token", required=True)
    s = sub.add_parser("check-investor"); s.add_argument("--token", required=True); s.add_argument("--file")
    s = sub.add_parser("render"); s.add_argument("--out")
    sub.add_parser("status")
    a = ap.parse_args(argv)
    if a.cmd == "start":
        return cmd_start(a)
    run_id = a.run or current_run_id()
    if not run_id:
        print("Chưa có lần chạy nào. Chạy `run_report.py start` trước.", file=sys.stderr)
        return 2
    m = load_manifest(run_id)
    return {"complete": cmd_complete, "fail": cmd_fail, "plan": cmd_plan, "gate": cmd_gate,
            "evidence": cmd_evidence, "check-investor": cmd_check_investor, "render": cmd_render,
            "status": cmd_status}[a.cmd](a, m)


if __name__ == "__main__":
    sys.exit(main())
