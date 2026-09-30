#!/usr/bin/env python3
"""DỮ LIỆU TẢI HỘ: khi script không gọi thẳng được API (proxy, Cloudflare, app Claude chặn domain).

Agent tải dữ liệu bằng công cụ của mình (web fetch cho DexScreener, Blockscout MCP cho Blockscout) rồi lưu
vào ~/.stock-token-scout/fetched/ bằng lệnh dưới đây. Các script khác đọc lại như phản hồi API thật, nên
pipeline, luật chấm và báo cáo HTML chạy y nguyên. Quy trình đầy đủ: references/data_fallback.md.

    python3 fetched.py missing                      # URL script cần mà chưa có, kèm cách tải
    python3 fetched.py missing --clear              # xoá danh sách sau khi đã tải xong
    python3 fetched.py put --url URL --file resp.json          # lưu JSON thô
    python3 fetched.py put-dex --url URL --file pairs.txt      # lưu cặp DexScreener dạng dòng rút gọn
    python3 fetched.py put-holders --token 0xT --file h.txt    # lưu top holder Blockscout dạng dòng rút gọn
    python3 fetched.py put-token --token 0xT --supply RAW --holders N [--decimals 18] [--exchange-rate X]
    python3 fetched.py status

Dòng rút gọn DexScreener (một cặp mỗi dòng, 22 trường, phân cách bằng |, trường thiếu để trống):
    pairAddress|dexId|base.address|base.symbol|base.name|quote.address|quote.symbol|liquidity.usd|
    liquidity.base|liquidity.quote|volume.h24|volume.h6|volume.h1|txns.h24.buys|txns.h24.sells|
    priceChange.h24|fdv|pairCreatedAt|priceUsd|priceNative|website|twitter
Dòng rút gọn holder: address|is_contract(0/1)|proxy_type|name|value_raw
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import OrderedDict

import common as c

DEX_FIELDS = 22


def _num(x):
    try:
        return float(x) if str(x).strip() not in ("", "None", "null") else None
    except ValueError:
        return None


def dex_line_to_pair(line: str) -> dict:
    f = [x.strip() for x in line.split("|")]
    if len(f) < 20:
        raise ValueError(f"dòng DexScreener cần ít nhất 20 trường, có {len(f)}: {line[:80]}")
    f += [""] * (DEX_FIELDS - len(f))
    (pool, dex, ba, bs, bn, qa, qs, liq, lb, lq, v24, v6, v1, buys, sells, chg, fdv, created, pu, pn, web, x) = f[:DEX_FIELDS]
    p = {"chainId": "robinhood", "dexId": dex, "url": f"https://dexscreener.com/robinhood/{pool.lower()}",
         "pairAddress": pool, "baseToken": {"address": ba, "symbol": bs, "name": bn},
         "quoteToken": {"address": qa, "symbol": qs, "name": qs}, "priceUsd": pu, "priceNative": pn,
         "txns": {"h24": {"buys": int(_num(buys) or 0), "sells": int(_num(sells) or 0)}},
         "volume": {"h24": _num(v24) or 0, "h6": _num(v6) or 0, "h1": _num(v1) or 0},
         "priceChange": {"h24": _num(chg)} if _num(chg) is not None else {},
         "liquidity": {"usd": _num(liq), "base": _num(lb), "quote": _num(lq)},
         "fdv": _num(fdv), "marketCap": _num(fdv),
         "info": {"websites": [{"url": web}] if web else [],
                  "socials": [{"type": "twitter", "url": x}] if x else []}}
    if _num(created):
        p["pairCreatedAt"] = int(_num(created))
    return p


def holder_line(line: str) -> dict:
    f = [x.strip() for x in line.split("|")]
    if len(f) != 5:
        raise ValueError(f"dòng holder cần 5 trường: {line[:80]}")
    h, ic, px, name, val = f
    return {"address": {"hash": h, "is_contract": ic == "1", "proxy_type": px or None, "name": name or None},
            "value": val}


def _lines(path: str) -> list[str]:
    text = sys.stdin.read() if path == "-" else open(path, encoding="utf-8").read()
    return [l for l in (x.strip().strip("`") for x in text.splitlines()) if l.startswith("0x")]


def hint(url: str) -> str:
    u = url.lower()
    if "dexscreener" in u:
        return "web fetch URL này; lưu bằng put-dex (dòng rút gọn) hoặc put (JSON thô)"
    if "blockscout" in u:
        path = u.split("/api/v2", 1)[-1].split("?")[0]
        return f"Blockscout MCP direct_api_call chain 4663, endpoint /api/v2{path}; holder → put-holders, token → put-token"
    if "geckoterminal" in u:
        return "thường bị chặn (robots); bỏ qua được: thiếu lịch sử 7 ngày, báo cáo sẽ ghi rõ"
    return "web fetch rồi put"


def cmd_missing(a):
    p = c.CACHE_DIR / "missing_urls.txt"
    urls = list(OrderedDict.fromkeys(l.strip() for l in p.read_text(encoding="utf-8").splitlines() if l.strip())) \
        if p.exists() else []
    urls = [u for u in urls if c.read_fetched(u) is None]
    if a.clear and p.exists():
        p.unlink()
    opt = set(OrderedDict.fromkeys(l.strip() for l in (c.CACHE_DIR / "missing_optional.txt").read_text(encoding="utf-8").splitlines())) \
        if (c.CACHE_DIR / "missing_optional.txt").exists() else set()
    required = [u for u in urls if u not in opt]
    optional = [u for u in opt if c.read_fetched(u) is None]
    if a.clear and (c.CACHE_DIR / "missing_optional.txt").exists():
        (c.CACHE_DIR / "missing_optional.txt").unlink()
    out = {}
    for u in required:
        out.setdefault(c._host(u), []).append({"url": u, "how": hint(u)})
    print(json.dumps({"missing": len(required), "by_host": out,
                      "optional": {"count": len(optional),
                                   "note": "pool/hồ sơ bổ sung của ứng viên: chỉ tải cho token trong hàng đợi "
                                           "(onchain.py sẽ đòi), không cần tải hết",
                                   "urls": optional[:50]}}, ensure_ascii=False, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("missing"); m.add_argument("--clear", action="store_true")
    p = sub.add_parser("put"); p.add_argument("--url", required=True); p.add_argument("--file", required=True)
    d = sub.add_parser("put-dex"); d.add_argument("--url", required=True); d.add_argument("--file", required=True)
    h = sub.add_parser("put-holders"); h.add_argument("--token", required=True); h.add_argument("--file", required=True)
    t = sub.add_parser("put-token"); t.add_argument("--token", required=True); t.add_argument("--supply", required=True)
    t.add_argument("--holders", required=True); t.add_argument("--decimals", default="18")
    t.add_argument("--exchange-rate")
    sub.add_parser("status")
    a = ap.parse_args()

    if a.cmd == "missing":
        cmd_missing(a)
    elif a.cmd == "put":
        text = sys.stdin.read() if a.file == "-" else open(a.file, encoding="utf-8").read()
        c.save_fetched(a.url, json.loads(text))
        print(json.dumps({"saved": a.url}))
    elif a.cmd == "put-dex":
        pairs = [dex_line_to_pair(l) for l in _lines(a.file)]
        c.save_fetched(a.url, pairs, "agent:dex-lines")
        print(json.dumps({"saved": a.url, "pairs": len(pairs),
                          "note": "DexScreener trả tối đa 30 cặp mỗi token" if len(pairs) >= 30 else ""}, ensure_ascii=False))
    elif a.cmd == "put-holders":
        items = [holder_line(l) for l in _lines(a.file)]
        c.save_fetched(f"{c.BS}/tokens/{a.token.lower()}/holders", {"items": items, "next_page_params": None},
                       "agent:blockscout-mcp")
        print(json.dumps({"saved": "holders", "token": a.token.lower(), "items": len(items)}))
    elif a.cmd == "put-token":
        d = {"total_supply": a.supply, "decimals": a.decimals, "holders_count": a.holders}
        if a.exchange_rate:
            d["exchange_rate"] = a.exchange_rate
        c.save_fetched(f"{c.BS}/tokens/{a.token.lower()}", d, "agent:blockscout-mcp")
        print(json.dumps({"saved": "token", "token": a.token.lower()}))
    elif a.cmd == "status":
        files = sorted((c.CACHE_DIR / "fetched").glob("*.json")) if (c.CACHE_DIR / "fetched").exists() else []
        rows = []
        for f in files:
            d = json.loads(f.read_text(encoding="utf-8"))
            rows.append({"url": d["url"], "source": d.get("source"), "age_h": round((time.time() - d["saved_at"]) / 3600, 1)})
        print(json.dumps({"fetched": len(rows), "items": rows}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
