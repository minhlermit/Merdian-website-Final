# Định nghĩa và cách đọc chỉ số định lượng

Các ngưỡng dưới đây là **heuristic để xếp hạng và đặt câu hỏi**, chưa được kiểm định thống kê trên Robinhood Chain (chuỗi mới chạy từ 01/07/2026). Khi viết báo cáo, luôn ghi rõ đây là ngưỡng tham khảo, không phải chuẩn.

## Mục lục
1. Pool và thanh khoản
2. Volume và hành vi giao dịch
3. Tách lợi nhuận meme / cổ phiếu
4. Holder và team
5. Tổ hợp tín hiệu thường gặp

---

## 1. Pool và thanh khoản

| Chỉ số | Công thức | Cách đọc |
|---|---|---|
| Thanh khoản tổng | Tổng `liquidity.usd` của mọi pool | Dưới ~20k USD: một lệnh vài trăm USD đã làm lệch giá. Trên ~250k USD: đủ sâu để đo hành vi |
| Tỉ trọng pool chính | Vol pool lớn nhất / tổng vol | > 90%: thị trường phụ thuộc một pool, rút thanh khoản pool đó là chết |
| FDV / thanh khoản | FDV / thanh khoản tổng | > 50x: định giá "trên giấy" rất lớn so với tiền thật trong pool; bán vài % nguồn cung là sập giá |
| Stock token bị khoá | Lượng stock token trong pool / nguồn cung on-chain của stock token đó | Chỉ số riêng của mảng ghép cặp. Tỉ lệ cao nghĩa là memecoin đang hút nguồn cung cổ phiếu token, dễ đẩy premium của stock token (vụ BONER/HIMS) |

Lưu ý Uniswap v4: pool không phải một hợp đồng riêng mà nằm trong PoolManager, nên lượng token trong pool lấy từ `liquidity.base/quote` của DexScreener, không lấy từ số dư địa chỉ.

## 2. Volume và hành vi giao dịch

| Chỉ số | Công thức | Cách đọc |
|---|---|---|
| Vòng quay 24h | Vol 24h / thanh khoản | 0,5–10x: sôi động bình thường. > 40x: nghi wash trading hoặc bot vòng tròn. Trước khi hết trợ giá gas (cuối 09/2026), bot spam rẻ nên ngưỡng này dễ bị vượt |
| Tỉ lệ bán | Lệnh bán / tổng lệnh | 35–60% là cân bằng. Dưới 15% khi có nhiều lệnh mua: nghi honeypot hoặc hạn chế bán |
| Ví mua / ví bán duy nhất | Từ GeckoTerminal | Thước đo tham gia tốt hơn số lệnh vì một bot có thể tạo hàng nghìn lệnh |
| Lệnh trung bình | Vol / tổng lệnh | Rất nhỏ (vài USD) cùng số lệnh rất lớn: dấu hiệu bot tăng số giao dịch |
| Tăng tốc volume | Vol 1h / (Vol 24h / 24) | > 3x: có sự kiện đang diễn ra (listing, KOL gọi, tin tức). Kiểm tra nguyên nhân trước khi diễn giải |

## 3. Tách lợi nhuận meme / cổ phiếu

Với token ghép cặp: `P = R × S`, trong đó R là số stock token đổi được một token, S là giá USD của stock token.

- `R_chg` là phần do cộng đồng/cầu memecoin tạo ra.
- `S_chg` là beta cổ phiếu mà holder nhận thụ động.
- Một token "tăng 70% trong tuần" mà S tăng 60% thì cộng đồng gần như không tạo giá trị. Ngược lại R tăng mạnh trong tuần cổ phiếu đi ngang mới là tín hiệu cầu thật.
- Khi thị trường Mỹ đóng cửa, S trên chain có thể lệch khỏi giá tham chiếu; phần "cổ phiếu" lúc đó lẫn cả premium/discount của stock token.

## 4. Holder và team

| Chỉ số | Cách đọc |
|---|---|
| Top 10 trừ hạ tầng | Đã loại địa chỉ burn và pool. Trên ~50%: giá phụ thuộc vài ví |
| Top 10 ví thường (EOA) | Loại thêm hợp đồng (locker, vault, launchpad). Gần với "người thật có thể bán" nhất |
| Ví thường lớn nhất | Trên ~5% ở token vốn hoá nhỏ là rủi ro xả hàng đáng kể |
| Hợp đồng trong top 20 | Phải xác định từng cái: locker (tốt nếu khoá thật), vault chia cổ tức, hay ví multisig của team (cần xem ai ký) |
| Holder/ngày | Từ lần chạy trước (cache). Tăng đều cùng top 10 giảm dần là dấu hiệu phân phối lành mạnh |
| Deployer là hợp đồng | Token tạo qua launchpad factory; ví team thật phải lấy từ trang launchpad hoặc sự kiện tạo token |
| Deployer đã chuyển đi | % nguồn cung deployer đã chuyển ra. Chuyển cho nhiều ví mới lập có thể là chia ví để che tập trung |

Giới hạn: script đọc tối đa 100 holder lớn nhất. Không phát hiện được cụm ví liên kết (một người nhiều ví). Muốn làm sâu hơn, dùng Bitquery hoặc Dune để nối nguồn tiền nạp của các ví top.

## 5. Tổ hợp tín hiệu thường gặp

| Tổ hợp | Diễn giải thận trọng |
|---|---|
| Vòng quay rất cao + lệnh trung bình rất nhỏ + ví mua ít | Volume ảo; creator có thể đang tự giao dịch để ăn phí |
| R tăng + holder tăng đều + top 10 giảm | Cầu thật, phân phối đang loãng ra |
| Giá tăng nhưng R đi ngang | Chỉ ăn theo cổ phiếu, chưa có câu chuyện riêng |
| FDV/thanh khoản cao + ví thường lớn nhất > 5% | Một lệnh bán là đủ phá giá |
| Stock token bị khoá tỉ lệ cao + cuối tuần | Premium stock token dễ phình, rủi ro kép khi thị trường mở cửa lại |
