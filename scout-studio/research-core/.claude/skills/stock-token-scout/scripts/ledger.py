#!/usr/bin/env python3
"""SỔ BẰNG CHỨNG: nơi mọi thông tin off-chain đi vào trước khi tới LLM.

Ba việc:
1. evidence  — lưu bài X / tin / đoạn docs, loại trùng bằng hash. LLM chỉ đọc mục MỚI.
2. page      — tải website/docs, so hash với lần trước. Không đổi thì không cần LLM đọc lại.
3. bridge / claim — ghi cầu nối danh tính và tuyên bố của dự án, tính mức tin cậy bằng LUẬT CỐ ĐỊNH,
                    rồi đối chiếu tuyên bố với dữ liệu on-chain.

Ví dụ:
  python3 ledger.py evidence add-batch --token 0xT --file results.json
  python3 ledger.py evidence pending --token 0xT
  python3 ledger.py evidence done --token 0xT
  python3 ledger.py page --token 0xT --url https://site.xyz --official
  python3 ledger.py bridge add --token 0xT --subject creator --entity @alice --type project_names_creator --url https://x.com/proj/status/1
  python3 ledger.py bridge show --token 0xT
  python3 ledger.py claim add --token 0xT --type paired_with --arg NVDA --claim "ABC launched paired with NVDA" --url https://...
  python3 ledger.py claim verify --token 0xT
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import html
import json
import re
import time
import urllib.request
from urllib.parse import urlparse

import common as c
import store

# ------------------------------------------------------------------ bridge strength
# V = xác minh bằng mật mã; S = kênh chính thức do chính dự án/creator kiểm soát; M = trung bình; W = yếu
BRIDGES = {
    "project": {
        "website_links_contract": "S", "x_links_contract": "S", "launchpad_profile": "S",
        "x_links_website": "M", "website_links_x": "M", "dex_profile_links": "M", "fomo_metadata": "W",
        "third_party_mention": "W", "contradiction": "X",
    },
    "creator": {
        "signed_message": "V", "creator_self_claim_with_contract": "S", "launchpad_creator_profile": "S",
        "project_names_creator": "S", "website_names_creator": "S", "creator_self_claim": "M",
        "project_reposts_creator": "W", "third_party_mention": "W", "contradiction": "X",
    },
    "wallet": {
        "signed_message": "V", "launchpad_creator_profile": "S", "public_wallet_disclosure_repeated": "S",
        "single_wallet_disclosure": "M", "contradiction": "X",
    },
}
CREATOR_SIDE = {"signed_message", "creator_self_claim_with_contract", "launchpad_creator_profile"}
PROJECT_SIDE = {"project_names_creator", "website_names_creator"}


def domain(u: str) -> str:
    return (urlparse(u or "").netloc or "").lower().removeprefix("www.")


def attribution_level(subject: str, rows: list) -> tuple[str, str]:
    types = [r["bridge"] for r in rows]
    strength = [BRIDGES[subject].get(t, "W") for t in types]
    if "X" in strength:
        return "CONFLICT", "có bằng chứng mâu thuẫn"
    if "V" in strength:
        return "VERIFIED_OFFCHAIN", "có chữ ký ví"
    S = [r for r in rows if BRIDGES[subject].get(r["bridge"]) == "S"]
    M = [r for r in rows if BRIDGES[subject].get(r["bridge"]) == "M"]
    if subject == "project":
        if len({domain(r["url"]) for r in S}) >= 2 or (S and M and {domain(r["url"]) for r in S} != {domain(r["url"]) for r in M}):
            return "VERIFIED_OFFCHAIN", "hai kênh chính thức độc lập cùng trỏ về hợp đồng"
        if S or len(M) >= 2:
            return "LIKELY", "mới có một kênh chính thức"
        return "UNCONFIRMED", "chỉ có nguồn yếu"
    if subject == "creator":
        if set(types) & CREATOR_SIDE and set(types) & PROJECT_SIDE:
            return "VERIFIED_OFFCHAIN", "creator tự nhận kèm hợp đồng và phía dự án xác nhận"
        if S:
            return "LIKELY", "một phía xác nhận"
        return "UNCONFIRMED", "chỉ có nhắc tên, repost hoặc tự nhận không kèm hợp đồng"
    # wallet ↔ người
    if S:
        return ("VERIFIED_OFFCHAIN" if len(S) >= 2 or "launchpad_creator_profile" in types else "LIKELY"), "công bố ví từ kênh chính thức"
    return "UNCONFIRMED", "không suy ra danh tính từ quan hệ ví"


# ------------------------------------------------------------------ evidence
def cmd_evidence(a, con):
    if a.action in ("add", "add-batch"):
        items = json.load(open(a.file, encoding="utf-8")) if a.action == "add-batch" else [
            {"url": a.url, "source": a.source, "category": a.category, "text": a.text, "author": a.author,
             "posted_at": a.posted_at}]
        new = []
        for it in items:
            h = store.text_hash(it.get("url"), it.get("text", ""))
            try:
                con.execute("INSERT INTO evidence(token, url, source, category, author, posted_at, text, hash, first_seen)"
                            " VALUES(?,?,?,?,?,?,?,?,?)",
                            (a.token.lower(), it.get("url"), it.get("source", "web"), it.get("category", "event"),
                             it.get("author"), it.get("posted_at"), (it.get("text") or "")[:4000], h, time.time()))
                new.append(it)
            except Exception:           # UNIQUE(token, hash): đã thấy
                pass
        con.commit()
        print(json.dumps({"received": len(items), "new": len(new), "new_items": new}, ensure_ascii=False, indent=1))
    elif a.action == "pending":
        rows = con.execute("SELECT id, url, source, category, author, posted_at, text FROM evidence"
                           " WHERE token=? AND processed=0 ORDER BY id LIMIT ?", (a.token.lower(), a.limit)).fetchall()
        print(json.dumps([dict(r) for r in rows], ensure_ascii=False, indent=1))
    elif a.action == "done":
        con.execute("UPDATE evidence SET processed=1 WHERE token=? AND processed=0", (a.token.lower(),))
        con.commit()
        print("ok")


# ------------------------------------------------------------------ pages
def html_to_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<[^>]+>", " ", raw))).strip()


def cmd_page(a, con):
    try:
        req = urllib.request.Request(a.url, headers={"User-Agent": "stock-token-scout/2.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read(2_000_000).decode("utf-8", "replace")
    except Exception as e:
        print(json.dumps({"status": "FETCH_FAILED", "error": str(e)[:200],
                          "hint": "Trang có thể cần JavaScript: dùng web fetch của agent rồi lưu bằng evidence add."}))
        return
    text = html_to_text(raw)
    h = hashlib.sha256(text.encode()).hexdigest()[:24]
    token = a.token.lower()
    prev = con.execute("SELECT hash, text FROM pages WHERE url=? AND token=?", (a.url, token)).fetchone()
    has_ca = token in raw.lower()
    handles = sorted(set(re.findall(r"(?:x|twitter)\.com/([A-Za-z0-9_]{2,15})", raw)))[:10]
    out = {"url": a.url, "contains_contract": has_ca, "x_handles_found": handles}
    if prev and prev["hash"] == h:
        out["status"] = "UNCHANGED"
    else:
        if prev:
            old = re.split(r"(?<=[.!?])\s+", prev["text"])
            new = re.split(r"(?<=[.!?])\s+", text)
            diff = [l for l in difflib.unified_diff(old, new, lineterm="", n=0) if l[:1] in "+-" and l[:3] not in ("+++", "---")]
            out.update(status="CHANGED", diff=diff[:60])
        else:
            out.update(status="NEW", text=text[:6000])
        con.execute("INSERT OR REPLACE INTO pages(url, token, hash, text, last_checked) VALUES(?,?,?,?,?)",
                    (a.url, token, h, text, time.time()))
    if a.official:
        if has_ca:
            _add_bridge(con, token, "project", domain(a.url), "website_links_contract", a.url, "tự phát hiện")
        for hd in handles:
            _add_bridge(con, token, "project", f"@{hd}", "website_links_x", a.url, "tự phát hiện")
        out["bridges_recorded"] = True
    con.commit()
    print(json.dumps(out, ensure_ascii=False, indent=1))


# ------------------------------------------------------------------ bridges
def _add_bridge(con, token, subject, entity, btype, url, note=None):
    if btype == "wallet_relationship":
        raise SystemExit("Không ghi được: quan hệ ví không phải bằng chứng danh tính.")
    if btype not in BRIDGES[subject]:
        raise SystemExit(f"Loại cầu nối không hợp lệ cho {subject}: {sorted(BRIDGES[subject])}")
    con.execute("INSERT OR IGNORE INTO bridges(token, subject, entity, bridge, url, note, ts) VALUES(?,?,?,?,?,?,?)",
                (token, subject, entity.lower(), btype, url, note, time.time()))


def attribution_table(con, token: str) -> list[dict]:
    rows = con.execute("SELECT * FROM bridges WHERE token=? ORDER BY subject, entity", (token,)).fetchall()
    groups: dict[tuple, list] = {}
    for r in rows:
        groups.setdefault((r["subject"], r["entity"]), []).append(r)
    out = []
    for (subject, entity), rs in groups.items():
        level, why = attribution_level(subject, rs)
        out.append({"subject": subject, "entity": entity, "level": level, "reason": why,
                    "evidence": [f"{r['bridge']}: {r['url']}" for r in rs]})
    return out


def cmd_bridge(a, con):
    token = a.token.lower()
    if a.action == "add":
        _add_bridge(con, token, a.subject, a.entity, a.type, a.url, a.note)
        con.commit()
    print(json.dumps(attribution_table(con, token), ensure_ascii=False, indent=1))


# ------------------------------------------------------------------ claims
AUTO = {"paired_with", "burn_mechanism", "fixed_supply", "lp_locked", "stock_backed", "team_allocation",
        "contract_address"}
CLAIM_TYPES = sorted(AUTO | {"utility", "revenue", "partnership", "other"})


def verify_claim(con, token: str, cl) -> tuple[str, str]:
    fact, _ = store.latest_fact(con, token, "onchain")
    t, arg = cl["ctype"], (cl["arg"] or "").upper()
    if t == "paired_with":
        wl_rev = {v: k for k, v in c.load_whitelist().items()}
        canon = con.execute("SELECT pool FROM pools WHERE token=? AND stock=?", (token, arg)).fetchone()
        pools = (fact or {}).get("pools") or []
        if canon or any(p.get("stock") == arg for p in pools):
            return "VERIFIED_ONCHAIN", f"Có pool {arg} với stock token chính chủ {wl_rev.get(arg, '')}"
        fake = [p for p in pools if (p.get("counter") or "").upper() == arg and not p.get("stock")]
        if fake:
            return "CONFLICT", f"Pool ghép với token tên {arg} nhưng KHÔNG phải địa chỉ chính chủ: {fake[0].get('counter_addr')}"
        return "UNCONFIRMED", "Chưa thấy pool nào ghép với stock token này"
    if t == "contract_address":
        return (("VERIFIED_ONCHAIN", "Địa chỉ dự án công bố khớp token đang phân tích") if arg.lower() == token
                else ("CONFLICT", f"Dự án công bố địa chỉ {arg.lower()} khác token đang phân tích"))
    if t == "stock_backed":
        # Ghép cặp trong pool KHÔNG phải bảo chứng. Chỉ có thể nâng mức nếu người phân tích tự tìm được
        # cơ chế quy đổi (redeem) và ghi lại bằng `claim set` kèm bằng chứng.
        return "CONFLICT", ("Tuyên bố 'được bảo chứng bằng cổ phiếu' nhưng on-chain chỉ thấy quan hệ ghép cặp trong AMM, "
                            "không thấy cơ chế quy đổi cho holder")
    if not fact:
        return "UNCONFIRMED", "Chưa có dữ kiện on-chain: chạy onchain.py trước"
    if t == "team_allocation":
        dep = fact.get("deployer") or {}
        try:
            claimed = float(arg.strip("%"))
        except ValueError:
            return "UNCONFIRMED", "Tham số phải là phần trăm, ví dụ --arg 5"
        if dep.get("deployer_is_contract") or dep.get("deployer") is None:
            return "UNCONFIRMED", "Token tạo qua factory: ví team không xác định được từ deployer"
        held = dep.get("deployer_holds_pct")
        if not isinstance(held, (int, float)):
            return "UNCONFIRMED", "Deployer không nằm trong top holder; cần xác định ví team khác"
        sent = dep.get("deployer_sent_pct") or 0
        if held > claimed + 0.5:
            return "CONFLICT", f"Deployer đang giữ {held}% > mức team công bố {claimed}%"
        return "LIKELY", (f"Deployer giữ {held}% (đã chuyển đi {sent}%). Không mâu thuẫn với {claimed}%, "
                          "nhưng team có thể dùng ví khác")
    if t == "burn_mechanism":
        sf = fact.get("supply_flows") or {}
        if not sf.get("sample_transfers"):
            return "UNCONFIRMED", "Không đọc được lệnh chuyển (Blockscout không trả dữ liệu): chưa kiểm được"
        if sf.get("burns"):
            return "VERIFIED_ONCHAIN", f"{sf['burns']} lệnh burn từ {sf['unique_burners']} ví trong mẫu {sf['sample_transfers']} lệnh chuyển"
        return "UNCONFIRMED", "Không thấy burn trong mẫu gần nhất (không có nghĩa là không có cơ chế)"
    if t == "fixed_supply":
        ct = fact.get("contract") or {}
        if ct.get("unavailable") or not ct:
            return "UNCONFIRMED", "Không đọc được hợp đồng (Blockscout không trả dữ liệu): chưa kiểm được"
        if any(x.startswith("mint") for x in ct.get("power_functions", [])):
            return "CONFLICT", "Hợp đồng có hàm mint"
        if ct.get("is_verified") and not ct.get("proxy_type"):
            return "VERIFIED_ONCHAIN", "Mã đã verify, không có hàm mint, không phải proxy"
        return "LIKELY" if ct.get("is_verified") else "UNCONFIRMED", "Proxy hoặc chưa verify: nguồn cung có thể đổi qua nâng cấp"
    if t == "lp_locked":
        labels = " ".join((x.get("label") or "") for x in (fact.get("holders") or {}).get("contracts_in_top20", [])).lower()
        if "lock" in labels:
            return "LIKELY", "Có hợp đồng mang nhãn locker trong top holder; cần kiểm tra thời hạn khoá"
        return "UNCONFIRMED", "Không thấy locker trong top holder (với Uniswap v4, LP không nằm ở địa chỉ pool)"
    return cl["status"], cl["detail"] or ""


def cmd_claim(a, con):
    token = a.token.lower()
    if a.action == "add":
        con.execute("INSERT OR IGNORE INTO claims(token, claim, ctype, arg, source_url, ts) VALUES(?,?,?,?,?,?)",
                    (token, a.claim, a.type, a.arg, a.url, time.time()))
    elif a.action == "set":
        con.execute("UPDATE claims SET status=?, detail=?, ts=? WHERE id=?", (a.status, a.detail, time.time(), a.id))
    elif a.action == "verify":
        for cl in con.execute("SELECT * FROM claims WHERE token=?", (token,)).fetchall():
            if cl["ctype"] in AUTO:
                st, det = verify_claim(con, token, cl)
                con.execute("UPDATE claims SET status=?, detail=?, ts=? WHERE id=?", (st, det, time.time(), cl["id"]))
    con.commit()
    rows = con.execute("SELECT id, claim, ctype, arg, source_url, status, detail FROM claims WHERE token=?", (token,)).fetchall()
    print(json.dumps([dict(r) for r in rows], ensure_ascii=False, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("evidence")
    e.add_argument("action", choices=["add", "add-batch", "pending", "done"])
    e.add_argument("--token", required=True)
    e.add_argument("--file"); e.add_argument("--url"); e.add_argument("--text", default="")
    e.add_argument("--source", default="web", choices=["web", "x", "website", "docs", "fomo", "launchpad", "github", "news"])
    e.add_argument("--category", default="event", choices=["identity", "event", "narrative", "claim", "product"])
    e.add_argument("--author"); e.add_argument("--posted-at", dest="posted_at")
    e.add_argument("--limit", type=int, default=40)

    p = sub.add_parser("page")
    p.add_argument("--token", required=True); p.add_argument("--url", required=True)
    p.add_argument("--official", action="store_true", help="đây là website/docs chính thức của dự án")

    b = sub.add_parser("bridge")
    b.add_argument("action", choices=["add", "show"])
    b.add_argument("--token", required=True)
    b.add_argument("--subject", choices=["project", "creator", "wallet"])
    b.add_argument("--entity"); b.add_argument("--type"); b.add_argument("--url"); b.add_argument("--note")

    cl = sub.add_parser("claim")
    cl.add_argument("action", choices=["add", "verify", "set", "show"])
    cl.add_argument("--token", required=True)
    cl.add_argument("--claim"); cl.add_argument("--type", default="other", choices=CLAIM_TYPES); cl.add_argument("--arg")
    cl.add_argument("--url"); cl.add_argument("--id", type=int)
    cl.add_argument("--status", choices=store.LEVELS); cl.add_argument("--detail")

    a = ap.parse_args()
    con = store.connect()
    {"evidence": cmd_evidence, "page": cmd_page, "bridge": cmd_bridge, "claim": cmd_claim}[a.cmd](a, con)


if __name__ == "__main__":
    main()
