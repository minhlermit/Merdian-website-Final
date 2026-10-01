---
description: Chạy lại riêng bước cuối (investor memo + HTML) cho lần chạy Scout hiện tại, không nghiên cứu lại
---
Đặt `R=.claude/skills/scout-reader/scripts/run_report.py`. Tham số tuỳ chọn: run id (`$ARGUMENTS`), thêm `--run <id>` vào mọi lệnh nếu có.

1. `python3 $R status`. Token nào chưa COMPLETE thì giữ nguyên: bước này không nghiên cứu thêm.
2. `python3 $R plan`. Mã 3: báo token nào chưa xong và dừng.
3. Token COMPLETE có `investor_status` khác DONE: giao cho `investor-memo-writer` (DEEP 1–2 token mỗi lượt, BRIEF gộp một lượt), rồi `compare`.
4. `python3 $R render`, rồi giao file HTML (trong app Claude: sao chép sang thư mục outputs và gửi file). Tin nhắn kèm theo tối đa 6 dòng.
