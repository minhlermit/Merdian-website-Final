#!/usr/bin/env python3
"""ON-CHAIN AGENT (tất định): bảng dữ kiện cho một token trên Robinhood Chain.

    python3 scripts/onchain.py 0xTOKEN              # in Markdown, lưu vào kho
    python3 scripts/onchain.py 0xTOKEN --json f.json

Gồm: pool/volume theo sàn, tách lợi nhuận meme (R) và cổ phiếu (S), stock token bị khoá,
holder, deployer, hồ sơ hợp đồng (verify, proxy, hàm quyền lực), hoạt động mint/burn,
và module Stock-Pair (stock chính chủ, lệch giá giữa các pool, giờ thị trường Mỹ, issuer mint).
Mọi dữ kiện ở đây mang mức VERIFIED_ONCHAIN hoặc [API]; không có suy luận danh tính.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from datetime import datetime, timezone

import common as c
import store


def pct(a, b):
    return round(100 * (a / b - 1), 2) if a and b else None


# --------------------------------------------------------------------- pools
def pools_for(token: str, wl: dict) -> list[dict]:
    rows: dict[str, dict] = {}
    for p in c.dex_token_pairs(token):
        b, q = p.get("baseToken") or {}, p.get("quoteToken") or {}
        ba, qa = (b.get("address") or "").lower(), (q.get("address") or "").lower()
        if token not in (ba, qa):
            continue
        is_base = ba == token
        other = q if is_base else b
        liq = p.get("liquidity") or {}
        tx = (p.get("txns") or {}).get("h24") or {}
        rows[(p.get("pairAddress") or "").lower()] = {
            "_meta": b if is_base else q,       # tên/ticker dự phòng khi GeckoTerminal lỗi
            "pool": p.get("pairAddress"), "dex": p.get("dexId"), "url": p.get("url"),
            "counter": other.get("symbol"), "counter_addr": (other.get("address") or "").lower(),
            "stock": wl.get((other.get("address") or "").lower()),
            "token_is_base": is_base,
            "liq_usd": c.f(liq.get("usd")),
            "token_in_pool": c.f(liq.get("base") if is_base else liq.get("quote")),
            "counter_in_pool": c.f(liq.get("quote") if is_base else liq.get("base")),
            "vol24": c.f((p.get("volume") or {}).get("h24")), "vol6": c.f((p.get("volume") or {}).get("h6")),
            "vol1": c.f((p.get("volume") or {}).get("h1")),
            "buys24": int(tx.get("buys") or 0), "sells24": int(tx.get("sells") or 0),
            "buyers24": None, "sellers24": None,
            "price_native": c.f(p.get("priceNative")), "price_usd": c.f(p.get("priceUsd")),
            "fdv": c.f(p.get("fdv")), "mcap": c.f(p.get("marketCap")),
            "created": (p["pairCreatedAt"] / 1000) if p.get("pairCreatedAt") else None,
            "info": p.get("info") or {},
        }
    # bổ sung số ví mua/bán duy nhất từ GeckoTerminal
    for g in c.gt_token_pools(token):
        a = g.get("attributes") or {}
        k = (a.get("address") or "").lower()
        tx = ((a.get("transactions") or {}).get("h24")) or {}
        if k in rows:
            rows[k]["buyers24"], rows[k]["sellers24"] = tx.get("buyers"), tx.get("sellers")
            rows[k]["gt_base"] = c.gt_addr((g.get("relationships") or {}).get("base_token"))
    return sorted(rows.values(), key=lambda r: -r["liq_usd"])


def token_usd_and_R(p: dict) -> tuple[float | None, float | None, float | None]:
    """Trả về (P giá USD của token, R = số stock token cho 1 token, S giá USD stock token)."""
    pn, pu = p["price_native"], p["price_usd"]
    if not pn or not pu:
        return None, None, None
    if p["token_is_base"]:
        P, R = pu, pn
        S = P / R
    else:                                   # token là quote: priceUsd là giá của phía còn lại
        S, R = pu, 1 / pn
        P = R * S
    return (P, R, S) if p["stock"] else (P, None, None)


# --------------------------------------------------------------------- price history
def history(pool: dict) -> dict:
    gb = pool.get("gt_base")
    side = "base" if (gb == pool["_token"]) or (not gb and pool["token_is_base"]) else "quote"
    usd = c.gt_ohlcv(pool["pool"], currency="usd", token=side)
    out: dict = {"hours": len(usd)}
    if len(usd) < 25:
        return out
    usd = sorted(usd, key=lambda r: r[0])
    closes = [r[4] for r in usd if r[4]]
    rets = [math.log(b / a) for a, b in zip(closes, closes[1:]) if a and b]
    peak, mdd = closes[0], 0.0
    for x in closes:
        peak = max(peak, x)
        mdd = min(mdd, x / peak - 1)
    out.update(
        P_chg24=pct(closes[-1], closes[-25]), P_chg_window=pct(closes[-1], closes[0]),
        vol_hourly_pct=round(100 * statistics.pstdev(rets), 2) if len(rets) > 2 else None,
        max_drawdown_pct=round(100 * mdd, 1),
        usd_volume_window=round(sum(r[5] for r in usd)),
    )
    if pool.get("stock"):
        tok = sorted(c.gt_ohlcv(pool["pool"], currency="token", token=side), key=lambda r: r[0])
        rc = [r[4] for r in tok if r[4]]
        if len(rc) >= 25:
            r_win, r_24 = rc[-1] / rc[0] - 1, rc[-1] / rc[-25] - 1
            p_win, p_24 = closes[-1] / closes[0] - 1, closes[-1] / closes[-25] - 1
            out.update(
                R_chg24=round(100 * r_24, 2), R_chg_window=round(100 * r_win, 2),
                S_chg24=round(100 * ((1 + p_24) / (1 + r_24) - 1), 2),
                S_chg_window=round(100 * ((1 + p_win) / (1 + r_win) - 1), 2),
            )
    return out


# --------------------------------------------------------------------- holders & deployer
INFRA_LABELS = {"PoolManager", "DopplerHookInitializer", "RehypeDopplerHookInitializer", "UniswapV3Pool",
                "UniswapV2Pair", "PositionManager"}


def holders(token: str, pool_addrs: set[str]) -> dict:
    meta = c.bs_token(token)
    supply = c.f(meta.get("total_supply"))
    count = meta.get("holders_count") or meta.get("holders")
    items = c.bs_holders(token, pages=2)
    rows = []
    for it in items:
        a = it.get("address") or {}
        h = (a.get("hash") or "").lower()
        label = a.get("name") or ""
        # EIP-7702: ví người dùng (EOA) uỷ quyền cho mã smart account; Blockscout báo is_contract=True nhưng vẫn là ví cá nhân
        is_contract = bool(a.get("is_contract")) and a.get("proxy_type") != "eip7702"
        # Uniswap v4 giữ thanh khoản của mọi pool trong PoolManager (pool id không phải địa chỉ);
        # token tự giữ (vesting của launchpad Doppler) và hook khởi tạo của launchpad cũng là hạ tầng
        infra = (h in c.BURN or h in pool_addrs or h == token.lower()
                 or label in INFRA_LABELS or label.endswith("Pool"))
        rows.append({"addr": h, "share": c.f(it.get("value")) / supply if supply else None,
                     "is_contract": is_contract, "label": label or None, "infra": infra})
    real = [r for r in rows if not r["infra"]]
    eoa = [r for r in real if not r["is_contract"]]
    s = lambda xs, n: round(100 * sum((r["share"] or 0) for r in xs[:n]), 2) if xs else None
    burned = round(100 * sum((r["share"] or 0) for r in rows if r["addr"] in c.BURN), 2)
    return {
        "total_supply_raw": meta.get("total_supply"), "decimals": meta.get("decimals"),
        "exchange_rate": c.f(meta.get("exchange_rate"), None),
        "holders_count": int(count) if str(count or "").isdigit() else count,
        "top10_all_pct": s(rows, 10), "top10_ex_infra_pct": s(real, 10), "top10_eoa_pct": s(eoa, 10),
        "largest_eoa_pct": s(eoa, 1), "burned_pct": burned,
        "contracts_in_top20": [{"addr": r["addr"], "label": r["label"], "pct": round(100 * (r["share"] or 0), 2)}
                               for r in rows[:20] if r["is_contract"]],
        "_rows": rows,
    }


def deployer(token: str, supply: float, top_rows: list[dict]) -> dict:
    info = c.bs_address(token)
    dep = (info.get("creator_address_hash") or "").lower()
    if not dep:
        return {"deployer": None, "note": "Blockscout không trả về creator"}
    dinfo = c.bs_address(dep)
    out = {"deployer": dep, "deployer_is_contract": bool(dinfo.get("is_contract")),
           "deployer_label": dinfo.get("name"), "creation_tx": info.get("creation_tx_hash")}
    if out["deployer_is_contract"]:
        out["note"] = ("Token được tạo qua hợp đồng factory (thường là launchpad). Ví 'creator' thật phải lấy từ "
                       "trang launchpad hoặc sự kiện tạo token; ví deployer không phải team.")
        return out
    held = next((r["share"] for r in top_rows if r["addr"] == dep), None)
    outs = c.bs_transfers_from(dep, token, pages=2)
    sent = sum(c.f((t.get("total") or {}).get("value")) for t in outs)
    recips = {((t.get("to") or {}).get("hash") or "").lower() for t in outs}
    out.update(
        deployer_holds_pct=round(100 * held, 2) if held is not None else "ngoài top 100",
        deployer_sent_pct=round(100 * sent / supply, 2) if supply else None,
        deployer_out_transfers=len(outs), deployer_distinct_recipients=len(recips),
    )
    return out


# --------------------------------------------------------------------- stock float
def stock_float(pool: dict) -> dict | None:
    if not pool.get("stock"):
        return None
    meta = c.bs_token(pool["counter_addr"])
    dec = int(meta.get("decimals") or 18)
    supply = c.f(meta.get("total_supply")) / 10 ** dec
    locked = pool["counter_in_pool"]
    return {"stock": pool["stock"], "stock_in_pool": round(locked, 4), "stock_supply_onchain": round(supply, 2),
            "share_of_supply_pct": round(100 * locked / supply, 3) if supply else None}


# --------------------------------------------------------------------- contract & supply flows
POWER_FUNCS = {
    "mint": "owner/role có thể in thêm token",
    "pause": "có thể tạm dừng chuyển token",
    "blacklist": "có thể chặn ví", "blocklist": "có thể chặn ví", "addbot": "có thể gắn cờ ví là bot",
    "settax": "có thể đổi thuế giao dịch", "setfee": "có thể đổi phí", "setbuyfee": "có thể đổi phí mua",
    "setsellfee": "có thể đổi phí bán", "setmaxtx": "có thể giới hạn kích thước lệnh",
    "setmaxwallet": "có thể giới hạn ví", "upgradeto": "hợp đồng nâng cấp được",
    "excludefromfee": "có thể miễn phí cho ví chọn lọc",
}


def contract_profile(token: str) -> dict:
    a = c.bs_address(token)
    if not a:
        return {"is_verified": None, "proxy_type": None, "implementations": [], "power_functions": [],
                "has_owner": None, "renounce_available": None, "unavailable": True,
                "note": "Không đọc được hợp đồng: Blockscout không trả dữ liệu (không phải kết luận về hợp đồng)."}
    out = {"is_verified": a.get("is_verified"), "proxy_type": a.get("proxy_type"),
           "implementations": [i.get("address") or i.get("address_hash") for i in (a.get("implementations") or [])],
           "power_functions": [], "has_owner": None, "renounce_available": None}
    target = out["implementations"][0] if out["implementations"] else token
    if not out["is_verified"] and not out["implementations"]:
        out["note"] = "Mã nguồn chưa verify trên Blockscout: không đọc được quyền của hợp đồng."
        return out
    sc = c.bs_smart_contract(target)
    names = {(f.get("name") or "").lower() for f in (sc.get("abi") or []) if f.get("type") == "function"}
    for n in sorted(names):
        for k, why in POWER_FUNCS.items():
            if n == k or n.startswith(k):
                out["power_functions"].append(f"{n}(): {why}")
                break
    out["has_owner"] = "owner" in names
    out["renounce_available"] = "renounceownership" in names
    out["compiler"] = sc.get("compiler_version")
    return out


def supply_flows(token: str, supply_raw: float) -> dict:
    """Mẫu các lệnh chuyển gần nhất: mint (từ 0x0), burn (tới 0x0/dead), số ví đốt duy nhất."""
    items = c.bs_token_transfers(token, pages=3)
    mints = burns = 0
    burn_amt = mint_amt = 0.0
    burners = set()
    ts = [t.get("timestamp") for t in items if t.get("timestamp")]
    for t in items:
        fr = ((t.get("from") or {}).get("hash") or "").lower()
        to = ((t.get("to") or {}).get("hash") or "").lower()
        v = c.f((t.get("total") or {}).get("value"))
        if fr == c.BURN_ZERO:
            mints += 1
            mint_amt += v
        if to in c.BURN:
            burns += 1
            burn_amt += v
            burners.add(fr)
    return {"sample_transfers": len(items), "sample_from": min(ts) if ts else None, "sample_to": max(ts) if ts else None,
            "mints": mints, "mint_pct_supply": round(100 * mint_amt / supply_raw, 4) if supply_raw else None,
            "burns": burns, "burn_pct_supply": round(100 * burn_amt / supply_raw, 4) if supply_raw else None,
            "unique_burners": len(burners),
            "note": "Chỉ là mẫu tối đa 150 lệnh chuyển gần nhất, không phải toàn bộ lịch sử."}


# --------------------------------------------------------------------- stock-pair module
def us_market_open(t: float | None = None) -> bool:
    """Phiên chính NYSE/Nasdaq 9:30-16:00 giờ New York, thứ 2-6. Không tính ngày lễ."""
    from zoneinfo import ZoneInfo
    now = datetime.fromtimestamp(t or time.time(), tz=ZoneInfo("America/New_York"))
    if now.weekday() >= 5:
        return False
    mins = now.hour * 60 + now.minute
    return 9 * 60 + 30 <= mins < 16 * 60


def stock_pair_module(pool: dict, S_implied: float | None) -> dict:
    stock_addr = pool["counter_addr"]
    out = {"stock": pool["stock"], "canonical": True, "stock_contract": stock_addr,
           "us_market_open_now": us_market_open()}
    # giá stock token ở pool sâu nhất với stablecoin trên chain
    best = None
    for p in c.dex_token_pairs(stock_addr):
        b, q = p.get("baseToken") or {}, p.get("quoteToken") or {}
        syms = {(b.get("symbol") or "").upper(), (q.get("symbol") or "").upper()}
        if syms & {"USDG", "USDC", "USDT"}:
            liq = c.f((p.get("liquidity") or {}).get("usd"))
            if not best or liq > best[1]:
                is_base = (b.get("address") or "").lower() == stock_addr
                px = c.f(p.get("priceUsd")) if is_base else (1 / c.f(p.get("priceNative"), 0) if c.f(p.get("priceNative")) else None)
                best = (px, liq, p.get("pairAddress"))
    if best and best[0] and S_implied:
        out.update(S_stable_pool=round(best[0], 4), stable_pool_liq=round(best[1]), stable_pool=best[2],
                   implied_vs_stable_pool_pct=round(100 * (S_implied / best[0] - 1), 3))
    else:
        out["note_price"] = "Không tìm thấy pool stock/stablecoin để so; giá tham chiếu Chainlink là bước nâng cấp."
    flows = supply_flows(stock_addr, 0)
    out["issuer_mints_in_sample"] = flows["mints"]
    out["issuer_burns_in_sample"] = flows["burns"]
    out["reminder"] = ("Ghép cặp KHÔNG phải bảo chứng. Stock Token là chứng khoán nợ do Robinhood Assets (Jersey) phát hành: "
                       "rủi ro đối tác phát hành, không có quyền cổ đông.")
    return out


# --------------------------------------------------------------------- report
PRICE_CONFLICT_PCT = 20.0


def cross_check_price(p_dex, p_bs) -> dict | None:
    """So giá DexScreener với tỉ giá Blockscout. Lệch lớn thường do một nguồn trễ (cache) hoặc pool lệch giá."""
    if not p_dex or not p_bs:
        return None
    diff = round(100 * (p_dex / p_bs - 1), 1)
    return {"dexscreener": p_dex, "blockscout": p_bs, "diff_pct": diff, "conflict": abs(diff) > PRICE_CONFLICT_PCT}


def build(token: str) -> dict:
    token = token.lower()
    wl = c.load_whitelist()
    pools = pools_for(token, wl)
    for p in pools:
        p["_token"] = token
    main = pools[0] if pools else None
    stock_main = next((p for p in pools if p["stock"]), None)
    ref = stock_main or main
    P = R = S = None
    if ref:
        P, R, S = token_usd_and_R(ref)
    liq = sum(p["liq_usd"] for p in pools)
    vol24 = sum(p["vol24"] for p in pools)
    buys, sells = sum(p["buys24"] for p in pools), sum(p["sells24"] for p in pools)
    gt_info = c.gt_token_info(token)
    h = holders(token, {(p["pool"] or "").lower() for p in pools})
    gth = gt_info.get("holders") or {}
    if not isinstance(h.get("holders_count"), int) and gth.get("count"):
        # Blockscout lỗi (ví dụ Cloudflare chặn IP máy chủ): dùng số liệu GeckoTerminal, ghi rõ nguồn.
        # top_10 của GeckoTerminal gồm cả pool và hợp đồng, nên KHÔNG điền vào top10_eoa_pct.
        h["holders_count"] = int(gth["count"])
        h["top10_all_pct"] = c.f((gth.get("distribution_percentage") or {}).get("top_10"), None)
        h["source"] = "geckoterminal"
    dep = deployer(token, c.f(h.get("total_supply_raw")), h.get("_rows", []))
    price_check = cross_check_price(P, h.get("exchange_rate"))
    if price_check and price_check["conflict"]:
        c.warn(f"Giá lệch {price_check['diff_pct']}% giữa DexScreener (${P:.6g}) và tỉ giá Blockscout "
               f"(${h['exchange_rate']:.6g}): số liệu giá cần kiểm lại")
    created = [p["created"] for p in pools if p.get("created")]
    info = (main or {}).get("info") or {}
    tickers = {t.upper() for t in wl.values()}
    fake_pairs = [{"pool": p["pool"], "claimed_stock": (p["counter"] or "").upper(), "counter_addr": p["counter_addr"],
                   "liq_usd": round(p["liq_usd"])}
                  for p in pools if not p["stock"] and (p["counter"] or "").upper() in tickers]
    report = {
        "token": token, "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        # GeckoTerminal có thể trả 429: lấy tên/ticker dự phòng từ DexScreener
        "name": gt_info.get("name") or next((p["_meta"].get("name") for p in pools
                                             if isinstance(p.get("_meta"), dict) and p["_meta"].get("name")), None),
        "symbol": gt_info.get("symbol") or next((p["_meta"].get("symbol") for p in pools
                                                 if isinstance(p.get("_meta"), dict) and p["_meta"].get("symbol")), None),
        "profile": {
            "websites": gt_info.get("websites") or [w.get("url") for w in info.get("websites") or []],
            "x": gt_info.get("twitter_handle") or next((s.get("url") for s in info.get("socials") or []
                                                        if s.get("type") in ("twitter", "x")), None),
            "telegram": gt_info.get("telegram_handle"), "description": (gt_info.get("description") or info.get("description") or "")[:600],
            "gt_score": gt_info.get("gt_score"), "gt_holders": gt_info.get("holders"),
            "image_url": gt_info.get("image_url") or info.get("imageUrl"),
        },
        "market": {
            "price_usd": P, "R_stock_per_token": R, "S_stock_usd": S, "reference_pool_stock": (ref or {}).get("stock"),
            "liq_total_usd": round(liq), "vol24_total_usd": round(vol24),
            "turnover24": round(vol24 / liq, 2) if liq else None,
            "vol_share_main_pool_pct": round(100 * main["vol24"] / vol24, 1) if main and vol24 else None,
            "buys24": buys, "sells24": sells, "sell_share": round(sells / (buys + sells), 3) if buys + sells else None,
            "avg_trade_usd": round(vol24 / (buys + sells), 1) if buys + sells else None,
            "fdv_usd": round(max((p["fdv"] for p in pools), default=0)),
            "fdv_to_liq": round(max((p["fdv"] for p in pools), default=0) / liq, 1) if liq else None,
            "age_days": round((time.time() - min(created)) / 86400, 1) if created else None,
            "price_check": price_check,
            "vol_accel_1h_vs_24h_avg": round(sum(p["vol1"] for p in pools) / (vol24 / 24), 2) if vol24 else None,
        },
        # 8 pool lớn nhất + mọi pool ghép stock token: claim paired_with được đối chiếu trên danh sách này
        "pools": [{k: v for k, v in p.items() if k not in ("info", "_token", "_meta")}
                  for p in pools[:8] + [q for q in pools[8:] if q.get("stock")]],
        "history_7d": history(ref) if ref else {},
        "stock_float": stock_float(stock_main) if stock_main else None,
        "holders": {k: v for k, v in h.items() if not k.startswith("_")},
        "holder_growth": None,
        "deployer": dep,
        "contract": contract_profile(token),
        "supply_flows": supply_flows(token, c.f(h.get("total_supply_raw"))),
        "stock_pair": stock_pair_module(stock_main, S) if stock_main else None,
        "suspected_fake_stock_pairs": fake_pairs,
        "warnings": c.WARNINGS,
    }
    con = store.connect()
    prev, prev_ts = store.latest_fact(con, token, "onchain")
    if prev and isinstance(prev.get("holders", {}).get("holders_count"), int) and isinstance(h.get("holders_count"), int):
        days = max((time.time() - prev_ts) / 86400, 1 / 24)
        hc0, hc1 = prev["holders"]["holders_count"], h["holders_count"]
        report["holder_growth"] = {"since_hours": round(days * 24, 1), "holders_delta": hc1 - hc0,
                                   "holders_per_day": round((hc1 - hc0) / days, 1),
                                   "top10_eoa_change_pp": round((h.get("top10_eoa_pct") or 0) - (prev["holders"].get("top10_eoa_pct") or 0), 2)}
    store.save_fact(con, token, "onchain", report)
    con.execute("UPDATE snapshots SET holders=?, top10_eoa=? WHERE id=(SELECT id FROM snapshots WHERE token=? ORDER BY ts DESC LIMIT 1)",
                (h.get("holders_count") if isinstance(h.get("holders_count"), int) else None, h.get("top10_eoa_pct"), token))
    con.commit()
    return report


def md(r: dict) -> str:
    m, h, d, hi = r["market"], r["holders"], r["deployer"], r["history_7d"]
    L = [f"# Fact sheet: {r['symbol']} ({r['token']})", f"*{r['generated_utc']} UTC*", "",
         "## Thị trường",
         f"- Giá: {(m['price_usd'] or 0):.6g} USD | Thanh khoản tổng: {m['liq_total_usd']:,} USD | Vol 24h: {m['vol24_total_usd']:,} USD",
         f"- Vòng quay 24h: {m['turnover24']}x | Tỉ lệ bán: {m['sell_share']} | Lệnh TB: {m['avg_trade_usd']} USD",
         f"- FDV: {m['fdv_usd']:,} USD | FDV/thanh khoản: {m['fdv_to_liq']}x | Tuổi: {m['age_days']} ngày",
         f"- Tăng tốc volume (1h so với TB giờ của 24h): {m['vol_accel_1h_vs_24h_avg']}x"]
    if m["R_stock_per_token"]:
        L.append(f"- Cặp tham chiếu: {m['reference_pool_stock']} | R = {m['R_stock_per_token']:.6g} stock/token | S = {m['S_stock_usd']:.2f} USD")
    L += ["", "## Pool", "| Sàn | Cặp với | Thanh khoản | Vol 24h | Ví mua/bán | Lệnh mua/bán |", "|---|---|---|---|---|---|"]
    for p in r["pools"]:
        L.append(f"| {p['dex']} | {p['counter']}{' (stock)' if p['stock'] else ''} | {p['liq_usd']:,.0f} | "
                 f"{p['vol24']:,.0f} | {p['buyers24']}/{p['sellers24']} | {p['buys24']}/{p['sells24']} |")
    if hi:
        L += ["", "## Lịch sử 7 ngày (theo giờ, pool tham chiếu)", f"- Giá USD: 24h {hi.get('P_chg24')}% | cả kỳ {hi.get('P_chg_window')}% | "
              f"drawdown lớn nhất {hi.get('max_drawdown_pct')}% | biến động giờ {hi.get('vol_hourly_pct')}%"]
        if "R_chg_window" in hi:
            L.append(f"- Tách lợi nhuận cả kỳ: phần meme (R) {hi['R_chg_window']}% | phần cổ phiếu (S) {hi['S_chg_window']}%")
    if r["stock_float"]:
        sf = r["stock_float"]
        L.append(f"- Stock token {sf['stock']} bị khoá trong pool: {sf['stock_in_pool']} / {sf['stock_supply_onchain']} "
                 f"({sf['share_of_supply_pct']}% nguồn cung on-chain)")
    L += ["", "## Holder",
          f"- Số holder: {h.get('holders_count')} | Top 10 (trừ pool/burn): {h.get('top10_ex_infra_pct')}% | "
          f"Top 10 ví thường: {h.get('top10_eoa_pct')}% | Ví thường lớn nhất: {h.get('largest_eoa_pct')}% | Đã burn: {h.get('burned_pct')}%"]
    for x in h.get("contracts_in_top20", [])[:6]:
        L.append(f"  - Hợp đồng trong top 20: {x['label'] or x['addr'][:12]} ({x['pct']}%)")
    if r["holder_growth"]:
        g = r["holder_growth"]
        L.append(f"- So với lần chạy trước ({g['since_hours']}h): holder {g['holders_delta']:+} ({g['holders_per_day']}/ngày), "
                 f"top 10 ví thường thay đổi {g['top10_eoa_change_pp']:+} điểm %")
    L += ["", "## Deployer", f"- Địa chỉ: {d.get('deployer')} | Là hợp đồng: {d.get('deployer_is_contract')} {d.get('deployer_label') or ''}"]
    if d.get("note"):
        L.append(f"- {d['note']}")
    if "deployer_holds_pct" in d:
        L.append(f"- Đang giữ: {d['deployer_holds_pct']}% | Đã chuyển đi: {d['deployer_sent_pct']}% qua "
                 f"{d['deployer_out_transfers']} lệnh tới {d['deployer_distinct_recipients']} ví")
    ct = r.get("contract") or {}
    L += ["", "## Hợp đồng", f"- Verify: {ct.get('is_verified')} | Proxy: {ct.get('proxy_type') or 'không'} | Có owner: {ct.get('has_owner')} | "
          f"Có renounceOwnership: {ct.get('renounce_available')}"]
    L += [f"  - {x}" for x in ct.get("power_functions", [])] or []
    if ct.get("note"):
        L.append(f"- {ct['note']}")
    sf2 = r.get("supply_flows") or {}
    if sf2:
        L.append(f"- Mint/burn trong mẫu {sf2['sample_transfers']} lệnh chuyển: mint {sf2['mints']} ({sf2['mint_pct_supply']}% cung), "
                 f"burn {sf2['burns']} ({sf2['burn_pct_supply']}% cung), {sf2['unique_burners']} ví đốt duy nhất")
    sp = r.get("stock_pair")
    if sp:
        L += ["", "## Stock-Pair", f"- {sp['stock']} chính chủ: {sp['canonical']} | Thị trường Mỹ đang mở: {sp['us_market_open_now']}"]
        if "implied_vs_stable_pool_pct" in sp:
            L.append(f"- Giá {sp['stock']} ngầm định trong pool meme lệch {sp['implied_vs_stable_pool_pct']}% so với pool "
                     f"{sp['stock']}/stablecoin sâu nhất (thanh khoản {sp['stable_pool_liq']:,} USD)")
        L.append(f"- Issuer mint/burn stock token trong mẫu: {sp['issuer_mints_in_sample']}/{sp['issuer_burns_in_sample']}")
    for fp in r.get("suspected_fake_stock_pairs") or []:
        L.append(f"- CẢNH BÁO: pool {fp['pool']} ghép với token tên {fp['claimed_stock']} nhưng địa chỉ "
                 f"{fp['counter_addr']} KHÔNG nằm trong danh sách stock token chính chủ")
    pr = r["profile"]
    L += ["", "## Hồ sơ", f"- Website: {', '.join(pr['websites'] or []) or 'không có'} | X: {pr['x'] or 'không có'} | GT score: {pr['gt_score']}",
          f"- Mô tả: {pr['description'] or '-'}"]
    if r["warnings"]:
        L += ["", "## Cảnh báo dữ liệu", *[f"- {w}" for w in r["warnings"][:15]]]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("token")
    ap.add_argument("--json")
    a = ap.parse_args()
    r = build(a.token)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(r, fh, ensure_ascii=False, indent=1, default=str)
    print(md(r))


if __name__ == "__main__":
    main()
