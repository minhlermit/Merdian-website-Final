#!/usr/bin/env python3
"""Chế độ KHÁM PHÁ: tìm token đang trending trên Robinhood Chain có liên quan tới tokenized stock.

Nguồn: GeckoTerminal (trending 6h, 24h, pool mới) + DexScreener (mọi pool ghép với stock token chính chủ).
Đầu ra: shortlist xếp theo điểm định lượng nhanh (0-100) kèm cờ rủi ro.

    python3 scripts/discover.py                  # in Markdown
    python3 scripts/discover.py --json out.json  # thêm file JSON cho bước deep dive
    python3 scripts/discover.py --top 15 --include-unrelated
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import datetime, timezone

import common as c

QUOTE_SYMBOLS = {"WETH", "ETH", "USDG", "USDC", "USDT", "USDC.E"}
KEYWORDS = ["stock", "tokenized", "tokenised", "equity", "equities", "dividend", "rwa", "real-world",
            "nasdaq", "wall street", "shares", "etf", "treasury", "nvda", "nvidia", "tsla", "tesla",
            "spcx", "spacex", "aapl", "hims", "stock token", "stock-paired"]


def iso_to_ts(s: str | None) -> float | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def blank(addr: str, symbol: str = "?", name: str = "") -> dict:
    return {"address": addr, "symbol": symbol, "name": name, "pools": [], "paired_with": set(),
            "trending": set(), "websites": [], "x": None, "description": ""}


def add_pool(cands: dict, addr: str, pool: dict):
    cands[addr]["pools"].append(pool)


DEX_PAIR_CAP = 30            # /token-pairs/v1 của DexScreener trả tối đa 30 cặp mỗi token
FAKE_PAIRS: list[dict] = []   # pool có "cổ phiếu" trùng ticker nhưng KHÔNG phải địa chỉ chính chủ


def collect(whitelist: dict[str, str], gt_pages: int) -> dict[str, dict]:
    cands: dict[str, dict] = {}
    tickers = {t.upper() for t in whitelist.values()}

    # 1) GeckoTerminal: trending + mới
    gt_sources = [("trending_pools", "6h"), ("trending_pools", "24h"), ("new_pools", None)]
    for kind, dur in gt_sources:
        for p in c.gt_pools(kind, pages=gt_pages, duration=dur):
            a = p.get("attributes") or {}
            rel = p.get("relationships") or {}
            base, quote = c.gt_addr(rel.get("base_token")), c.gt_addr(rel.get("quote_token"))
            name = a.get("name", "")
            base_sym = name.split("/")[0].strip() if "/" in name else "?"
            quote_sym = name.split("/")[1].strip().upper() if "/" in name else ""
            if quote_sym in tickers and quote not in whitelist and base not in whitelist:
                FAKE_PAIRS.append({"token": base, "symbol": base_sym, "pool": a.get("address"),
                                   "claimed_stock": quote_sym, "quote_addr": quote,
                                   "liq": c.f(a.get("reserve_in_usd"))})
            if base in whitelist or base_sym.upper() in QUOTE_SYMBOLS:
                continue                      # bỏ qua pool mà "base" là chính stock token hay WETH
            cands.setdefault(base, blank(base, base_sym))
            tx24 = ((a.get("transactions") or {}).get("h24")) or {}
            add_pool(cands, base, {
                "src": "gt", "pool": a.get("address"), "name": name,
                "liq": c.f(a.get("reserve_in_usd")), "vol24": c.f((a.get("volume_usd") or {}).get("h24")),
                "vol1": c.f((a.get("volume_usd") or {}).get("h1")),
                "buys24": int(tx24.get("buys") or 0), "sells24": int(tx24.get("sells") or 0),
                "buyers24": tx24.get("buyers"), "sellers24": tx24.get("sellers"),
                "chg24": c.f((a.get("price_change_percentage") or {}).get("h24")),
                "fdv": c.f(a.get("fdv_usd")), "mcap": c.f(a.get("market_cap_usd")),
                "created": iso_to_ts(a.get("pool_created_at")),
                "stock": whitelist.get(quote),
            })
            if quote in whitelist:
                cands[base]["paired_with"].add(whitelist[quote])
            cands[base]["trending"].add(f"{kind.split('_')[0]}{'-' + dur if dur else ''}")

    # 2) DexScreener: mọi pool có một phía là stock token chính chủ
    for addr, ticker in whitelist.items():
        pairs = c.dex_token_pairs(addr)
        if len(pairs) >= DEX_PAIR_CAP:
            c.warn(f"DexScreener chỉ trả {DEX_PAIR_CAP} cặp cho {ticker}: có thể bỏ sót memecoin ghép {ticker} "
                   "(bổ sung bằng GeckoTerminal trending hoặc tìm theo tên)")
        for p in pairs:
            b, q = p.get("baseToken") or {}, p.get("quoteToken") or {}
            ba, qa = (b.get("address") or "").lower(), (q.get("address") or "").lower()
            meme = b if qa in whitelist and ba not in whitelist else q if ba in whitelist and qa not in whitelist else None
            if not meme or (meme.get("symbol") or "").upper() in QUOTE_SYMBOLS:
                continue
            ma = meme["address"].lower()
            cands.setdefault(ma, blank(ma, meme.get("symbol", "?"), meme.get("name", "")))
            cands[ma]["paired_with"].add(ticker)
            tx = (p.get("txns") or {}).get("h24") or {}
            add_pool(cands, ma, {
                "src": "dex", "pool": p.get("pairAddress"), "name": f"{meme.get('symbol')}/{ticker}",
                "dex": p.get("dexId"), "url": p.get("url"),
                "liq": c.f((p.get("liquidity") or {}).get("usd")), "vol24": c.f((p.get("volume") or {}).get("h24")),
                "vol1": c.f((p.get("volume") or {}).get("h1")),
                "buys24": int(tx.get("buys") or 0), "sells24": int(tx.get("sells") or 0),
                "buyers24": None, "sellers24": None,
                "chg24": c.f((p.get("priceChange") or {}).get("h24")),
                "fdv": c.f(p.get("fdv")), "mcap": c.f(p.get("marketCap")),
                "created": (p["pairCreatedAt"] / 1000) if p.get("pairCreatedAt") else None,
                "stock": ticker,
            })
            info = p.get("info") or {}
            _apply_info(cands[ma], info)
    return cands


def _apply_info(cand: dict, info: dict):
    if not cand["websites"]:
        cand["websites"] = [w.get("url") for w in (info.get("websites") or []) if w.get("url")]
    for s in info.get("socials") or []:
        url = s.get("url") or ""
        if (s.get("type") in ("twitter", "x") or "x.com/" in url or "twitter.com/" in url) and not cand["x"]:
            cand["x"] = url
    if not cand["description"]:
        cand["description"] = info.get("description") or ""


def complete_pools(cands: dict, whitelist: dict[str, str], addrs: list[str]):
    """Bổ sung MỌI pool của token (DexScreener), không chỉ pool đang lọt trending.

    Thiếu bước này, thanh khoản tổng của token phụ thuộc pool nào đang trending: pool rớt khỏi trending
    sẽ trông như thanh khoản sụt (LIQUIDITY_COLLAPSE giả). Pool trùng địa chỉ được summarize() gộp.
    """
    for a in addrs:
        for p in c.dex_token_pairs(a):
            b, q = p.get("baseToken") or {}, p.get("quoteToken") or {}
            ba, qa = (b.get("address") or "").lower(), (q.get("address") or "").lower()
            if a not in (ba, qa):
                continue
            me, other = (b, q) if ba == a else (q, b)
            oa = (other.get("address") or "").lower()
            tx = (p.get("txns") or {}).get("h24") or {}
            add_pool(cands, a, {
                "src": "dex", "pool": p.get("pairAddress"), "name": f"{me.get('symbol')}/{other.get('symbol')}",
                "dex": p.get("dexId"), "url": p.get("url"),
                "liq": c.f((p.get("liquidity") or {}).get("usd")), "vol24": c.f((p.get("volume") or {}).get("h24")),
                "vol1": c.f((p.get("volume") or {}).get("h1")),
                "buys24": int(tx.get("buys") or 0), "sells24": int(tx.get("sells") or 0),
                "buyers24": None, "sellers24": None,
                "chg24": c.f((p.get("priceChange") or {}).get("h24")),
                "fdv": c.f(p.get("fdv")), "mcap": c.f(p.get("marketCap")),
                "created": (p["pairCreatedAt"] / 1000) if p.get("pairCreatedAt") else None,
                "stock": whitelist.get(oa),
            })
            if oa in whitelist:
                cands[a]["paired_with"].add(whitelist[oa])
            _apply_info(cands[a], p.get("info") or {})


def enrich_profiles(cands: dict):
    """Lấy website/X/mô tả từ DexScreener cho token chưa có hồ sơ (gộp 30 địa chỉ/lệnh)."""
    need = [a for a, x in cands.items() if not x["websites"] and a.startswith("0x")]
    for p in c.dex_tokens(need):
        a = ((p.get("baseToken") or {}).get("address") or "").lower()
        if a in cands:
            _apply_info(cands[a], p.get("info") or {})
            if cands[a]["name"] == "":
                cands[a]["name"] = (p.get("baseToken") or {}).get("name", "")


def summarize(x: dict) -> dict:
    pools = x["pools"]
    # gộp pool trùng (cùng địa chỉ từ hai nguồn) -> giữ bản có buyers
    uniq: dict[str, dict] = {}
    for p in pools:
        k = (p.get("pool") or "").lower()
        if k not in uniq or (p.get("buyers24") is not None and uniq[k].get("buyers24") is None):
            uniq[k] = p
    pools = list(uniq.values())
    main = max(pools, key=lambda p: p["liq"]) if pools else {}
    liq = sum(p["liq"] for p in pools)
    vol24 = sum(p["vol24"] for p in pools)
    vol1 = sum(p.get("vol1") or 0 for p in pools)
    buys = sum(p["buys24"] for p in pools)
    sells = sum(p["sells24"] for p in pools)
    buyers = sum(p["buyers24"] or 0 for p in pools) if any(p.get("buyers24") is not None for p in pools) else None
    sellers = sum(p["sellers24"] or 0 for p in pools) if any(p.get("sellers24") is not None for p in pools) else None
    created = [p["created"] for p in pools if p.get("created")]
    age_h = (time.time() - min(created)) / 3600 if created else None
    fdv = max((p["fdv"] for p in pools), default=0)
    text = f"{x['name']} {x['symbol']} {x['description']}".lower()
    stock_liq: dict[str, float] = {}
    for p in pools:
        if p.get("stock"):
            stock_liq[p["stock"]] = stock_liq.get(p["stock"], 0.0) + (p["liq"] or 0)
    paired = sorted(t for t, v in stock_liq.items() if v >= c.MIN_STOCK_PAIR_LIQ)
    dust = sorted(t for t, v in stock_liq.items() if v < c.MIN_STOCK_PAIR_LIQ)
    related = bool(paired) or any(k in text for k in KEYWORDS)
    return {
        "address": x["address"], "symbol": x["symbol"], "name": x["name"],
        "link": "paired" if paired else ("keyword" if related else "none"),
        "paired_with": paired, "dust_pairs": dust, "stock_pair_liq": round(sum(stock_liq[t] for t in paired)),
        "trending": sorted(x["trending"]),
        "n_pools": len(pools), "main_pool": main.get("pool"), "main_pool_name": main.get("name"),
        "liq_usd": round(liq), "vol24_usd": round(vol24), "vol1_usd": round(vol1), "turnover24": round(vol24 / liq, 2) if liq else None,
        "buys24": buys, "sells24": sells, "buyers24": buyers, "sellers24": sellers,
        "sell_share": round(sells / (buys + sells), 3) if buys + sells else None,
        "avg_trade_usd": round(vol24 / (buys + sells), 1) if buys + sells else None,
        "chg24_pct": main.get("chg24"), "main_pool_liq": round(main.get("liq") or 0), "fdv_usd": round(fdv), "fdv_to_liq": round(fdv / liq, 1) if liq else None,
        "age_h": round(age_h, 1) if age_h is not None else None,
        "websites": x["websites"][:3], "x": x["x"], "description": x["description"][:300],
    }


def quick_score(s: dict) -> tuple[int, list[str]]:
    """Điểm định lượng nhanh để xếp hạng, KHÔNG phải kết luận đầu tư."""
    score, flags = 0.0, []
    liq = s["liq_usd"] or 0
    score += min(20, max(0, 20 * (math.log10(max(liq, 1)) - 4) / 2))       # 10k$ ->0, 1M$ ->20
    t = s["turnover24"] or 0
    if 0.5 <= t <= 10:
        score += 15
    elif 10 < t <= 40:
        score += 7
    elif t > 40:
        flags.append(f"vòng quay {t:.0f}x/ngày: nghi wash trading")
    part = s["buyers24"] if s["buyers24"] is not None else (s["buys24"] + s["sells24"]) / 4
    score += 20 if part >= 500 else 14 if part >= 200 else 8 if part >= 80 else 3
    ss = s["sell_share"]
    if ss is not None and 0.35 <= ss <= 0.6:
        score += 10
    if s["buys24"] > 50 and s["sells24"] == 0:
        flags.append("có mua không có bán: nghi honeypot")
        score -= 30
    ch = s["chg24_pct"] or 0
    if -20 <= ch <= 300:
        score += 10
    elif ch > 800:
        flags.append(f"đã tăng {ch:.0f}% trong 24h")
    score += {"paired": 15, "keyword": 7, "none": 0}[s["link"]]
    score += 5 if s["websites"] else 0
    score += 5 if s["x"] else 0
    if not s["websites"]:
        flags.append("không có website")
    if s["age_h"] is not None and s["age_h"] < 3:
        flags.append("pool dưới 3 giờ tuổi")
    if s["fdv_to_liq"] and s["fdv_to_liq"] > 50:
        flags.append(f"FDV gấp {s['fdv_to_liq']:.0f} lần thanh khoản: giá dễ bị kéo")
    return max(0, min(100, round(score))), flags


def to_markdown(rows: list[dict]) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    out = [f"# Shortlist Robinhood Chain: tokenized-stock related ({now})", "",
           "| # | Token | Liên kết | Điểm | Thanh khoản | Vol 24h | Vòng quay | Người mua/bán 24h | Tỉ lệ bán | Tuổi (h) | Cờ |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        link = f"paired {','.join(r['paired_with'])}" if r["link"] == "paired" else r["link"]
        bs = f"{r['buyers24']}/{r['sellers24']}" if r["buyers24"] is not None else f"{r['buys24']}/{r['sells24']} lệnh"
        out.append(f"| {i} | {r['symbol']} `{r['address'][:10]}…` | {link} | {r['score']} | {r['liq_usd']:,}$ | "
                   f"{r['vol24_usd']:,}$ | {r['turnover24']} | {bs} | {r['sell_share']} | {r['age_h']} | "
                   f"{'; '.join(r['flags']) or '-'} |")
    if c.WARNINGS:
        out += ["", "**Cảnh báo dữ liệu:**", *[f"- {w}" for w in c.WARNINGS[:15]]]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--gt-pages", type=int, default=2)
    ap.add_argument("--include-unrelated", action="store_true", help="giữ cả token không liên quan cổ phiếu")
    ap.add_argument("--json", help="ghi kết quả đầy đủ ra file JSON")
    args = ap.parse_args()

    wl = c.load_whitelist()
    cands = collect(wl, args.gt_pages)
    enrich_profiles(cands)
    complete_pools(cands, wl, [a for a, x in cands.items() if summarize(x)["link"] != "none"])
    rows = []
    for x in cands.values():
        s = summarize(x)
        if s["link"] == "none" and not args.include_unrelated:
            continue
        s["score"], s["flags"] = quick_score(s)
        rows.append(s)
    rows.sort(key=lambda r: -r["score"])
    rows = rows[: args.top]
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"generated": time.time(), "rows": rows, "warnings": c.WARNINGS}, fh, ensure_ascii=False, indent=1)
    print(to_markdown(rows))
    if not rows and c.WARNINGS:
        sys.exit(2)          # không lấy được dữ liệu: báo cho Claude biết để xử lý mạng


if __name__ == "__main__":
    main()
