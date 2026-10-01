---
description: Điều tra hàng đợi của Stock Token Scout (hoặc một token nếu truyền địa chỉ), rồi dựng báo cáo HTML cho nhà đầu tư
---
Dùng skill stock-token-scout ở chế độ INVESTIGATE. Đặt `R=.claude/skills/scout-reader/scripts/run_report.py`.

**0. Mở lần chạy.** Có tham số thì `python3 $R start --tokens $ARGUMENTS`; không có thì `python3 $R start` (đọc `~/.stock-token-scout/queue.json`). Script tự loại token trùng.

**1. Nghiên cứu từng token** (các agent ở giai đoạn này không bao giờ là investor-memo-writer):
1. `python3 .claude/skills/stock-token-scout/scripts/context.py <TOKEN>`.
2. Token có event FAKE_STOCK_PAIR: chỉ viết memo ngắn về stock token giả, bỏ qua bước 3–4.
3. Giao cho `onchain-analyst` và `social-researcher` (có thể song song), rồi `project-analyst`.
4. Giao kết quả cho `risk-synthesizer` để viết memo và đánh dấu đã xử lý.
5. Giao memo cho `potential-assessor` để chấm tiềm năng (chèn khối `scout-verdict`).
6. Đóng cổng: `python3 $R complete --token <TOKEN> --memo <đường dẫn memo>`. Mã 1 nghĩa là memo chưa đủ (script ghi INCOMPLETE kèm lý do): sửa phần thiếu một lần rồi gọi lại; vẫn thiếu thì để nguyên. Điều tra hỏng giữa chừng: `python3 $R fail --token <TOKEN> --reason "<lý do>"`.

**2. Chọn ứng viên.** Khi mọi token đã COMPLETE / INCOMPLETE / FAILED: `python3 $R plan`. Mã 3 nghĩa là còn token chưa xong: quay lại bước 1. Script chọn 4–5 ứng viên DEEP theo điểm, còn lại BRIEF.

**3. Investor memo** (chỉ sau bước 2, chỉ cho token COMPLETE):
- Giao các token DEEP cho `investor-memo-writer` (mỗi lượt 1–2 token).
- Giao tất cả token BRIEF cho `investor-memo-writer` trong một lượt.
- Cuối cùng giao `compare` cho `investor-memo-writer`.

**4. Deliverable.** `python3 $R render`, rồi `python3 .claude/skills/scout-reader/scripts/render_report.py` (thư viện memo). Giao đúng một file `~/.stock-token-scout/reports/latest.html` (trong app Claude: sao chép sang thư mục outputs tên `Robinhood_Token_Report_<YYYY-MM-DD>.html` và gửi file). Memo `.md` chỉ là bằng chứng trung gian; không gửi cho người dùng, không viết thêm memo tổng hợp chu kỳ.

Không có subagent (app Claude): tự đóng từng vai theo đúng thứ tự trên. Mạng bị chặn: chế độ tải hộ theo `.claude/skills/stock-token-scout/references/data_fallback.md`.

Tin nhắn cuối tối đa 6 dòng, chỉ nêu: tên file, event mức 3, claim CONFLICT, token bị chấm TRÁNH XA, token có kết luận TIẾP TỤC NGHIÊN CỨU, và một dòng giới hạn dữ liệu nếu có. Không kể lại quy trình.
