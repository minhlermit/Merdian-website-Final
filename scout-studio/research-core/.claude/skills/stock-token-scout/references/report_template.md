# Mẫu research memo

Viết bằng ngôn ngữ người dùng dùng (mặc định tiếng Việt). **Mọi khẳng định có nhãn mức bằng chứng:** `[VERIFIED_ONCHAIN]`, `[VERIFIED_OFFCHAIN]`, `[LIKELY]`, `[UNCONFIRMED]`, `[CONFLICT]`. Số liệu giữ nguyên từ script, không làm tròn lại theo ý.

## Memo điều tra một token

```
# [TICKER]: [tên dự án]
*[địa chỉ hợp đồng] | [UTC] | Xếp loại: THEO DÕI SÁT / THEO DÕI / BỎ QUA | Lần trước: [xếp loại cũ hoặc "mới"]*

## Kết luận nhanh
[3 câu: dự án là gì; động cơ kinh tế có cùng chiều holder nhỏ không; điều gì sẽ làm đổi đánh giá]

## Sự kiện kích hoạt
[event từ scout_cycle, mô tả sự kiện trước rồi mới đến giả thuyết nguyên nhân]

## Dự án
- Loại: [stock-paired / utility mint-burn / AI credit / DeFi primitive / meme thuần / khác]
- Use case tự nhận: ... [VERIFIED_OFFCHAIN hoặc UNCONFIRMED]
- Cơ chế utility và mint/burn: ... đối chiếu: ... [VERIFIED_ONCHAIN / CONFLICT]
- Cầu token đến từ đâu; cái gì tiêu thụ token; ai nhận doanh thu

## Cấu trúc thị trường
| Chỉ số | Giá trị | Đọc thế nào |
[tuổi, pool chính, quote asset, thanh khoản, volume, vòng quay, ví mua/bán, FDV/thanh khoản, tách R/S]

## Sở hữu
[số holder, top 10 ví thường, ví lớn nhất, hợp đồng trong top 20, deployer đang giữ / đã chuyển, xu hướng so với lần trước]

## Hành vi ví
[mint/burn trong mẫu, ví đốt duy nhất, dấu hiệu bot (lệnh trung bình nhỏ, vòng quay cao), các giới hạn đo lường]

## Xã hội và danh tính
- Tài khoản dự án: @... [mức]
- Creator: @... [mức] (bằng chứng: ...)
- Ví ↔ creator: [mức; thường là UNCONFIRMED]
- Sự kiện mới: ...
- Narrative: [claim, lần đầu thấy, số tài khoản độc lập, có thay đổi on-chain tương ứng không]

## Stock-pair (nếu có)
- Stock token chính chủ? [VERIFIED_ONCHAIN / CONFLICT]
- Ticker cơ sở, địa chỉ hợp đồng
- Giá ngầm định trong pool so với pool stock/stablecoin sâu nhất; thị trường Mỹ đang mở hay đóng
- Tỉ lệ stock token bị khoá; issuer có mint/burn gần đây không
- Nhắc: ghép cặp ≠ bảo chứng; rủi ro đối tác của nhà phát hành

## Claim đã đối chiếu
| Claim | Nguồn | Kết quả | Chi tiết |
[từ `ledger.py claim verify`]

## Động cơ kinh tế
[bảng các bên + tỉ lệ động cơ team, theo incentives.md]

## Cờ rủi ro
- Thị trường / Cấu trúc / Hợp đồng / Thanh khoản / Đối tác / Oracle / Xã hội: [mỗi nhóm một dòng, "không thấy" nếu không có]

## Điều kiện đánh giá lại
[3–5 điều đo được, ví dụ "top 10 ví thường vượt 35%", "vòng quay > 40x hai chu kỳ liên tiếp"]

## Đánh giá tiềm năng (thẳng thắn)
[Do agent potential-assessor viết sau khi memo xong, theo skill scout-reader (references/scorecard.md).
Gồm dòng xếp loại, bảng 6 tiêu chí, kịch bản tốt/xấu nhất, phản biện, và khối ```scout-verdict ... ``` dạng JSON.
risk-synthesizer để trống mục này.]

## Nguồn
[link]

*Tài liệu nghiên cứu, không phải khuyến nghị đầu tư.*
```

## Memo tổng hợp một chu kỳ

```
# Scout Robinhood Chain: [UTC]
## Cảnh báo (chỉ khi có event mức 3, claim CONFLICT, hoặc đổi xếp loại)
## Đã điều tra
| Token | Event | Xếp loại theo dõi | Đánh giá tiềm năng | Thay đổi so với lần trước | File memo |
## Token giả mạo stock (FAKE_STOCK_PAIR)
## Giới hạn của chu kỳ này
```

## Quy tắc xếp loại

Memo có hai xếp loại, trả lời hai câu hỏi khác nhau:
- **Xếp loại theo dõi** (dưới đây, risk-synthesizer ghi): token có đáng để scout theo dõi tiếp không.
- **Đánh giá tiềm năng** (potential-assessor chấm, luật trong `scout-reader/scripts/render_report.py` tính): dự án chất lượng tới đâu, viết cho người đọc cuối.

Một token có thể THEO DÕI SÁT (đang có biến động lớn cần theo dõi) mà vẫn là ĐẦU CƠ THUẦN.

- **THEO DÕI SÁT:** liên kết cổ phiếu trung thực (hoặc cơ chế utility có dùng thật), claim quan trọng không `CONFLICT`, holder đang loãng ra, không có red flag nghiêm trọng.
- **THEO DÕI:** có điểm tốt nhưng còn ít nhất một câu hỏi lớn chưa trả lời.
- **BỎ QUA:** có `CONFLICT` ở claim cốt lõi, stock token giả, hoặc động cơ team ngược chiều holder rõ ràng.

Không dùng từ "mua", "bán", "nên vào lệnh", mục tiêu giá.
