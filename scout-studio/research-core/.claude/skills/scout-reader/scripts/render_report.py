#!/usr/bin/env python3
"""ĐỌC MEMO STOCK TOKEN SCOUT (.md) → bảng đánh giá dễ hiểu (HTML) hoặc tóm tắt JSON.

    python3 render_report.py                       # đọc ~/.stock-token-scout/reports, ghi index.html vào đó
    python3 render_report.py --dir DIR --out FILE  # thư mục memo khác / file HTML khác
    python3 render_report.py --json                # tóm tắt gọn cho Claude đọc (không phải mở từng memo)
    python3 render_report.py --check MEMO.md       # kiểm khối scout-verdict, in xếp loại do luật tính

Xếp loại cuối cùng do LUẬT trong file này tính từ điểm và cờ đỏ, không lấy nguyên văn chữ LLM viết.
Mọi chữ trong memo (tên token, mô tả...) có thể do người lạ đặt, nên luôn được escape khi đưa vào HTML.
Chỉ dùng thư viện chuẩn Python 3.9+.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import pathlib
import re
import sys
import time

SCHEMA = 1

DIMENSIONS = [
    ("mechanism", "Cơ chế & lý do tồn tại"),
    ("stock_link", "Liên kết cổ phiếu trung thực"),
    ("liquidity", "Thanh khoản & thị trường"),
    ("distribution", "Phân bổ holder"),
    ("incentives", "Động cơ của team"),
    ("transparency", "Minh bạch & danh tính"),
]
DIM_KEYS = [k for k, _ in DIMENSIONS]

HARD_FLAGS = {
    "FAKE_STOCK_PAIR": "Ghép cặp với stock token giả",
    "CORE_CLAIM_CONFLICT": "Tuyên bố cốt lõi mâu thuẫn với dữ liệu chuỗi",
    "FALSE_BACKING_CLAIM": "Nói 'được bảo chứng bằng cổ phiếu' nhưng thực chất chỉ ghép cặp",
    "HONEYPOT_PATTERN": "Dấu hiệu mua được nhưng khó bán (honeypot)",
    "IMPERSONATION": "Mạo danh Robinhood hoặc thương hiệu khác",
    "OWNER_CAN_MINT": "Ví cá nhân còn quyền in thêm token",
    "TEAM_DUMPING": "Team hoặc deployer đang xả lượng lớn",
    "PROMPT_INJECTION": "Nội dung dự án chứa câu lệnh nhắm vào AI",
}

# mã: (nhãn, biểu tượng, giải thích một câu)
VERDICTS = {
    "RESEARCH_DEEPER": ("ĐÁNG NGHIÊN CỨU SÂU", "🟢", "Nền tảng tốt hơn mặt bằng chung. Vẫn chưa phải lý do để mua."),
    "UNPROVEN": ("CÓ Ý TƯỞNG, CHƯA CHỨNG MINH", "🟡", "Có vài điểm tốt, nhưng phần quan trọng nhất chưa được kiểm chứng."),
    "SPECULATIVE": ("ĐẦU CƠ THUẦN", "🟠", "Không có lý do tồn tại ngoài việc được giao dịch. Tham gia là chấp nhận khả năng mất toàn bộ."),
    "AVOID": ("TRÁNH XA", "🔴", "Có dấu hiệu gian dối hoặc rủi ro cấu trúc nghiêm trọng. Điểm số không còn ý nghĩa."),
    "UNRATED": ("CHƯA ĐỦ DỮ LIỆU", "⚪", "Memo chưa có đánh giá, hoặc thiếu quá nhiều dữ liệu để chấm."),
}
DISPLAY_ORDER = ["RESEARCH_DEEPER", "UNPROVEN", "SPECULATIVE", "AVOID", "UNRATED"]

CONF_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
CONF_LABEL = {"LOW": "Thấp", "MEDIUM": "Trung bình", "HIGH": "Cao"}

EVIDENCE = {
    "VERIFIED_ONCHAIN": "Đã kiểm trên blockchain",
    "VERIFIED_OFFCHAIN": "Hai nguồn chính thức khớp nhau",
    "LIKELY": "Khả năng cao, một nguồn",
    "UNCONFIRMED": "Chưa kiểm chứng",
    "CONFLICT": "Mâu thuẫn với dữ liệu",
}

STALE_HOURS = 24
BLOCK_RE = re.compile(r"```scout-verdict[ \t]*\r?\n(.*?)\r?\n[ \t]*```", re.S)
ADDR_RE = re.compile(r"0x[0-9a-fA-F]{40}")
STAMP_RE = re.compile(r"(\d{8})_(\d{4})")


# ---------------------------------------------------------------- luật xếp loại

def _score(x):
    """Điểm hợp lệ là số nguyên 0–5; null/thiếu nghĩa là không đủ dữ liệu (khác với 0)."""
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return None
    return max(0, min(5, int(round(x))))


def compute(v: dict) -> dict:
    """Tính xếp loại từ điểm + cờ đỏ. Trả về dict kết quả và danh sách ghi chú điều chỉnh."""
    raw = v.get("scores") if isinstance(v.get("scores"), dict) else {}
    scores = {k: _score(raw.get(k)) for k in DIM_KEYS}
    known = {k: s for k, s in scores.items() if s is not None}
    flags = [str(f).strip() for f in (v.get("hard_flags") or []) if str(f).strip()]
    total, maxp = sum(known.values()), 5 * len(known)
    pct = total / maxp if maxp else 0.0
    notes = []

    conf = str(v.get("confidence", "LOW")).upper()
    conf = conf if conf in CONF_RANK else "LOW"
    cap = "HIGH" if len(known) == 6 else ("MEDIUM" if len(known) >= 4 else "LOW")
    if CONF_RANK[conf] > CONF_RANK[cap]:
        notes.append(f"Độ tin cậy hạ về {CONF_LABEL[cap]} vì chỉ chấm được {len(known)}/6 tiêu chí.")
        conf = cap

    if flags:
        verdict = "AVOID"
    elif len(known) < 3:
        verdict = "UNRATED"
        notes.append("Chỉ chấm được dưới 3/6 tiêu chí, chưa đủ để kết luận.")
    elif pct < 0.40:
        verdict = "SPECULATIVE"
    elif pct < 0.65:
        verdict = "UNPROVEN"
    else:
        blockers = []
        if len(known) < 5:
            blockers.append("thiếu dữ liệu ở quá 1 tiêu chí")
        if (scores["mechanism"] or 0) < 3:
            blockers.append("chưa có cơ chế/lý do tồn tại được kiểm chứng")
        if scores["liquidity"] == 0 or scores["distribution"] == 0:
            blockers.append("thanh khoản hoặc phân bổ holder ở mức 0")
        if conf == "LOW":
            blockers.append("độ tin cậy thấp")
        if blockers:
            verdict = "UNPROVEN"
            notes.append("Điểm đủ cao nhưng chưa đạt mức 'Đáng nghiên cứu sâu' vì " + "; ".join(blockers) + ".")
        else:
            verdict = "RESEARCH_DEEPER"

    # Không có lý do tồn tại ngoài giao dịch (cơ chế 0–1) thì đúng nghĩa là đầu cơ thuần,
    # dù thanh khoản hay độ minh bạch có cao: điểm phụ không bù được việc thiếu cơ chế.
    if verdict in ("UNPROVEN", "RESEARCH_DEEPER") and scores["mechanism"] is not None and scores["mechanism"] <= 1:
        notes.append("Giới hạn ở ĐẦU CƠ THUẦN vì điểm cơ chế ≤ 1: token không dùng vào việc gì ngoài giao dịch.")
        verdict = "SPECULATIVE"

    claimed = str(v.get("verdict", "")).upper()
    if claimed and claimed != verdict:
        notes.append(f"Agent đề xuất {VERDICTS.get(claimed, (claimed,))[0]}; luật chấm ra {VERDICTS[verdict][0]}. Dùng kết quả của luật.")

    return {"verdict": verdict, "scores": scores, "total": total, "max": maxp, "pct": pct,
            "confidence": conf, "hard_flags": flags, "notes": notes}


def validate(v: dict) -> list:
    """Cảnh báo về cấu trúc khối verdict (không chặn việc hiển thị)."""
    warn = []
    if v.get("schema") != SCHEMA:
        warn.append(f"schema nên là {SCHEMA}")
    raw = v.get("scores")
    if not isinstance(raw, dict):
        warn.append("thiếu 'scores'")
    else:
        for k in raw:
            if k not in DIM_KEYS:
                warn.append(f"tiêu chí lạ trong scores: {k}")
        for k in DIM_KEYS:
            x = raw.get(k)
            if x is not None and (_score(x) is None or not 0 <= x <= 5):
                warn.append(f"điểm {k} phải là số 0–5 hoặc null")
    for f in v.get("hard_flags") or []:
        if str(f) not in HARD_FLAGS:
            warn.append(f"cờ đỏ ngoài danh sách chuẩn: {f}")
    for key in ("ticker", "one_liner", "bear_case"):
        if not str(v.get(key, "")).strip():
            warn.append(f"thiếu '{key}'")
    return warn


# ---------------------------------------------------------------- đọc memo

def _section(text: str, heading: str) -> str:
    m = re.search(r"^##\s*" + re.escape(heading) + r"[^\n]*\n(.*?)(?=^##\s|\Z)", text, re.S | re.M)
    return m.group(1).strip() if m else ""


def _first_para(s: str, limit: int = 400) -> str:
    for para in re.split(r"\n\s*\n", s):
        p = " ".join(line.strip() for line in para.splitlines() if line.strip() and not line.strip().startswith("```"))
        if p:
            return p if len(p) <= limit else p[: limit - 1] + "…"
    return ""


def _stamp(path: pathlib.Path, v: dict) -> float:
    at = str(v.get("assessed_at", ""))
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%MZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return dt.datetime.strptime(at, fmt).replace(tzinfo=dt.timezone.utc).timestamp()
        except ValueError:
            pass
    m = STAMP_RE.search(path.name)
    if m:
        try:
            return dt.datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M").replace(tzinfo=dt.timezone.utc).timestamp()
        except ValueError:
            pass
    return path.stat().st_mtime


def parse_memo(path: pathlib.Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    head = next((l for l in text.splitlines() if l.startswith("# ")), "# " + path.stem)
    title = head[2:].strip()
    ticker_guess, _, name_guess = title.partition(":")
    addr = ADDR_RE.search(text)
    item = {"file": path.name, "path": str(path), "errors": [], "warnings": []}

    m = BLOCK_RE.search(text)
    v = {}
    if m:
        try:
            v = json.loads(m.group(1))
            if not isinstance(v, dict):
                raise ValueError("khối verdict phải là object JSON")
        except (ValueError, json.JSONDecodeError) as e:
            item["errors"].append(f"khối scout-verdict không đọc được: {e}")
            v = {}
    if v:
        item["warnings"] = validate(v)
        item.update(compute(v))
    else:
        if not m:
            item["errors"].append("memo chưa có khối scout-verdict")
        item.update({"verdict": "UNRATED", "scores": {k: None for k in DIM_KEYS}, "total": 0, "max": 0,
                     "pct": 0.0, "confidence": "LOW", "hard_flags": [], "notes": []})

    rating = re.search(r"Xếp loại:\s*([^|*\n]+)", text)
    item.update({
        "ticker": str(v.get("ticker") or ticker_guess.strip() or path.stem)[:40],
        "name": str(v.get("name") or name_guess.strip())[:80],
        "token": str(v.get("token") or (addr.group(0) if addr else "")).lower(),
        "memo_rating": str(v.get("memo_rating") or (rating.group(1).strip() if rating else "")),
        "one_liner": str(v.get("one_liner") or _first_para(_section(text, "Kết luận nhanh"))),
        "bull_case": str(v.get("bull_case", "")),
        "bear_case": str(v.get("bear_case", "")),
        "what_must_be_true": [str(x) for x in (v.get("what_must_be_true") or [])][:6],
        "watch_triggers": [str(x) for x in (v.get("watch_triggers") or [])][:6],
        "key_facts": [f for f in (v.get("key_facts") or []) if isinstance(f, dict)][:10],
        "ts": _stamp(path, v),
    })
    return item


def load(report_dir: pathlib.Path) -> dict:
    tokens, history = {}, {}
    cycles = sorted(report_dir.glob("cycle_*.md"))
    for p in sorted(report_dir.glob("*.md")):
        if p.name.startswith("cycle_"):
            continue
        it = parse_memo(p)
        key = it["token"] or it["ticker"].lower()
        history[key] = history.get(key, 0) + 1
        if key not in tokens or it["ts"] >= tokens[key]["ts"]:
            tokens[key] = it
    for k, it in tokens.items():
        it["memo_count"] = history[k]
        it["age_h"] = max(0.0, (time.time() - it["ts"]) / 3600)
    items = sorted(tokens.values(), key=lambda i: (DISPLAY_ORDER.index(i["verdict"]), -i["pct"], i["ticker"]))
    return {"items": items, "latest_cycle": cycles[-1].name if cycles else None}


# ---------------------------------------------------------------- JSON cho Claude

def summary_json(data: dict) -> list:
    out = []
    for i in data["items"]:
        out.append({
            "ticker": i["ticker"], "token": i["token"], "verdict": i["verdict"],
            "label": VERDICTS[i["verdict"]][0], "score": f'{i["total"]}/{i["max"]}' if i["max"] else None,
            "confidence": i["confidence"], "hard_flags": i["hard_flags"], "one_liner": i["one_liner"],
            "age_hours": round(i["age_h"], 1), "file": i["file"], "notes": i["notes"] + i["errors"],
        })
    return out


# ---------------------------------------------------------------- HTML

def esc(x) -> str:
    return html.escape(str(x), quote=True)


CSS = """
:root{--bg:#f7f7f5;--card:#fff;--ink:#1c1c1a;--muted:#6b6b66;--line:#e4e4df;--bar:#ececE8;
--g:#1f8a4c;--y:#b7860b;--o:#c8611a;--r:#c0392b;--n:#8a8a85;--accent:#2f5bd3}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#141413;--card:#1e1e1c;--ink:#eeeeea;
--muted:#a3a39c;--line:#33332f;--bar:#2c2c29;--g:#3fbf74;--y:#e0b43a;--o:#ef8a45;--r:#ef6b5c;--n:#9a9a94;--accent:#7b9cff}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1040px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:26px;margin:0 0 4px}h2{font-size:18px;margin:32px 0 12px}.muted{color:var(--muted)}
.disc{border:1px solid var(--line);border-left:4px solid var(--r);background:var(--card);padding:12px 14px;border-radius:8px;margin:16px 0}
.stats{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0}.stat{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px;margin:14px 0}
.top{display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px;align-items:flex-start}
.tk{font-size:20px;font-weight:700}.addr{font-family:ui-monospace,Menlo,monospace;font-size:12px;color:var(--muted);word-break:break-all}
.badge{display:inline-block;padding:4px 10px;border-radius:999px;font-weight:700;font-size:13px;color:#fff}
.v-RESEARCH_DEEPER{background:var(--g)}.v-UNPROVEN{background:var(--y)}.v-SPECULATIVE{background:var(--o)}.v-AVOID{background:var(--r)}.v-UNRATED{background:var(--n)}
.one{font-size:16px;margin:12px 0}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media (max-width:720px){.grid{grid-template-columns:1fr}}
.dim{display:grid;grid-template-columns:170px 1fr 34px;gap:8px;align-items:center;font-size:13px;margin:4px 0}
.bar{height:8px;background:var(--bar);border-radius:4px;overflow:hidden}.bar i{display:block;height:100%;background:var(--accent)}
.flag{color:var(--r);font-weight:600}.note{font-size:13px;color:var(--muted)}
table{width:100%;border-collapse:collapse;font-size:13px}td{border-top:1px solid var(--line);padding:6px 4px;vertical-align:top}
.ev{font-size:11px;padding:1px 6px;border-radius:4px;border:1px solid var(--line);white-space:nowrap}
.ev-CONFLICT{border-color:var(--r);color:var(--r)}.ev-VERIFIED_ONCHAIN{border-color:var(--g);color:var(--g)}
ul{margin:6px 0;padding-left:20px}h4{margin:12px 0 4px;font-size:14px}.stale{color:var(--o);font-size:13px}
a{color:var(--accent)}details{margin-top:10px}summary{cursor:pointer;color:var(--muted)}
"""


def _ul(xs) -> str:
    return "<ul>" + "".join(f"<li>{esc(x)}</li>" for x in xs) + "</ul>" if xs else "<p class='muted'>Chưa có.</p>"


def card(i: dict) -> str:
    label, icon, expl = VERDICTS[i["verdict"]]
    dims = "".join(
        f"<div class='dim'><span>{esc(name)}</span><span class='bar'><i style='width:{(i['scores'][k] or 0) * 20}%'></i></span>"
        f"<b>{esc(i['scores'][k]) if i['scores'][k] is not None else '?'}</b></div>"
        for k, name in DIMENSIONS)
    flags = "".join(f"<li class='flag'>{esc(HARD_FLAGS.get(f, f))}</li>" for f in i["hard_flags"])
    facts = "".join(
        f"<tr><td>{esc(f.get('label', ''))}</td><td>{esc(f.get('value', ''))}</td>"
        f"<td><span class='ev ev-{esc(f.get('evidence', ''))}'>{esc(EVIDENCE.get(str(f.get('evidence')), f.get('evidence', '')))}</span></td></tr>"
        for f in i["key_facts"])
    notes = "".join(f"<p class='note'>ⓘ {esc(n)}</p>" for n in i["notes"] + i["errors"])
    stale = f"<p class='stale'>Dữ liệu đã {i['age_h']:.0f} giờ tuổi. Memecoin đổi rất nhanh, hãy chạy lại trước khi dựa vào.</p>" if i["age_h"] > STALE_HOURS else ""
    score = f"{i['total']}/{i['max']} điểm" if i["max"] else "chưa chấm"
    return f"""<article class="card">
<div class="top"><div><div class="tk">{esc(i['ticker'])} <span class="muted" style="font-weight:400;font-size:15px">{esc(i['name'])}</span></div>
<div class="addr">{esc(i['token'])}</div></div>
<div><span class="badge v-{i['verdict']}">{icon} {esc(label)}</span></div></div>
<p class="muted" style="margin:6px 0 0">{esc(expl)}</p>
<p class="one">{esc(i['one_liner']) or '<span class="muted">Memo không có kết luận nhanh.</span>'}</p>
{stale}{('<ul>' + flags + '</ul>') if flags else ''}
<div class="grid"><div><h4>Chấm điểm ({esc(score)}, độ tin cậy: {esc(CONF_LABEL[i['confidence']])})</h4>{dims}</div>
<div><h4>Dữ kiện chính</h4>{('<table>' + facts + '</table>') if facts else '<p class="muted">Chưa có.</p>'}</div></div>
<div class="grid"><div><h4>Kịch bản tốt nhất</h4><p>{esc(i['bull_case']) or '<span class="muted">Chưa có.</span>'}</p></div>
<div><h4>Kịch bản xấu nhất</h4><p>{esc(i['bear_case']) or '<span class="muted">Chưa có.</span>'}</p></div></div>
<details><summary>Điều gì phải đúng để đánh giá tốt lên, và dấu hiệu cần theo dõi</summary>
<h4>Phải đúng</h4>{_ul(i['what_must_be_true'])}<h4>Theo dõi</h4>{_ul(i['watch_triggers'])}</details>
{notes}
<p class="note">Memo gốc: <a href="{esc(i['file'])}">{esc(i['file'])}</a> · {esc(i['memo_count'])} memo cho token này · Xếp loại theo dõi của researcher: {esc(i['memo_rating'] or 'không ghi')}</p>
</article>"""


def render_html(data: dict) -> str:
    items = data["items"]
    counts = {k: sum(1 for i in items if i["verdict"] == k) for k in DISPLAY_ORDER}
    stats = "".join(f"<span class='stat'>{VERDICTS[k][1]} {esc(VERDICTS[k][0])}: <b>{counts[k]}</b></span>"
                    for k in DISPLAY_ORDER if counts[k])
    cycle = (f"<p class='muted'>Memo tổng hợp chu kỳ mới nhất: <a href='{esc(data['latest_cycle'])}'>{esc(data['latest_cycle'])}</a></p>"
             if data["latest_cycle"] else "")
    legend = "".join(f"<li><b>{VERDICTS[k][1]} {esc(VERDICTS[k][0])}</b>: {esc(VERDICTS[k][2])}</li>" for k in DISPLAY_ORDER)
    ev = "".join(f"<li><span class='ev ev-{k}'>{esc(v)}</span> <span class='muted'>({k})</span></li>" for k, v in EVIDENCE.items())
    body = "".join(card(i) for i in items) or "<p class='muted'>Chưa có memo nào trong thư mục này.</p>"
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Robinhood Token Research</title><style>{CSS}</style></head>
<body><div class="wrap">
<h1>Robinhood Token Research</h1><p class="muted">Đánh giá tiềm năng token ghép cặp cổ phiếu trên Robinhood Chain · tạo lúc {esc(now)} · {len(items)} token</p>
<div class="disc"><b>Đây là tài liệu nghiên cứu, không phải khuyến nghị đầu tư.</b> Xếp loại đánh giá chất lượng dự án, không dự đoán giá.
Phần lớn token tạo qua launchpad mất gần hết giá trị. Không bỏ vào số tiền bạn không chấp nhận mất.</div>
<div class="stats">{stats}</div>{cycle}
{body}
<h2>Cách đọc</h2><ul>{legend}</ul>
<p>Điểm mỗi tiêu chí từ 0 đến 5. Dấu <b>?</b> nghĩa là không đủ dữ liệu, khác với 0. Xếp loại do luật cố định tính từ điểm và cờ đỏ,
agent AI không tự nâng được. Chỉ cần một cờ đỏ là xếp loại thành TRÁNH XA.</p>
<h4>Nhãn bằng chứng</h4><ul>{ev}</ul>
</div></body></html>"""


# ---------------------------------------------------------------- CLI

def default_dir() -> pathlib.Path:
    base = os.getenv("STS_REPORT_DIR") or os.path.join(os.getenv("STS_CACHE_DIR") or os.path.expanduser("~/.stock-token-scout"), "reports")
    return pathlib.Path(base).expanduser()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Dựng bảng đánh giá từ memo Stock Token Scout")
    ap.add_argument("--dir", help="thư mục chứa memo .md")
    ap.add_argument("--out", help="file HTML đầu ra (mặc định <dir>/index.html)")
    ap.add_argument("--json", action="store_true", help="in tóm tắt JSON thay vì ghi HTML")
    ap.add_argument("--check", metavar="MEMO", help="kiểm một memo và in xếp loại do luật tính")
    a = ap.parse_args(argv)

    if a.check:
        p = pathlib.Path(a.check).expanduser()
        if not p.is_file():
            print(f"Không thấy file {p}", file=sys.stderr)
            return 2
        it = parse_memo(p)
        out = {k: it[k] for k in ("ticker", "verdict", "total", "max", "confidence", "hard_flags", "notes", "warnings", "errors")}
        out["label"] = VERDICTS[it["verdict"]][0]
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 1 if it["errors"] else 0

    d = pathlib.Path(a.dir).expanduser() if a.dir else default_dir()
    if not d.is_dir():
        print(f"Không thấy thư mục memo {d}", file=sys.stderr)
        return 2
    data = load(d)
    if a.json:
        print(json.dumps(summary_json(data), ensure_ascii=False, indent=1))
        return 0
    out = pathlib.Path(a.out).expanduser() if a.out else d / "index.html"
    out.write_text(render_html(data), encoding="utf-8")
    print(f"Đã ghi {out} ({len(data['items'])} token)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
