---
description: Chạy trọn bộ nghiên cứu token Robinhood Chain và giao đúng một file HTML báo cáo cho nhà đầu tư (không cần người dùng hướng dẫn thêm)
---
Mục tiêu duy nhất: người dùng nhận **một file HTML** gồm nội dung nghiên cứu và các bảng đánh giá token. Không hỏi lại, không dừng giữa chừng, không giải thích quy trình.

Tham số tuỳ chọn `$ARGUMENTS`: một hoặc nhiều địa chỉ token (cách nhau bằng dấu phẩy). Chỉ có ticker thì tìm địa chỉ trên DexScreener trước; ticker trùng nhiều token thì chọn token có thanh khoản lớn nhất và ghi rõ trong báo cáo. Không có tham số thì quét cả chuỗi.

1. **Quét.** Có tham số: bỏ qua bước này. Không có: `python3 .claude/skills/stock-token-scout/scripts/scout_cycle.py --max-queue 5`.
   - Mã 2, hoặc cảnh báo proxy/DNS/Cloudflare: đặt `STS_OFFLINE=1` và làm theo `.claude/skills/stock-token-scout/references/data_fallback.md` (tải hộ bằng web fetch + Blockscout MCP, lưu bằng `fetched.py`), chạy lại tới khi ra mã 0 hoặc 10.
   - Mã 0 (không có tín hiệu): người dùng vẫn cần báo cáo. Chạy `python3 .claude/skills/stock-token-scout/scripts/discover.py --top 5 --json /tmp/sts_top.json`, rồi `python3 .claude/skills/scout-reader/scripts/run_report.py start --tokens <các địa chỉ trong rows[].address, cách nhau bằng dấu phẩy>` và làm tiếp bước 2 với lần chạy này (bỏ qua bước 0 "Mở lần chạy" của `/investigate` vì đã mở).
2. **Nghiên cứu.** Làm đúng lệnh `/investigate` (kèm `$ARGUMENTS` nếu có): on-chain, social, project, memo, chấm điểm, cổng COMPLETE, plan, investor memo, compare, `run_report.py render`. Không có subagent thì tự đóng từng vai theo thứ tự.
3. **Giao file.** Trong app Claude: sao chép `~/.stock-token-scout/reports/latest.html` sang thư mục outputs với tên `Robinhood_Token_Report_<YYYY-MM-DD>.html` rồi gửi file. Trong Claude Code: in đường dẫn file. Không gửi memo `.md`, JSON hay log.
4. **Tin nhắn cuối ≤ 6 dòng:** tên file; token nổi bật và xếp loại; cảnh báo mức 3 / CONFLICT / TRÁNH XA nếu có; một dòng giới hạn dữ liệu nếu có. Không kể lại các bước đã chạy.
