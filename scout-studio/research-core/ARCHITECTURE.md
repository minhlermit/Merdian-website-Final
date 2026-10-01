# Robinhood Token Research & Evaluation: kiến trúc

> **Blockchain cho thấy hoạt động kinh tế một cách minh bạch, nhưng không tự động cho thấy danh tính con người.**

Pipeline: `discover → enrich → verify → classify → investigate → score → present`

## 1. Quyết định của v2

| Chủ đề | Spec gốc | v2 chọn | Lý do |
|---|---|---|---|
| Phạm vi chuỗi | Đa chuỗi | **Chỉ Robinhood Chain** | Lợi thế nằm ở module Stock-Pair. Đa chuỗi tốn công nhiều lần mà không thêm lợi thế |
| Event | Stream realtime | **Snapshot + diff** mỗi chu kỳ (ví dụ 6 giờ) | Chuỗi ra block khoảng 0,1 giây; stream thật cần hạ tầng tốn phí. Diff giữ đúng tinh thần event-driven với độ trễ theo giờ |
| Agent | 6 agent chuyên môn | **Script tất định** cho Discovery và On-chain; **LLM** cho Social, Project, Stock-Pair (diễn giải), Risk, tổng hợp | LLM chỉ được gọi khi có tín hiệu |
| X | API hoặc browser | **X-Lite**: link dự án → web search → web fetch; browser chỉ khi người dùng tự yêu cầu, chỉ đọc | Chi phí dữ liệu gần 0; điều khoản X hạn chế thu thập tự động; bảo vệ tài khoản X |
| Fomo | Nguồn khám phá | **Lớp chú ý**, không phải nguồn dữ liệu trung tâm | Số liệu của app phần lớn đến từ on-chain, đọc được qua API công khai |
| Lưu trữ | Normalized DB | SQLite cục bộ `~/.stock-token-scout/scout.db` | Đủ cho 5–20 ứng viên mỗi chu kỳ |

**Nguyên tắc chi phí:** API dữ liệu trả phí là đường nâng cấp, không phải phụ thuộc mặc định. Scout phải dùng hết dữ liệu on-chain công khai, link do dự án cung cấp, web search và thông tin công khai trước khi gọi nguồn trả phí.

**Chi phí AI tỉ lệ với thông tin mới**, không tỉ lệ với tổng dữ liệu đã quét: bằng chứng đã thấy (theo hash) và trang không đổi (theo hash) không bao giờ được đưa lại cho LLM.

## 2. Luồng dữ liệu

```
cron (6h) ─► scout_cycle.py ── DexScreener + GeckoTerminal ──► snapshot ─► diff ─► events
                   │ mã thoát 0: dừng, không tốn credit AI
                   │ mã thoát 10: có hàng đợi
                   ▼
        claude -p (headless) cho từng token trong queue.json
                   │
      ┌────────────┼──────────────────────────────┐
      ▼            ▼                              ▼
 onchain.py    X-Lite (web search/fetch)     ledger.py page (website/docs)
 [Blockscout]  → ledger.py evidence          → hash, chỉ trả phần thay đổi
      │            │ (chỉ mục MỚI)                │
      └────────────┼──────────────────────────────┘
                   ▼
   ledger.py bridge (attribution, luật cố định) + claim verify (đối chiếu on-chain)
                   ▼
            context.py (gói bối cảnh gọn) ─► LLM viết memo ─► context.py --mark-handled
                   ▼
   potential-assessor: chấm 6 tiêu chí + cờ đỏ (xếp loại do luật trong render_report.py tính)
                   ▼
   run_report.py complete ── cổng: memo đủ mục + scout-verdict hợp lệ ──► COMPLETE / INCOMPLETE / FAILED
                   ▼   (chờ MỌI token của lần chạy xong)
   run_report.py plan ── chọn 4–5 ứng viên DEEP theo điểm, còn lại BRIEF
                   ▼
   investor-memo-writer (chỉ token COMPLETE, gọi `gate` trước) ── đọc memo + `evidence` từ DB, không gọi mạng
                   ▼
   run_report.py render ── logo/link/bảng/loại trùng/rủi ro thoát hàng tối thiểu (tất định, có cache)
                   ▼
   ~/.stock-token-scout/reports/latest.html  ◄── deliverable duy nhất của lần chạy
```

## 3. Các module

| Module | Thực thi | Việc |
|---|---|---|
| Discovery | `scout_cycle.py` | Trending/pool mới, pool ghép stock chính chủ; event: `NEW_STOCK_PAIRED_POOL`, `NEW_CANDIDATE`, `LIQUIDITY_COLLAPSE` (kèm gợi ý nguyên nhân mức LIKELY/UNCONFIRMED), `LIQUIDITY_EXPANSION`, `VOLUME_ACCELERATION`, `PARTICIPANT_SURGE`, `HONEYPOT_PATTERN`, `FAKE_STOCK_PAIR` |
| On-chain | `onchain.py` | Pool, volume, ví mua/bán, R/S, holder, deployer, hợp đồng (verify, proxy, hàm quyền lực), mint/burn |
| Stock-Pair | `onchain.py` + LLM | Stock chính chủ, cảnh báo stock token giả, lệch giá giữa pool meme và pool stock/stablecoin, giờ thị trường Mỹ, issuer mint/burn, rủi ro đối tác |
| Claim | `ledger.py claim` | Tuyên bố off-chain (`paired_with`, `burn_mechanism`, `fixed_supply`, `lp_locked`, `stock_backed`, `team_allocation`, `contract_address`) được đối chiếu tự động với dữ liệu chuỗi |
| Social (X-Lite) | LLM + `ledger.py` | Tài khoản chính thức, creator, sự kiện, narrative; mọi thứ qua sổ bằng chứng |
| Project | LLM | Cơ chế token, nguồn cầu, cái gì tiêu thụ token, doanh thu đi đâu |
| Risk | LLM + luật | Thị trường, cấu trúc, hợp đồng, thanh khoản, đối tác, oracle, xã hội |
| Dữ liệu tải hộ | `fetched.py` + `common.get_json` | Khi môi trường chặn API: agent tải bằng web fetch / Blockscout MCP, lưu vào `~/.stock-token-scout/fetched/`; script đọc như API thật. `STS_OFFLINE=1` không chờ mạng; `scout_cycle.py` trả mã 3 nếu còn thiếu và chưa ghi gì vào kho |
| Chất lượng dữ liệu | `onchain.py`, `discover.py`, `run_report.py` | Kiểm chéo giá DexScreener với tỉ giá Blockscout (lệch > 20% thì cảnh báo), cảnh báo DexScreener cắt ở 30 cặp, ví EIP-7702 tính là ví cá nhân, PoolManager/hook launchpad/token tự giữ tính là hạ tầng; mục "Độ tin cậy dữ liệu" ở đầu HTML |
| Giao kết quả | `/report` | Chạy trọn pipeline không hỏi lại và giao đúng một file HTML; tin nhắn cuối ≤ 6 dòng, không kể quy trình |

## 4. Mức bằng chứng

| Mức | Nghĩa |
|---|---|
| `VERIFIED_ONCHAIN` | Đọc trực tiếp từ chuỗi hoặc API index của chuỗi |
| `VERIFIED_OFFCHAIN` | Hai kênh chính thức độc lập khớp nhau, hoặc có chữ ký ví |
| `LIKELY` | Một kênh chính thức |
| `UNCONFIRMED` | Chỉ nguồn yếu (nhắc tên, repost, bên thứ ba) |
| `CONFLICT` | Tuyên bố mâu thuẫn với dữ liệu on-chain hoặc với kênh chính thức khác |

Mức attribution do **luật trong `ledger.py`** tính, không do LLM tự gán. Quan hệ ví (ví A chuyển tiền cho ví B) không bao giờ được dùng làm bằng chứng danh tính.

## 5. Sự kiện được mô tả trước, nguyên nhân điều tra sau

Viết "phát hiện sự kiện thanh khoản giảm 51% trong 6 giờ", không viết "rug pull". Sau đó phân biệt: LP rút, chuyển pool/sàn, migration, đổi range thanh khoản tập trung, rút có chủ đích.

## 6. Agent trong Claude Code

| Agent | File | Công cụ |
|---|---|---|
| Discovery | `scout_cycle.py` (không phải LLM) | — |
| On-chain | `.claude/agents/onchain-analyst.md` | Bash, Read |
| Social (X-Lite) | `.claude/agents/social-researcher.md` | WebSearch, WebFetch, Bash, Read, Write |
| Project | `.claude/agents/project-analyst.md` | Bash, Read, WebFetch |
| Risk + memo | `.claude/agents/risk-synthesizer.md` | Bash, Read, Write |
| Chấm tiềm năng | `.claude/agents/potential-assessor.md` | Bash, Read, Edit |
| Investor Memo & Presentation (bước cuối) | `.claude/agents/investor-memo-writer.md` | Bash, Read, Write |
| Trạng thái lần chạy + HTML | `scout-reader/scripts/run_report.py` (không phải LLM) | — |

Điều phối bằng lệnh `/scout` (quét rồi điều tra), `/investigate [địa chỉ]`, `/present` (chạy lại riêng bước cuối) và `/verdict` (hỏi đáp về memo).

## 7. Đường nâng cấp (chỉ khi cần, có trả phí)

X API hoặc xAI X Search cho giám sát toàn thị trường; Bitquery/Dune cho cụm ví liên kết và lịch sử đầy đủ; Chainlink feed cho giá tham chiếu cổ phiếu; stream RPC nếu cần độ trễ tính bằng giây.

## 8. Giới hạn đã biết

- Event `NEW_STOCK_PAIRED_POOL` nghĩa là "mới với scout", không nhất thiết pool mới tạo: pool đã tồn tại lâu vẫn bị báo khi lần đầu lọt vào danh sách trending.
- Token tạo qua launchpad có deployer là hợp đồng factory; người tạo thật phải lấy từ giao dịch tạo token. Mọi token cùng launchpad dùng chung khuôn thanh khoản nên số liệu ban đầu giống nhau, không có nghĩa là cùng một người.
- GeckoTerminal giới hạn lượt gọi (HTTP 429); chu kỳ dày có thể thiếu số liệu, xem mục Technical Evidence trong báo cáo.

- Mẫu mint/burn chỉ gồm tối đa 150 lệnh chuyển gần nhất.
- Không phát hiện cụm ví liên kết; chưa đo sniper/ví mua sớm.
- Uniswap v4 để thanh khoản trong PoolManager, nên chưa đọc được sự kiện add/remove LP theo từng người.
- Giá tham chiếu cổ phiếu dùng pool stock/stablecoin sâu nhất trên chuỗi; Chainlink là bước nâng cấp.
- Ngưỡng event và điểm nhanh là heuristic.
- DexScreener `/token-pairs` trả tối đa 30 cặp mỗi stock token: memecoin ghép NVDA/SPY/META có thể bị bỏ sót nếu không lọt trending GeckoTerminal.
- Ở chế độ tải hộ, dữ liệu web fetch có thể trễ (cache); script kiểm chéo giá với Blockscout nhưng không tự sửa số liệu.
