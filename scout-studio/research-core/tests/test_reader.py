"""Kiểm thử skill scout-reader (không cần mạng): python3 tests/test_reader.py"""
import sys, json, io, contextlib, tempfile, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude/skills/scout-reader/scripts"))
import render_report as r

D = pathlib.Path(tempfile.mkdtemp(prefix="sts_reader_"))


BALD = "0xcda13e82ee4cfd2d4d0906070508b5745dc71e18"


def memo(name, ticker, verdict_obj=None, extra="", addr=None):
    addr = addr or ("0x" + (ticker.encode().hex() * 40)[:40])
    block = ""
    if verdict_obj is not None:
        body = verdict_obj if isinstance(verdict_obj, str) else json.dumps(verdict_obj, ensure_ascii=False, indent=1)
        block = f"\n## Đánh giá tiềm năng (thẳng thắn)\n```scout-verdict\n{body}\n```\n"
    text = (f"# {ticker}: Dự án thử\n*{addr} | 2026-09-23 | Xếp loại: BỎ QUA | Lần trước: mới*\n\n"
            f"## Kết luận nhanh\nMeme mẫu launchpad, ít holder.\n{extra}{block}\n## Nguồn\n- x\n")
    (D / name).write_text(text, encoding="utf-8")
    return D / name


def V(**kw):
    base = {"schema": 1, "ticker": "T", "one_liner": "một câu", "bear_case": "xấu", "confidence": "HIGH",
            "hard_flags": [], "scores": {"mechanism": 1, "stock_link": 3, "liquidity": 2, "distribution": 0,
                                         "incentives": 1, "transparency": 1}}
    base.update(kw)
    return base


# 1. Luật xếp loại
assert r.compute(V())["verdict"] == "SPECULATIVE"                                  # 8/30 như ví dụ BALDCOIN
good = {"mechanism": 4, "stock_link": 3, "liquidity": 4, "distribution": 3, "incentives": 3, "transparency": 3}
assert r.compute(V(scores=good))["verdict"] == "RESEARCH_DEEPER"                    # 20/30, đủ điều kiện
assert r.compute(V(scores=dict(good, mechanism=2)))["verdict"] == "UNPROVEN"        # cơ chế chưa kiểm → không lên xanh
assert r.compute(V(scores=dict(good, distribution=0, mechanism=5, liquidity=5)))["verdict"] == "UNPROVEN"
assert r.compute(V(scores=good, confidence="LOW"))["verdict"] == "UNPROVEN"
assert r.compute(V(scores=good, hard_flags=["FAKE_STOCK_PAIR"]))["verdict"] == "AVOID"   # một cờ đỏ là đủ
mid = {"mechanism": 2, "stock_link": 3, "liquidity": 3, "distribution": 2, "incentives": 2, "transparency": 3}
assert r.compute(V(scores=mid))["verdict"] == "UNPROVEN"                            # 15/30 = 50%
few = {"mechanism": 5, "stock_link": 5, "liquidity": None, "distribution": None, "incentives": None, "transparency": None}
res = r.compute(V(scores=few))
assert res["verdict"] == "UNRATED" and res["confidence"] == "LOW"                   # thiếu dữ liệu ≠ điểm cao
# null khác 0: bỏ tiêu chí thiếu khỏi mẫu số
res = r.compute(V(scores=dict(good, transparency=None)))
assert res["max"] == 25 and res["verdict"] == "RESEARCH_DEEPER" and res["confidence"] == "MEDIUM"
# điểm ngoài khoảng bị kẹp, kiểu sai bị coi là thiếu
res = r.compute(V(scores=dict(good, mechanism=9, liquidity="cao")))
assert res["scores"]["mechanism"] == 5 and res["scores"]["liquidity"] is None
# agent tự nâng hạng → luật thắng, có ghi chú
res = r.compute(V(verdict="RESEARCH_DEEPER"))
assert res["verdict"] == "SPECULATIVE" and any("luật" in n for n in res["notes"])

# meme thuần (cơ chế 1) có thanh khoản sâu vẫn là ĐẦU CƠ THUẦN, không được lên "có ý tưởng"
meme = {"mechanism": 1, "stock_link": 3, "liquidity": 4, "distribution": None, "incentives": 2, "transparency": 1}
res = r.compute(V(scores=meme))
assert res["pct"] > 0.4 and res["verdict"] == "SPECULATIVE" and any("cơ chế ≤ 1" in n for n in res["notes"]), res
assert r.compute(V(scores=dict(meme, mechanism=None)))["verdict"] == "UNPROVEN"      # thiếu dữ liệu ≠ meme

# 2. Đọc memo: có khối, memo cũ không có khối, JSON hỏng, khối thụt lề
m1 = memo("BALD_20260923_0618.md", "BALDCOIN", addr=BALD, verdict_obj=V(ticker="BALDCOIN", token=BALD,
          assessed_at="2026-09-23T06:18Z", key_facts=[{"label": "Holder", "value": "12", "evidence": "VERIFIED_ONCHAIN"}]))
it = r.parse_memo(m1)
assert it["verdict"] == "SPECULATIVE" and it["ticker"] == "BALDCOIN" and not it["errors"] and not it["warnings"], it
legacy = r.parse_memo(memo("OLD_20260922_0000.md", "OLDIE"))
assert legacy["verdict"] == "UNRATED" and legacy["one_liner"].startswith("Meme mẫu") and legacy["memo_rating"] == "BỎ QUA"
assert legacy["errors"]
broken = r.parse_memo(memo("BAD_20260923_0000.md", "BAD", "{không phải json"))
assert broken["verdict"] == "UNRATED" and any("không đọc được" in e for e in broken["errors"])
(D / "BAD_20260923_0000.md").unlink()
indented = "   ```scout-verdict\n   " + json.dumps(V(ticker="IND")) + "\n   ```"
(D / "IND_20260923_0000.md").write_text("# IND: x\n## Đánh giá tiềm năng\n" + indented + "\n", encoding="utf-8")
assert r.parse_memo(D / "IND_20260923_0000.md")["verdict"] == "SPECULATIVE"
(D / "IND_20260923_0000.md").unlink()

# 3. Chỉ giữ memo mới nhất cho mỗi token, bỏ qua memo tổng hợp chu kỳ
memo("BALD_20260922_0000.md", "BALDCOIN", addr=BALD, verdict_obj=V(ticker="BALDCOIN", token=BALD,
     assessed_at="2026-09-22T00:00Z", hard_flags=["HONEYPOT_PATTERN"]))
(D / "cycle_20260923_0620.md").write_text("# Scout Robinhood Chain\n", encoding="utf-8")
data = r.load(D)
bald = [i for i in data["items"] if i["ticker"] == "BALDCOIN"]
assert len(bald) == 1 and bald[0]["verdict"] == "SPECULATIVE" and bald[0]["memo_count"] == 2
assert data["latest_cycle"] == "cycle_20260923_0620.md"
assert all(i["ticker"] != "Scout Robinhood Chain" for i in data["items"])

# 4. HTML: chữ do người lạ đặt phải bị escape
evil = '<script>alert(1)</script>'
memo("EVIL_20260923_0000.md", "EVIL", V(ticker=evil, token="0x" + "e" * 40, one_liner='"><img src=x onerror=alert(1)>',
     key_facts=[{"label": evil, "value": evil, "evidence": '"><b>'}]))
page = r.render_html(r.load(D))
assert "<script>alert" not in page and "<img src=x" not in page and 'ev-"><b>' not in page
assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page
assert "không phải khuyến nghị đầu tư" in page                                   # miễn trừ luôn hiện

# 5. CLI: --json, --check, ghi index.html
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    assert r.main(["--dir", str(D), "--json"]) == 0
rows = json.loads(buf.getvalue())
assert {row["ticker"] for row in rows} >= {"BALDCOIN", "OLDIE"} and all("label" in row for row in rows)
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    assert r.main(["--check", str(m1)]) == 0
assert json.loads(buf.getvalue())["label"] == "ĐẦU CƠ THUẦN"
with contextlib.redirect_stdout(io.StringIO()):
    assert r.main(["--check", str(D / "OLD_20260922_0000.md")]) == 1          # thiếu khối → mã 1
    assert r.main(["--dir", str(D)]) == 0
assert (D / "index.html").read_text(encoding="utf-8").startswith("<!doctype html>")

# 6. Ví dụ trong scorecard.md phải khớp luật (tài liệu không được nói sai)
card = (ROOT / ".claude/skills/scout-reader/references/scorecard.md").read_text(encoding="utf-8")
ex = json.loads(r.BLOCK_RE.search(card).group(1))
assert r.compute(ex)["verdict"] == ex["verdict"] == "SPECULATIVE"
assert set(r.HARD_FLAGS) == set(__import__("re").findall(r"^\| `([A-Z_]+)` \|", card, __import__("re").M))

print("ALL READER TESTS PASSED")
