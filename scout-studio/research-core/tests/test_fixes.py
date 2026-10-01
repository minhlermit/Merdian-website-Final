"""Kiểm thử các lỗi phát hiện khi chạy thật trên Robinhood Chain (không cần mạng): python3 tests/test_fixes.py"""
import os, sys, io, time, tempfile, pathlib, urllib.error, urllib.request
os.environ["STS_CACHE_DIR"] = tempfile.mkdtemp(prefix="sts_fix_")
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude/skills/stock-token-scout/scripts"))
import common as c  # noqa: E402
import discover  # noqa: E402
import ledger  # noqa: E402
import store  # noqa: E402


_n = iter(range(1, 10_000))


def pool(liq, stock=None, created=None):
    return {"pool": f"0x{next(_n):040x}", "liq": liq, "vol24": 0, "vol1": 0, "buys24": 0, "sells24": 0,
            "buyers24": None, "sellers24": None, "fdv": 0, "chg24": 0, "created": created, "stock": stock}


def cand(pools, name="Token", desc=""):
    x = discover.blank("0x" + "1" * 40, "TKN", name)
    x["pools"], x["description"] = pools, desc
    return x


# 1. Pool bụi (PONS/SPY $477, DELTA/AAPL $7) không biến token thành "ghép cổ phiếu"
s = discover.summarize(cand([pool(7_000_000), pool(477, "SPY"), pool(982, "QQQ")]))
assert s["link"] == "none" and s["paired_with"] == [] and s["dust_pairs"] == ["QQQ", "SPY"], s
s = discover.summarize(cand([pool(7_000_000), pool(7, "AAPL")], desc="tokenized stock liquidity"))
assert s["link"] == "keyword", s                       # vẫn liên quan qua từ khoá, nhưng không phải "paired"
s = discover.summarize(cand([pool(2_000_000), pool(3_000, "NVDA"), pool(3_000, "NVDA"), pool(20_000, "TSLA")]))
assert s["link"] == "paired" and s["paired_with"] == ["NVDA", "TSLA"] and s["stock_pair_liq"] == 26_000, s

# 2. Cloudflare 403: cảnh báo một lần, sau đó bỏ qua host (không gọi lại)
calls = {"n": 0}


def cf_403(req, timeout=20):
    calls["n"] += 1
    raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {"cf-mitigated": "challenge"},
                                 io.BytesIO(b"<title>Just a moment...</title>"))


real = urllib.request.urlopen
urllib.request.urlopen = cf_403
c._MIN_GAP.clear()
assert c.get_json("https://robinhoodchain.blockscout.com/api/v2/tokens/0xa") is None
assert c.get_json("https://robinhoodchain.blockscout.com/api/v2/tokens/0xb") is None
assert calls["n"] == 1 and "robinhoodchain.blockscout.com" in c.BLOCKED_HOSTS
assert sum("Cloudflare" in w for w in c.WARNINGS) == 1

# 3. HTTP 429 tôn trọng Retry-After rồi thử lại
seq = iter([urllib.error.HTTPError("u", 429, "Too Many", {"Retry-After": "0"}, io.BytesIO(b"")), None])


class Resp(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): return False


def rl(req, timeout=20):
    e = next(seq)
    if e:
        raise e
    return Resp(b'{"ok": 1}')


urllib.request.urlopen = rl
assert c.get_json("https://api.geckoterminal.com/api/v2/x") == {"ok": 1}
urllib.request.urlopen = real

# 4. Hợp đồng không đọc được → claim nói rõ "chưa kiểm được", không nói "proxy hoặc chưa verify"
con = store.connect()
T = "0x" + "2" * 40
store.save_fact(con, T, "onchain", {"contract": {"unavailable": True}, "supply_flows": {"sample_transfers": 0}})
st, why = ledger.verify_claim(con, T, {"ctype": "fixed_supply", "arg": ""})
assert st == "UNCONFIRMED" and "Không đọc được hợp đồng" in why, why
st, why = ledger.verify_claim(con, T, {"ctype": "burn_mechanism", "arg": ""})
assert st == "UNCONFIRMED" and "Không đọc được lệnh chuyển" in why, why

# 5. Hàng đợi: cùng mức nghiêm trọng thì token điểm cao đứng trước, dù event ghi sau
now = time.time()
for addr, sym, score, ev_ts in (("0x" + "a" * 40, "HI", 95, now - 100), ("0x" + "b" * 40, "LO", 40, now)):
    con.execute("INSERT INTO tokens(address, symbol) VALUES(?,?)", (addr, sym))
    con.execute("INSERT INTO snapshots(token, ts, liq, score) VALUES(?,?,?,?)", (addr, now, 1e5, score))
    con.execute("INSERT INTO events(token, ts, type, severity, detail) VALUES(?,?,?,?,?)", (addr, ev_ts, "X", 2, "{}"))
con.commit()
order = [r["symbol"] for r in con.execute(
    "SELECT e.token, t.symbol, MAX(e.severity) sev FROM events e JOIN tokens t ON t.address=e.token"
    " WHERE e.handled=0 AND e.severity>=2 GROUP BY e.token ORDER BY sev DESC,"
    " COALESCE((SELECT s.score FROM snapshots s WHERE s.token=e.token ORDER BY s.ts DESC LIMIT 1), 0) DESC,"
    " MAX(e.ts) DESC")]
src = (ROOT / ".claude/skills/stock-token-scout/scripts/scout_cycle.py").read_text(encoding="utf-8")
assert "SELECT s.score FROM snapshots s WHERE s.token=e.token" in src and order == ["HI", "LO"], order

# 6. onchain: khoá dự phòng tên không đụng khoá _token có sẵn
osrc = (ROOT / ".claude/skills/stock-token-scout/scripts/onchain.py").read_text(encoding="utf-8")
assert 'p["_token"].get' not in osrc and 'isinstance(p.get("_meta"), dict)' in osrc

# 7. Pool rớt khỏi trending không được coi là thanh khoản sụt; vol1 không bị đếm trùng
import contextlib, json as _json  # noqa: E402
os.environ["STS_CACHE_DIR"] = tempfile.mkdtemp(prefix="sts_fix7_")
c.CACHE_DIR = pathlib.Path(os.environ["STS_CACHE_DIR"])
import scout_cycle  # noqa: E402
_NV = "0xd0601ce157db5bdc3162bbac2a2c8af5320d9eec"; _WE = "0x4200000000000000000000000000000000000006"
_MM = "0xaaaa000000000000000000000000000000000abc"; _TR = {"on": True}
def _gt():
    return {"attributes": {"address": "0xpoolweth", "name": "MEME / WETH", "reserve_in_usd": "400000",
            "volume_usd": {"h24": "480000", "h1": "20000"}, "price_change_percentage": {"h24": "2"},
            "transactions": {"h24": {"buys": 900, "sells": 800, "buyers": 300, "sellers": 250}},
            "fdv_usd": "5000000", "pool_created_at": "2026-09-01T00:00:00Z"},
            "relationships": {"base_token": {"data": {"id": "robinhood_" + _MM}},
                              "quote_token": {"data": {"id": "robinhood_" + _WE}}}}
def _dx(pool, other, osym, L, v24, v1):
    return {"pairAddress": pool, "dexId": "uniswap", "baseToken": {"address": _MM, "symbol": "MEME", "name": "Meme"},
            "quoteToken": {"address": other, "symbol": osym}, "liquidity": {"usd": L},
            "volume": {"h24": v24, "h1": v1}, "txns": {"h24": {"buys": 500, "sells": 450}}, "priceChange": {"h24": 2},
            "fdv": 5e6, "pairCreatedAt": (time.time() - 20 * 86400) * 1000, "info": {"websites": [{"url": "https://m.x"}]}}
def _fake(url, params=None, retries=3):
    u = url.lower()
    if "trending_pools" in u or "new_pools" in u:
        return {"data": [_gt()] if _TR["on"] else []}
    if "token-pairs/v1" in u and _NV in u:
        return [_dx("0xpoolnvda", _NV, "NVDA", 100000, 240000, 10000)]
    if "token-pairs/v1" in u and _MM in u:   # DexScreener thấy ĐỦ pool, kể cả pool WETH không trending
        return [_dx("0xpoolnvda", _NV, "NVDA", 100000, 240000, 10000), _dx("0xpoolweth", _WE, "WETH", 400000, 480000, 20000)]
    return []
c.get_json = _fake
def _run():
    discover.FAKE_PAIRS.clear(); c.WARNINGS.clear()
    with contextlib.redirect_stdout(io.StringIO()):
        return scout_cycle.run(5)
_run()
con = store.connect()
types1 = [r["type"] for r in con.execute("SELECT type FROM events")]
assert "VOLUME_ACCELERATION" not in types1, types1          # vol1 thật 30k = trung bình giờ 30k
assert con.execute("SELECT vol1 FROM snapshots").fetchone()[0] == 30000
con.execute("UPDATE snapshots SET ts=ts-6*3600"); con.execute("UPDATE events SET ts=ts-13*3600, handled=1"); con.commit()
_TR["on"] = False
_run()
con = store.connect()
new = [r["type"] for r in con.execute("SELECT type FROM events WHERE handled=0")]
assert "LIQUIDITY_COLLAPSE" not in new, new
snap = con.execute("SELECT liq FROM snapshots ORDER BY ts DESC LIMIT 1").fetchone()[0]
assert snap == 500000, snap                                  # vẫn đủ 2 pool
# nguồn dữ liệu thiếu (ít pool hơn lần trước) → không bắn LIQUIDITY_COLLAPSE
_orig = _fake
def _fake_dex_down(url, params=None, retries=3):
    return [] if ("token-pairs/v1" in url.lower() and _MM in url.lower()) else _orig(url, params, retries)
c.get_json = _fake_dex_down
con.execute("UPDATE snapshots SET ts=ts-6*3600"); con.execute("UPDATE events SET ts=ts-13*3600, handled=1"); con.commit()
_run()
con = store.connect()
assert "LIQUIDITY_COLLAPSE" not in [r["type"] for r in con.execute("SELECT type FROM events WHERE handled=0")]

# ---------------------------------------------------------------- v2.4
import importlib, json as _j  # noqa: E402
os.environ["STS_CACHE_DIR"] = tempfile.mkdtemp(prefix="sts_v24_")
importlib.reload(c)                      # bỏ các bản vá get_json ở trên, CACHE_DIR mới
c.CACHE_DIR = pathlib.Path(os.environ["STS_CACHE_DIR"])
import fetched  # noqa: E402
import onchain  # noqa: E402

# 8. Dữ liệu tải hộ được đọc như phản hồi API, không gọi mạng
def _no_net(req, timeout=20):
    raise AssertionError("không được gọi mạng khi đã có dữ liệu tải hộ")
urllib.request.urlopen = _no_net
U = "https://api.dexscreener.com/token-pairs/v1/robinhood/0xabc"
c.save_fetched(U, [{"pairAddress": "0x1"}])
assert c.get_json(U) == [{"pairAddress": "0x1"}]
assert c.get_json(U.upper().replace("HTTPS://API", "https://api")) == [{"pairAddress": "0x1"}]   # không phân biệt hoa thường

# 9. Proxy/DNS chặn: bỏ cuộc ngay, đánh dấu host, ghi URL thiếu
calls = []
def _tunnel(req, timeout=20):
    calls.append(1)
    raise urllib.error.URLError("Tunnel connection failed: 403 Forbidden")
urllib.request.urlopen = _tunnel
t0 = time.time()
assert c.get_json("https://robinhoodchain.blockscout.com/api/v2/tokens/0xdef") is None
assert c.get_json("https://robinhoodchain.blockscout.com/api/v2/tokens/0xeee") is None
assert len(calls) == 1 and time.time() - t0 < 3, (calls, time.time() - t0)
miss = (c.CACHE_DIR / "missing_urls.txt").read_text()
assert "tokens/0xdef" in miss and "tokens/0xeee" in miss

# 10. Dòng rút gọn DexScreener / holder → đúng cấu trúc script đọc
line = ("0xpool|uniswap|0xAAA|AI|Artificial Inu|0xNVDA|NVDA|5827048.7|14528881|10352|861580.25|352778.94|"
        "2013.74|346|651|-6.32|235276234|1784051311000|0.2378|0.001038|https://a.com/|https://x.com/a")
pr = fetched.dex_line_to_pair(line)
assert pr["liquidity"]["usd"] == 5827048.7 and pr["txns"]["h24"]["sells"] == 651 and pr["pairCreatedAt"] == 1784051311000
assert pr["info"]["socials"][0]["url"] == "https://x.com/a" and pr["priceChange"]["h24"] == -6.32
short = fetched.dex_line_to_pair("0xp|up|0xA|A|A|0xB|WETH|100|1|1|0|0|0|0|0||0||0.1|0.1")      # trường trống
assert short["priceChange"] == {} and "pairCreatedAt" not in short
hl = fetched.holder_line("0xH|1|eip7702||500")
assert hl["address"]["proxy_type"] == "eip7702" and hl["address"]["is_contract"] is True

# 11. Holder: ví EIP-7702 là ví cá nhân; PoolManager, hook launchpad và token tự giữ là hạ tầng
TOK = "0x91a2dae9699f0b82540b5886b0d8759c22820ba3"
c.save_fetched(f"{c.BS}/tokens/{TOK}", {"total_supply": "1000", "holders_count": "50", "exchange_rate": "0.5"})
c.save_fetched(f"{c.BS}/tokens/{TOK}/holders", {"items": [fetched.holder_line(x) for x in [
    f"{TOK}|1|eip1167|musebook|150", "0xpm|1||PoolManager|80", "0xhook|1||RehypeDopplerHookInitializer|30",
    "0xa7702|1|eip7702||40", "0xeoa|0|||20", "0xsafe|1|master_copy|SafeProxy|10"]], "next_page_params": None})
h = onchain.holders(TOK, set())
assert h["top10_eoa_pct"] == 6.0, h           # 40 + 20 trên 1000
assert h["largest_eoa_pct"] == 4.0 and h["top10_ex_infra_pct"] == 7.0 and h["exchange_rate"] == 0.5

# 12. Kiểm chéo giá: lệch > 20% là mâu thuẫn
assert onchain.cross_check_price(0.002064, 0.00123)["conflict"] is True
assert onchain.cross_check_price(0.2398, 0.2494)["conflict"] is False
assert onchain.cross_check_price(None, 0.1) is None

# 13. DexScreener trả đủ 30 cặp → cảnh báo có thể bỏ sót
c.WARNINGS.clear()
_orig_pairs = c.dex_token_pairs
c.dex_token_pairs = lambda a: [{"baseToken": {"address": a}, "quoteToken": {"address": "0x5fc5"}}] * 30
c.gt_pools = lambda *a, **k: []
discover.FAKE_PAIRS.clear()
discover.collect({"0xnvda": "NVDA"}, 1)
assert any("30 cặp cho NVDA" in w for w in c.WARNINGS), c.WARNINGS
c.dex_token_pairs = _orig_pairs

# 14. Chế độ không mạng: scout_cycle dừng với mã 3, không ghi snapshot
c.OFFLINE = True
c.SKIP_HOSTS = {"api.geckoterminal.com"}
c.BLOCKED_HOSTS.clear(); c.MISSING_THIS_RUN.clear(); c.WARNINGS.clear()
importlib.reload(scout_cycle)
with contextlib.redirect_stdout(io.StringIO()):
    code = scout_cycle.run(5)
assert code == 3, code
assert store.connect().execute("SELECT COUNT(*) FROM snapshots").fetchone()[0] == 0
assert not any("geckoterminal" in u for u in c.MISSING_THIS_RUN)       # nguồn bỏ qua không bị đòi tải
c.OFFLINE = False

# 15. HTML có mục "Độ tin cậy dữ liệu" và dòng nguồn chỉ gồm nguồn có dữ liệu
sys.path.insert(0, str(ROOT / ".claude/skills/scout-reader/scripts"))
import run_report  # noqa: E402
it = {"symbol": "QUBIT", "m": {"top10_eoa": None, "holders": 2021, "holders_source": None, "liq": 1, "vol24": 1,
      "turnover": 1, "top10_all": None, "largest_eoa": None, "fdv_to_liq": 1, "sell_share": 0.5, "age_days": 1,
      "holder_growth": None},
      "fact": {"generated_utc": "2026-09-23 15:13", "warnings": ["api.geckoterminal.com: không truy cập được"],
               "market": {"price_check": {"conflict": True, "diff_pct": 67.8}}}}
dq = run_report.data_quality_html([it])
assert "Độ tin cậy dữ liệu" in dq and "QUBIT" in dq and "67.8" in dq and "2026-09-23 15:13" in dq
ob = run_report.onchain_block(it)
assert "Nguồn: DexScreener, Blockscout" in ob and "GeckoTerminal" not in ob.split("Nguồn:")[1]

# 16. Skill và lệnh ghi rõ: giao một file HTML, không kể quy trình, tự xử lý khi mạng bị chặn
skill = (ROOT / ".claude/skills/stock-token-scout/SKILL.md").read_text(encoding="utf-8")
report_cmd = (ROOT / ".claude/commands/report.md").read_text(encoding="utf-8")
for t in (skill, report_cmd):
    assert "một file HTML" in t and "data_fallback.md" in t and "6 dòng" in t

# 17. Chế độ tải hộ: pool của ứng viên thanh khoản lớn nhất là bắt buộc, phần còn lại tuỳ chọn
os.environ["STS_CACHE_DIR"] = tempfile.mkdtemp(prefix="sts_v24b_")
c.CACHE_DIR = pathlib.Path(os.environ["STS_CACHE_DIR"])
c.OFFLINE = True; c.SKIP_HOSTS = {"api.geckoterminal.com"}
c.BLOCKED_HOSTS.clear(); c.MISSING_THIS_RUN.clear(); c.MISSING_OPTIONAL.clear(); c.WARNINGS.clear()
NV = "0xd0601ce157db5bdc3162bbac2a2c8af5320d9eec"
wl = c.load_whitelist()
for a in wl:
    lines = []
    if a == NV:
        lines = [f"0xbig|uniswap|0x{'b'*40}|BIG|Big|{NV}|NVDA|5000000|1|1|800000|0|0|300|300|1|9000000|1784051311000|0.1|0.001||",
                 f"0xsml|uniswap|0x{'s'*40}|SML|Small|{NV}|NVDA|30000|1|1|20000|0|0|50|50|1|90000|1784051311000|0.1|0.001||"]
    c.save_fetched(f"{c.DEX}/token-pairs/v1/robinhood/{a}", [fetched.dex_line_to_pair(l) for l in lines])
scout_cycle.COMPLETE_TOP = 1
with contextlib.redirect_stdout(io.StringIO()):
    code = scout_cycle.run(5)
assert code == 3 and any("b" * 40 in u for u in c.MISSING_THIS_RUN), c.MISSING_THIS_RUN
assert any("s" * 40 in u for u in c.MISSING_OPTIONAL) and not any("s" * 40 in u for u in c.MISSING_THIS_RUN)
c.OFFLINE = False; scout_cycle.COMPLETE_TOP = 10

print("ALL FIX TESTS PASSED")
