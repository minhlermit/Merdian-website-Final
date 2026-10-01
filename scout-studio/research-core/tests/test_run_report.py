"""Kiểm thử bước cuối (investor memo + HTML của lần chạy), không cần mạng: python3 tests/test_run_report.py"""
import os, sys, json, io, re, time, contextlib, tempfile, pathlib
TMP = tempfile.mkdtemp(prefix="sts_run_")
os.environ["STS_CACHE_DIR"] = TMP
os.environ["STS_OFFLINE"] = "1"
os.environ.pop("STS_REPORT_DIR", None)
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude/skills/scout-reader/scripts"))
import run_report as R  # noqa: E402
import store  # noqa: E402

A = "0x" + "a1" * 20          # ứng viên tốt
B = "0x" + "b2" * 20          # meme đầu cơ
C = "0x" + "c3" * 20          # stock token giả → TRÁNH XA
D = "0x" + "d4" * 20          # nghiên cứu hỏng
OTHER_A = "0x" + "a9" * 20    # token khác trùng ticker với A
REPORTS = pathlib.Path(TMP) / "reports"
REPORTS.mkdir(parents=True, exist_ok=True)
now = time.time()


def run(*args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            code = R.main(list(args))
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else 2
    txt = buf.getvalue()
    try:
        return code, json.loads(txt)
    except ValueError:
        return code, txt


def fact(sym, name, liq, holders, top10, websites=None, x=None):
    return {"name": name, "symbol": sym, "generated_utc": "2026-09-23 06:00",
            "profile": {"websites": websites or [], "x": x, "telegram": None, "image_url": None},
            "market": {"liq_total_usd": liq, "vol24_total_usd": liq * 2, "turnover24": 2.0, "fdv_to_liq": 8.0,
                       "sell_share": 0.45, "avg_trade_usd": 120.0, "age_days": 12.0, "vol_share_main_pool_pct": 70.0},
            "holders": {"holders_count": holders, "top10_eoa_pct": top10, "largest_eoa_pct": 3.0},
            "pools": [{"dex": "uniswap", "counter": "NVDA", "stock": "NVDA", "liq_usd": liq, "vol24": liq * 2,
                       "pool": "0x" + "9" * 64}],
            "deployer": {"deployer": "0x" + "f" * 40, "deployer_is_contract": True, "deployer_label": "DopplerFactory"},
            "contract": {"is_verified": True, "proxy_type": "eip1167", "power_functions": []},
            "warnings": ["GeckoTerminal HTTP 429 ở một phần lệnh gọi"]}


con = store.connect()
store.save_fact(con, A, "onchain", fact("ALPHA", "Alpha AI Credits", 400000, 2600, 14.0,
                                         websites=["https://alpha.example", "javascript:alert(1)"], x="@alpha_ai"))
store.save_fact(con, B, "onchain", fact("BALD", '<script>alert("x")</script>', 23000, 12, 80.0))
store.save_fact(con, C, "onchain", fact("NVDAX", "Fake NVDA", 60000, 300, 30.0))
# A: thanh khoản sụt > 50% trong 7 ngày → mức rủi ro tối thiểu CRITICAL
con.execute("INSERT INTO snapshots(token, ts, liq) VALUES(?,?,?)", (A, now - 3 * 86400, 900000))
con.execute("INSERT INTO snapshots(token, ts, liq) VALUES(?,?,?)", (A, now - 3600, 400000))
con.execute("INSERT INTO events(token, ts, type, severity, detail) VALUES(?,?,?,?,?)",
            (B, now - 7200, "NEW_STOCK_PAIRED_POOL", 3, "{}"))
con.execute("INSERT INTO claims(token, claim, ctype, arg, status, detail, ts) VALUES(?,?,?,?,?,?,?)",
            (A, "burn for AI credit", "burn_mechanism", "", "VERIFIED_ONCHAIN", "thấy lệnh đốt", now))
con.execute("INSERT INTO tokens(address, symbol) VALUES(?,?)", (A, "ALPHA"))
con.execute("INSERT INTO tokens(address, symbol) VALUES(?,?)", (OTHER_A, "alpha"))
con.execute("INSERT INTO evidence(token, url, source, category, text, hash, first_seen) VALUES(?,?,?,?,?,?,?)",
            (A, "https://x.com/alpha_ai/status/1", "x", "creator", "Ra mắt v2 tuần sau", "h1", now))
con.commit()


def verdict(ticker, token, scores, flags=(), conf="HIGH"):
    return {"schema": 1, "ticker": ticker, "token": token, "one_liner": f"{ticker} một câu", "bear_case": "xấu",
            "confidence": conf, "hard_flags": list(flags), "scores": scores}


def memo(token, ticker, v, sections=("Kết luận nhanh", "Cấu trúc thị trường", "Cờ rủi ro")):
    body = "".join(f"## {s}\nnội dung\n\n" for s in sections)
    p = REPORTS / f"{ticker}_20260923_0600.md"
    p.write_text(f"# {ticker}: dự án\n*{token} | Xếp loại: THEO DÕI*\n\n{body}## Đánh giá tiềm năng\n"
                 f"```scout-verdict\n{json.dumps(v, ensure_ascii=False)}\n```\n\n## Nguồn\n- x\n", encoding="utf-8")
    return str(p)


GOOD = {"mechanism": 4, "stock_link": 3, "liquidity": 4, "distribution": 4, "incentives": 3, "transparency": 3}
WEAK = {"mechanism": 1, "stock_link": 3, "liquidity": 2, "distribution": 0, "incentives": 1, "transparency": 1}

# 1. Mở lần chạy: loại trùng (khác hoa/thường vẫn là một token)
code, res = run("start", "--tokens", ",".join([A, B, C, D, A.upper().replace("0X", "0x")]))
assert code == 0 and res["deduplicated"] == 1 and len(res["tokens"]) == 4, res

# 2. Cổng: agent cuối bị chặn khi token chưa COMPLETE
assert run("gate", "--token", A)[0] == 4

# 3. Cổng COMPLETE từ chối memo thiếu mục, chấp nhận khi đủ
code, res = run("complete", "--token", A, "--memo", memo(A, "ALPHA", verdict("ALPHA", A, GOOD), sections=("Kết luận nhanh",)))
assert code == 1 and res["research_status"] == "INCOMPLETE" and any("Cờ rủi ro" in r for r in res["reasons"]), res
assert run("gate", "--token", A)[0] == 4
assert run("complete", "--token", A, "--memo", memo(A, "ALPHA", verdict("ALPHA", A, GOOD)))[0] == 0
# memo nói về token khác → từ chối
code, res = run("complete", "--token", B, "--memo", memo(B, "BALD", verdict("BALD", C, WEAK)))
assert code == 1 and any("token khác" in r for r in res["reasons"]), res
assert run("complete", "--token", B, "--memo", memo(B, "BALD", verdict("BALD", B, WEAK, conf="MEDIUM")))[0] == 0
# memo ngắn được chấp nhận chỉ khi là stock token giả
assert run("complete", "--token", C, "--memo",
           memo(C, "NVDAX", verdict("NVDAX", C, WEAK, flags=["FAKE_STOCK_PAIR"]), sections=()))[0] == 0

# 4. plan chờ mọi token xong; token hỏng không bao giờ tới agent cuối
code, res = run("plan")
assert code == 3 and res["pending"] == [D], res
assert run("fail", "--token", D, "--reason", "Blockscout 403")[0] == 0
code, res = run("plan", "--deep", "1")
assert code == 0, res
modes = {r["token"]: r["mode"] for r in res}
assert modes == {A: "DEEP", B: "BRIEF", C: "BRIEF"}, modes          # D không có trong plan; TRÁNH XA không được DEEP
assert run("gate", "--token", D)[0] == 4
code, g = run("gate", "--token", A)
assert code == 0 and g["allowed"] and g["mode"] == "DEEP", g

# 5. Gói bằng chứng: dùng lại dữ liệu đã có, gồm mức rủi ro tối thiểu do luật tính
code, ev = run("evidence", "--token", A)
assert code == 0 and ev["claims"][0]["status"] == "VERIFIED_ONCHAIN" and ev["evidence_items"][0]["category"] == "creator"
assert ev["metrics"]["exit_risk_floor"] == "CRITICAL" and ev["metrics"]["liq_drawdown_7d_pct"] > 50


def deep_memo(**kw):
    d = {"schema": 1, "token": A, "ticker": "ALPHA", "mode": "DEEP",
         "project_thesis": "Đốt token để lấy credit AI; sản phẩm có người dùng thật.",
         "problem": "Chi phí AI cho người dùng nhỏ", "product": "Ứng dụng chat trả bằng token",
         "technology": {"stack": "Hợp đồng burn + API", "advantage": "Không có lợi thế đặc biệt"},
         "creator_identity": {"summary": "@alpha_ai", "evidence": "LIKELY"},
         "creator_commentary": [{"summary": "Ra mắt v2 tuần sau", "source": "https://x.com/alpha_ai/status/1",
                                 "evidence": "UNCONFIRMED"}],
         "user_acquisition": "Launchpad trending", "retention": "Dùng credit hằng ngày",
         "monetization": "Phí credit", "token_value_capture": {"role": "Đốt khi dùng", "product_growth_drives_token_demand": "YES",
                                                               "explanation": "Dùng nhiều thì đốt nhiều"},
         "growth_engine": {"verdict": "SUSTAINABLE", "loop": "dùng → đốt", "depends_on_new_buyers": True, "explanation": "..."},
         "traction": [{"metric": "Holder", "value": "2600", "evidence": "VERIFIED_ONCHAIN"}],
         "moat": {"type": "NONE", "explanation": "Dễ sao chép"},
         "liquidity_exit_risk": {"level": "LOW", "assessment": "ổn", "deterioration_signals": []},
         "stock_pair_analysis": "Ghép cặp NVDA chính chủ; không bảo chứng", "catalysts": ["Ra v2"],
         "invalidation_conditions": ["Lượng đốt giảm 2 tuần liên tiếp"], "open_questions": ["Doanh thu thật?"],
         "evidence_confidence": "HIGH", "conviction": "CONTINUE_RESEARCH", "conviction_memo": "Có cơ chế đốt thật."}
    d.update(kw)
    return d


def write_inv(token, obj):
    p = R.investor_file(R.load_manifest(R.current_run_id()), token)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


# 6. Kiểm investor memo: cấm ngôn ngữ khuyến nghị, bắt đủ trường, luật hạ kết luận
write_inv(A, deep_memo(conviction_memo="Nên mua trước khi ra v2, mục tiêu giá x10"))
code, res = run("check-investor", "--token", A)
assert code == 1 and any("khuyến nghị" in e for e in res["errors"]), res
bad = deep_memo(); bad.pop("retention"); bad["invalidation_conditions"] = []
write_inv(A, bad)
code, res = run("check-investor", "--token", A)
assert code == 1 and any("retention" in e for e in res["errors"]) and any("mất hiệu lực" in e for e in res["errors"])
write_inv(A, deep_memo())
code, res = run("check-investor", "--token", A)
assert code == 0, res
assert res["growth"] == R.GROWTH["FRAGILE"]                            # vẫn dựa vào người mua mới → không "bền vững"
assert res["exit_risk"] == "Nghiêm trọng"                              # agent ghi LOW, số liệu on-chain nâng lên
assert res["conviction"] == "TIẾP TỤC NGHIÊN CỨU"
write_inv(B, {"schema": 1, "mode": "BRIEF", "project_thesis": "Meme mẫu launchpad.",
              "growth_engine": {"verdict": "NONE", "explanation": "Chỉ dựa vào người mua sau"},
              "conviction": "CONTINUE_RESEARCH", "conviction_memo": "12 holder, không có sản phẩm."})
code, res = run("check-investor", "--token", B)
assert code == 0 and res["conviction"] == "CHỈ THEO DÕI" and res["notes"], res
write_inv(C, {"schema": 1, "mode": "BRIEF", "project_thesis": "Giả NVDA.", "growth_engine": {"verdict": "UNKNOWN", "explanation": "-"},
              "conviction": "MONITOR", "conviction_memo": "Stock token giả."})
code, res = run("check-investor", "--token", C)
assert code == 0 and res["conviction"] == "DỪNG NGHIÊN CỨU", res

# 7. HTML duy nhất của lần chạy
cmp_path = R.run_path(R.current_run_id()) / "comparison.json"
cmp_path.write_text(json.dumps({"summary": "ALPHA là token duy nhất có cơ chế thật.", "ranking": [{"ticker": "ALPHA", "why": "có đốt token"}],
                                "patterns": ["2/3 token dùng khuôn launchpad"]}, ensure_ascii=False), encoding="utf-8")
code, _ = run("render")
assert code == 0
html = (REPORTS / "latest.html").read_text(encoding="utf-8")
run_file = REPORTS / f"scout_run_{R.current_run_id()}.html"
assert run_file.is_file() and run_file.read_text(encoding="utf-8") == html
assert html.index("Bảng so sánh") < html.index("Memo đầy đủ cho ứng viên hàng đầu")     # dashboard trước
for t in (A, B, C, D):
    assert html.count(f"id=\"t-{t}\"") == 1, t                                      # mỗi token đúng một thẻ
assert html.index(f'id="t-{A}"') < html.index(f'id="t-{B}"') < html.index(f'id="t-{D}"')
assert "<script>alert" not in html and "&lt;script&gt;" in html                    # tên token độc hại được escape
assert "javascript:alert" not in html and "https://alpha.example" in html and "https://x.com/alpha_ai" in html
assert "token khác cùng ticker" in html                                            # ALPHA trùng ticker với OTHER_A
assert "ALPHA là token duy nhất" in html and "Chưa hoàn tất nghiên cứu" in html and "Blockscout 403" in html
card_a = html[html.index(f'id="t-{A}"'):html.index(f'id="t-{B}"')]
visible, tech = card_a.split('<details class="tech">', 1)
assert A not in re.sub(r"#?t-0x[0-9a-f]{40}", "", visible)                          # địa chỉ chỉ nằm trong Technical Evidence
assert A in tech and "burn_mechanism" in tech and "HTTP 429" in tech
for section in ("Vấn đề dự án giải quyết", "Sản phẩm thực tế", "Công nghệ và lợi thế", "Creator đang nói gì",
                "Thu hút người dùng", "Vì sao người dùng quay lại", "Doanh thu", "Token nắm giữ giá trị",
                "Traction", "Moat", "Bằng chứng on-chain", "rủi ro thoát hàng", "Phân tích cặp cổ phiếu",
                "Catalyst", "Điều làm thesis mất hiệu lực", "TIẾP TỤC NGHIÊN CỨU"):
    assert section in visible, section
assert "class='logo mono'" in html                                                 # không mạng → logo chữ cái
assert "không phải khuyến nghị đầu tư" in html

# 8. Blockscout lỗi → holder lấy từ GeckoTerminal, top 10 gồm cả pool được ghi rõ, không giả làm "ví thường"
E = "0x" + "e5" * 20
gtf = fact("GTX", "GT fallback", 300000, 5000, None)
gtf["holders"] = {"holders_count": 5000, "top10_all_pct": 70.0, "source": "geckoterminal", "top10_eoa_pct": None}
store.save_fact(con, E, "onchain", gtf); con.commit()
mt = R.metrics(con, E)
assert mt["top10_eoa"] is None and mt["top10_all"] == 70.0 and mt["holders_source"] == "geckoterminal"
assert mt["exit_risk_floor"] == "MEDIUM" and any("gồm cả pool" in r for r in mt["exit_risk_reasons"])
assert R.top10_cell(mt) == "70.0%*"

# 9. Nhãn cặp: stablecoin không bị gắn cảnh báo; chỉ cảnh báo khi nghi stock token giả
f_usdg = fact("PX", "px", 1e6, 10, 10.0); f_usdg["pools"][0].update(counter="USDG", stock=None)
assert R.pair_label(f_usdg) == ("PX/USDG", "none")
f_fake = fact("FX", "fx", 1e5, 10, 10.0); f_fake["suspected_fake_stock_pairs"] = [{"claimed_stock": "NVDA"}]
assert R.pair_label(f_fake)[1] == "fake"
assert R.pair_label(fact("OK", "ok", 1e5, 10, 10.0)) == ("OK/NVDA", "stock")
assert R._fmt(100530) == "100,530" and R._fmt(69.8565, "%") == "69.9%" and R._fmt(0.479) == "0.479"
assert R._clip("một hai ba bốn", 8) == "một hai…"

# 10. Giá sụt mạnh trong 7 ngày nâng mức rủi ro thoát hàng tối thiểu (kể cả khi chỉ có một snapshot)
for tok, dd, want in (("0x" + "f1" * 20, -89.9, "HIGH"), ("0x" + "f2" * 20, -59.9, "MEDIUM"), ("0x" + "f3" * 20, -20.0, "LOW")):
    ff = fact("DD", "dd", 3e6, 5000, 10.0); ff["history_7d"] = {"max_drawdown_pct": dd}
    store.save_fact(con, tok, "onchain", ff); con.commit()
    assert R.metrics(con, tok)["exit_risk_floor"] == want, (dd, R.metrics(con, tok))

# 11. Token bị kết luận DỪNG NGHIÊN CỨU không nằm trong dải "Ứng viên hàng đầu"
top = html[html.index("Ứng viên hàng đầu"):html.index("Bảng so sánh")]
assert "ALPHA" in top and "NVDAX" not in top

print("ALL RUN REPORT TESTS PASSED")
