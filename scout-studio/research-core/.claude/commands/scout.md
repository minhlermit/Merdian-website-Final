---
description: Chạy một chu kỳ quét Stock Token Scout rồi điều tra nếu có tín hiệu
---
1. Chạy `python3 .claude/skills/stock-token-scout/scripts/scout_cycle.py --max-queue 5`.
2. Mã thoát 0: báo "không có tín hiệu đủ mạnh" và dừng. Mã thoát 2: báo lỗi dữ liệu kèm cảnh báo mạng và dừng.
3. Mã thoát 10: làm theo lệnh /investigate cho hàng đợi.
4. Không lấy được dữ liệu vì môi trường chặn API: không dừng, chuyển sang chế độ tải hộ (`.claude/skills/stock-token-scout/references/data_fallback.md`).
5. Muốn chạy một mạch ra file HTML cho người dùng: dùng `/report`.
