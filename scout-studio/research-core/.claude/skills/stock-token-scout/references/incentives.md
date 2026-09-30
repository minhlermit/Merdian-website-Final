# Khung phân tích động cơ kinh tế

Câu hỏi gốc: **ai kiếm tiền, bằng cách nào, và hành động nào tối đa hoá lợi ích của họ?** Nếu hành động tối ưu của team hoặc holder lớn đi ngược lợi ích của holder nhỏ, dự án có vấn đề cấu trúc dù website đẹp đến đâu.

## Bước 1: Lập bảng các bên

Điền cho mọi bên có mặt. Mỗi ô phải có nhãn mức bằng chứng: `[VERIFIED_ONCHAIN]`, `[VERIFIED_OFFCHAIN]`, `[LIKELY]`, `[UNCONFIRMED]` hoặc `[CONFLICT]`.

| Bên | Kiếm tiền từ đâu | Kiếm nhiều nhất khi nào | Hành động tối ưu của họ | Cùng chiều với holder nhỏ? |
|---|---|---|---|---|
| Team / creator | Phí creator, token đang giữ, doanh thu sản phẩm | | | |
| Launchpad | Phí giao dịch | Volume cao, bất kể giá | Khuyến khích tạo token và giao dịch | Chỉ một phần |
| Ví sớm / sniper | Chênh lệch giá | Khi có người mua sau | Bán vào sóng tăng | Thường ngược |
| LP | Phí pool | Volume cao, giá ổn định | | |
| KOL / caller / clan trên app xã hội | Token được cấp hoặc mua trước | Khi người theo dõi mua vào | | Thường ngược |
| Nhà phát hành stock token | Phát hành thêm khi premium cao | Cầu stock token tăng | Mint thêm, kéo premium về | Trung lập |
| Arbitrageur | Premium/discount stock token | Thị trường Mỹ đóng cửa | San bằng giá | Trung lập |

## Bước 2: Dòng phí đi đâu

1. Phí mỗi giao dịch là bao nhiêu, chia cho ai (launchpad, creator, holder, burn)? Lấy từ tài liệu launchpad. **Các tỉ lệ thay đổi thường xuyên: luôn kiểm tra lại tại thời điểm viết.** Ví dụ đã ghi nhận trong nghiên cứu trước (cần xác minh lại): Pons thu 1% mỗi giao dịch và creator nhận phần lớn phí; Bankr có chia phí cho creator và agent; Flap cho phép trả cổ tức bằng stock token cho holder; LONG chuyển phí từ sản phẩm LongX về token $AI.
2. Phí nhận bằng tài sản gì: ETH, USDG, hay stock token? Phí bằng stock token làm treasury tích luỹ cổ phiếu, nhưng thuộc về ai là câu hỏi then chốt.
3. Phí được dùng để làm gì, và **có kiểm chứng on-chain được không**: buyback (có lệnh mua từ ví treasury?), chia cổ tức (có hợp đồng phân phối?), hay nằm im trong ví creator?

## Bước 3: Tỉ lệ động cơ của team (định lượng)

```
Thu nhập phí năm ước tính = Vol 24h × phí giao dịch × tỉ lệ creator nhận × 365
Giá trị token team giữ   = % team giữ × FDV (hoặc × vốn hoá lưu hành)
Tỉ lệ động cơ            = Thu nhập phí năm / Giá trị token team giữ
```

- **Tỉ lệ rất cao (> 1):** team kiếm tiền chủ yếu từ volume, không cần giá tăng. Động cơ là kích volume, kể cả volume ảo. Đối chiếu với vòng quay và lệnh trung bình ở metrics.md.
- **Tỉ lệ thấp, team giữ nhiều token không khoá:** động cơ là đẩy giá rồi bán. Kiểm tra lịch sử chuyển đi của deployer/creator.
- **Team giữ ít, thu nhập phí thấp, có doanh thu sản phẩm:** gần mô hình doanh nghiệp nhất. Khi đó hỏi tiếp: doanh thu có quay về token không (burn, buyback, chia)?

Ghi rõ đây là ước tính thô vì volume dao động mạnh và tỉ lệ phí có thể sai.

## Bước 4: Liên kết cổ phiếu là loại gì

| Loại | Holder được gì | Rủi ro chính |
|---|---|---|
| Chỉ ghép cặp | Giá theo cổ phiếu qua pool, không có quyền đòi | Người bán rút stock token ra khỏi pool, LP chịu thiệt |
| Phí/cổ tức bằng stock token | Dòng tiền thật | Càng giống chứng khoán về pháp lý; phụ thuộc hợp đồng phân phối |
| Tuyên bố quy đổi/bảo chứng | Quyền đòi, nếu có thật | Nếu không mô tả được cơ chế redeem thì đây là **quảng cáo gây hiểu lầm** |

"Được backed bởi NVDA" mà thực chất chỉ ghép cặp là red flag nghiêm trọng về độ trung thực của team.

## Bước 5: Ai là thanh khoản thoát hàng

Theo dõi dòng người mua mới: app xã hội (fomo, clan copy trading), KOL, listing. Nếu tăng trưởng holder đến chủ yếu từ một kênh copy trading, dòng tiền tập trung và rút ra cũng tập trung.

## Red flags (liệt kê trong báo cáo nếu gặp)

- Dùng tên, logo Robinhood như thể chính chủ, hoặc nói có "token chính thức của Robinhood Chain" (không tồn tại)
- Ghép cặp với stock token không nằm trong danh sách trắng
- Website không ghi địa chỉ hợp đồng, hoặc ghi sai
- Team ẩn danh hoàn toàn và giữ > 5% không khoá
- Hứa lợi nhuận, cổ tức cố định
- Tỉ lệ động cơ > 1 cùng vòng quay > 40x
