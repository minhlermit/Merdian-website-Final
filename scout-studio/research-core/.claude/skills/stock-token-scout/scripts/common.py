"""Hàm dùng chung: gọi API công khai (DexScreener, GeckoTerminal, Blockscout) và danh sách trắng stock token.

Chỉ dùng thư viện chuẩn của Python để skill chạy được ở mọi nơi (Claude Code, máy cá nhân, VPS).
Mọi lỗi mạng đều trả về None và ghi vào `WARNINGS`, không làm dừng cả lượt phân tích.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = Path(os.getenv("STS_CACHE_DIR", Path.home() / ".stock-token-scout"))

DEX = "https://api.dexscreener.com"
GT = "https://api.geckoterminal.com/api/v2"
BS = os.getenv("STS_BLOCKSCOUT", "https://robinhoodchain.blockscout.com/api/v2")
DEX_CHAIN, GT_NET = "robinhood", "robinhood"

# Địa chỉ hạ tầng không tính là "holder thật" khi đo mức độ tập trung
BURN_ZERO = "0x0000000000000000000000000000000000000000"
BURN = {BURN_ZERO, "0x000000000000000000000000000000000000dead"}

WARNINGS: list[str] = []
_last_call: dict[str, float] = {}
_MIN_GAP = {"geckoterminal": 2.2, "dexscreener": 0.25, "blockscout": 0.3}


# Pool ghép cổ phiếu dưới ngưỡng này là "pool bụi": không đủ để gọi token là ghép cặp cổ phiếu.
MIN_STOCK_PAIR_LIQ = float(os.getenv("STS_MIN_STOCK_PAIR_LIQ", "5000"))
BLOCKED_HOSTS: set = set()   # host trả trang chặn bot (Cloudflare): bỏ qua cho hết lần chạy

# ------------------------------------------------------------------ dữ liệu tải hộ (khi môi trường chặn API)
# Trong app Claude (Cowork) hoặc máy có proxy, script có thể không gọi thẳng được API. Khi đó agent tải bằng
# công cụ của mình (web fetch, Blockscout MCP) rồi lưu vào đây bằng `fetched.py put ...`; script đọc lại như
# phản hồi API thật. Mọi URL không lấy được được ghi vào missing_urls.txt để agent biết cần tải gì.
# Xem references/data_fallback.md.
OFFLINE = os.getenv("STS_OFFLINE") == "1"                      # không gọi mạng, chỉ dùng dữ liệu tải hộ
# host biết chắc không tải hộ được (mặc định GeckoTerminal ở chế độ không mạng): thiếu thì bỏ qua, không đòi tải
SKIP_HOSTS = {h.strip().lower() for h in os.getenv("STS_SKIP_HOSTS", "api.geckoterminal.com" if OFFLINE else "").split(",")
              if h.strip()}
MISSING_THIS_RUN: list[str] = []      # thiếu và bắt buộc: scout_cycle dừng với mã 3
MISSING_OPTIONAL: list[str] = []      # thiếu nhưng không chặn (bổ sung pool/hồ sơ cho ứng viên)
_optional_depth = 0


class optional_fetch:
    """Trong khối này, URL thiếu ở chế độ tải hộ chỉ ghi lại, không chặn lần chạy."""
    def __enter__(self):
        global _optional_depth
        _optional_depth += 1

    def __exit__(self, *exc):
        global _optional_depth
        _optional_depth -= 1
        return False
FETCHED_MAX_AGE_H = float(os.getenv("STS_FETCHED_MAX_AGE_H", "6"))
_FAST_FAIL = ("tunnel connection failed", "name or service not known", "nodename nor servname",
              "connection refused", "network is unreachable", "temporary failure in name resolution")


def fetched_key(url: str) -> str:
    return url.strip().lower()


def fetched_path(url: str) -> Path:
    import hashlib
    return CACHE_DIR / "fetched" / (hashlib.sha1(fetched_key(url).encode()).hexdigest()[:20] + ".json")


def read_fetched(url: str):
    p = fetched_path(url)
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    if time.time() - d.get("saved_at", 0) > FETCHED_MAX_AGE_H * 3600:
        return None
    return d.get("data")


def save_fetched(url: str, data, source: str = "agent"):
    p = fetched_path(url)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"url": fetched_key(url), "saved_at": time.time(), "source": source, "data": data},
                            ensure_ascii=False), encoding="utf-8")


def record_missing(url: str):
    if _host(url) in SKIP_HOSTS:
        return
    (MISSING_OPTIONAL if _optional_depth else MISSING_THIS_RUN).append(fetched_key(url))
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        name = "missing_optional.txt" if _optional_depth else "missing_urls.txt"
        with open(CACHE_DIR / name, "a", encoding="utf-8") as fh:
            fh.write(fetched_key(url) + "\n")
    except OSError:
        pass


def _host(url: str) -> str:
    return urllib.parse.urlparse(url).netloc.lower()


def warn(msg: str):
    WARNINGS.append(msg)


def _throttle(url: str):
    for host, gap in _MIN_GAP.items():
        if host in url:
            wait = gap - (time.time() - _last_call.get(host, 0))
            if wait > 0:
                time.sleep(wait)
            _last_call[host] = time.time()


def get_json(url: str, params: dict | None = None, retries: int = 3):
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    headers = {"User-Agent": "stock-token-scout/1.0", "Accept": "application/json"}
    key = os.getenv("BLOCKSCOUT_API_KEY")
    if key and "blockscout" in url:
        headers["Authorization"] = f"Bearer {key}"
    host = _host(url)
    cached = read_fetched(url)
    if cached is not None:
        return cached
    if OFFLINE or host in BLOCKED_HOSTS:
        record_missing(url)
        if OFFLINE and host not in BLOCKED_HOSTS:
            BLOCKED_HOSTS.add(host)
            warn(f"{host}: không có dữ liệu trong lần chạy này (nguồn bị bỏ qua)" if host in SKIP_HOSTS else
                 f"{host}: chế độ không mạng (STS_OFFLINE=1), dùng dữ liệu tải hộ")
        return None
    if "geckoterminal" in host:
        retries = max(retries, 5)        # GeckoTerminal giới hạn ~30 lượt/phút: chờ lâu hơn trước khi bỏ cuộc
    for i in range(retries):
        _throttle(url)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and i < retries - 1:
                ra = e.headers.get("Retry-After") if e.headers else None
                time.sleep(min(60.0, float(ra)) if ra and ra.isdigit() else 6 * (i + 1))
                continue
            if e.code == 403:
                body = ""
                try:
                    body = e.read(2000).decode("utf-8", "ignore")
                except Exception:
                    pass
                if "Just a moment" in body or (e.headers and e.headers.get("cf-mitigated")):
                    BLOCKED_HOSTS.add(host)
                    record_missing(url)
                    warn(f"{host} chặn truy cập từ máy này (Cloudflare 403): bỏ qua nguồn này cho hết lần chạy. "
                         "Chạy trên máy cá nhân, đặt BLOCKSCOUT_API_KEY, hoặc tải hộ (references/data_fallback.md).")
                    return None
            if e.code == 404:
                return None
            record_missing(url)
            warn(f"HTTP {e.code}: {url[:120]}")
            return None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            # proxy chặn domain / không phân giải được: thử lại vô ích, đánh dấu host và chuyển sang dữ liệu tải hộ
            if any(k in str(getattr(e, "reason", e)).lower() for k in _FAST_FAIL):
                BLOCKED_HOSTS.add(host)
                record_missing(url)
                warn(f"{host}: môi trường này không truy cập được (proxy/DNS). Dữ liệu từ nguồn này cần tải hộ, "
                     "xem references/data_fallback.md.")
                return None
            if i == retries - 1:
                record_missing(url)
                warn(f"Lỗi mạng ({type(e).__name__}): {url[:120]}")
                return None
            time.sleep(2 * (i + 1))
    return None


def as_list(payload) -> list:
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    for k in ("pairs", "data", "items"):
        if isinstance(payload.get(k), list):
            return payload[k]
    return []


def f(x, default=0.0) -> float:
    try:
        return float(x) if x is not None else default
    except (TypeError, ValueError):
        return default


# --------------------------------------------------------------------- whitelist
def load_whitelist() -> dict[str, str]:
    """{địa_chỉ_lowercase: ticker}. Có thể ghi đè bằng file ~/.stock-token-scout/stock_tokens.json."""
    user_file = CACHE_DIR / "stock_tokens.json"
    path = user_file if user_file.exists() else SKILL_DIR / "references" / "stock_tokens.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return {v.lower(): k for k, v in data["tokens"].items()}


# --------------------------------------------------------------------- DexScreener
def dex_token_pairs(addr: str) -> list[dict]:
    return as_list(get_json(f"{DEX}/token-pairs/v1/{DEX_CHAIN}/{addr}"))


def dex_tokens(addrs: list[str]) -> list[dict]:
    out = []
    for i in range(0, len(addrs), 30):
        out += as_list(get_json(f"{DEX}/tokens/v1/{DEX_CHAIN}/{','.join(addrs[i:i + 30])}"))
    return out


# --------------------------------------------------------------------- GeckoTerminal
def gt_pools(kind: str, pages: int = 2, duration: str | None = None) -> list[dict]:
    """kind: 'trending_pools' hoặc 'new_pools'."""
    out = []
    for p in range(1, pages + 1):
        params = {"page": p, "include": "base_token,quote_token"}
        if duration and kind == "trending_pools":
            params["duration"] = duration
        out += as_list(get_json(f"{GT}/networks/{GT_NET}/{kind}", params))
    return out


def gt_token_pools(addr: str) -> list[dict]:
    return as_list(get_json(f"{GT}/networks/{GT_NET}/tokens/{addr}/pools", {"include": "base_token,quote_token"}))


def gt_token_info(addr: str) -> dict:
    d = get_json(f"{GT}/networks/{GT_NET}/tokens/{addr}/info")
    return ((d or {}).get("data") or {}).get("attributes") or {}


def gt_ohlcv(pool: str, timeframe="hour", limit=168, currency="usd", token="base") -> list[list]:
    d = get_json(f"{GT}/networks/{GT_NET}/pools/{pool}/ohlcv/{timeframe}",
                 {"aggregate": 1, "limit": limit, "currency": currency, "token": token})
    return (((d or {}).get("data") or {}).get("attributes") or {}).get("ohlcv_list") or []


def gt_addr(rel: dict | None) -> str:
    """'robinhood_0xabc' -> '0xabc'."""
    rid = (((rel or {}).get("data")) or {}).get("id", "")
    return rid.split("_", 1)[1].lower() if "_" in rid else rid.lower()


# --------------------------------------------------------------------- Blockscout
def bs_token(addr: str) -> dict:
    return get_json(f"{BS}/tokens/{addr}") or {}


def bs_holders(addr: str, pages: int = 1) -> list[dict]:
    items, params = [], None
    for _ in range(pages):
        d = get_json(f"{BS}/tokens/{addr}/holders", params)
        if not d:
            break
        items += d.get("items") or []
        params = d.get("next_page_params")
        if not params:
            break
    return items


def bs_address(addr: str) -> dict:
    return get_json(f"{BS}/addresses/{addr}") or {}


def bs_transfers_from(holder: str, token: str, pages: int = 2) -> list[dict]:
    items, params = [], {"type": "ERC-20", "filter": "from", "token": token}
    for _ in range(pages):
        d = get_json(f"{BS}/addresses/{holder}/token-transfers", params)
        if not d:
            break
        items += d.get("items") or []
        nxt = d.get("next_page_params")
        if not nxt:
            break
        params = {**params, **nxt}
    return items


# --------------------------------------------------------------------- cache
def cache_path(name: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / name


def load_cache(name: str) -> dict:
    p = cache_path(name)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def save_cache(name: str, data: dict):
    cache_path(name).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def bs_smart_contract(addr: str) -> dict:
    return get_json(f"{BS}/smart-contracts/{addr}") or {}


def bs_token_transfers(addr: str, pages: int = 3) -> list[dict]:
    items, params = [], None
    for _ in range(pages):
        d = get_json(f"{BS}/tokens/{addr}/transfers", params)
        if not d:
            break
        items += d.get("items") or []
        params = d.get("next_page_params")
        if not params:
            break
    return items
