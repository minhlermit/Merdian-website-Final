---
description: Đọc memo Stock Token Scout và trả lời dễ hiểu cho nhà đầu tư (một token, một file, hoặc cả thư mục)
---
Dùng skill scout-reader.

Đối tượng: `$ARGUMENTS` có thể là ticker, địa chỉ hợp đồng, đường dẫn một memo `.md`, hoặc một thư mục memo. Không có tham số thì dùng `~/.stock-token-scout/reports/`.

1. Chạy `python3 .claude/skills/scout-reader/scripts/render_report.py --json` (thêm `--dir <thư mục>` nếu cần).
2. Memo nào `UNRATED` vì thiếu khối `scout-verdict`: giao cho agent `potential-assessor` chấm, rồi chạy lại bước 1.
3. Trả lời theo "Mẫu câu trả lời cho nhà đầu tư" trong `.claude/skills/scout-reader/references/reading-guide.md`: một token thì dùng mẫu một token, nhiều token thì dùng bảng so sánh.
4. Chạy `python3 .claude/skills/scout-reader/scripts/render_report.py` và báo đường dẫn file `index.html` để người dùng mở bằng trình duyệt.
