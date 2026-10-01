# X-Lite: lớp thông tin off-chain gần như miễn phí

X trong skill này **không** dùng để đọc tài khoản dự án cho có. X là lớp tình báo off-chain với ba việc:

| Lớp | Tìm gì | Ví dụ đầu ra |
|---|---|---|
| **Đồ thị danh tính** | Creator, founder, team, dự án cũ | @creatorA → Orbit; trước đó làm dự án B |
| **Sự kiện** | Launch, cập nhật sản phẩm, tích hợp, đổi cơ chế token, sự cố | "AI credits launched 2h ago" |
| **Narrative** | Dự án đang được kể thế nào, bởi ai, lan nhanh ra sao | "burn token → AI credits", lần đầu từ tài khoản dự án, sau đó 7 tài khoản độc lập nhắc lại |

**Không làm "sentiment score = 73% bullish".** Con số đó tạo độ chính xác giả. Thay vào đó, ghi claim cụ thể, ai nói đầu tiên, bao nhiêu tài khoản độc lập lặp lại, rồi đem claim về đối chiếu on-chain.

## Công cụ theo thứ tự chi phí

1. **Link do dự án cung cấp** (DexScreener/GeckoTerminal profile, website, launchpad). Miễn phí, đáng tin nhất cho điểm khởi đầu.
2. **Web search có trọng tâm.** Bài và hồ sơ công khai trên X thường xuất hiện trong kết quả tìm kiếm bên ngoài.
3. **Web fetch** trang dự án, docs, bài báo.
4. **Trình duyệt (Claude in Chrome)**: chỉ khi người dùng tự yêu cầu trong phiên tương tác, chỉ đọc, số lượt ít. Điều khoản của X hạn chế thu thập tự động, nên không dùng trình duyệt để cào X theo lịch; người chịu rủi ro là tài khoản của người dùng.
5. **X API / xAI X Search**: đường nâng cấp có trả phí, chỉ khi cần giám sát toàn thị trường. Không dùng mặc định.

## Truy vấn mẫu (điều chỉnh theo dự án, tối đa khoảng 6 mỗi chu kỳ)

```
"<tên dự án>" "<địa chỉ hợp đồng>"
"<tên dự án>" <ticker> Robinhood Chain
site:x.com <handle dự án>
"<tên dự án>" founder OR "built by" OR team
"<handle creator>" launch OR token OR rug
"<tên dự án>" <cơ chế tuyên bố, ví dụ "AI credits" hoặc "paired with NVDA">
```

Ưu tiên truy vấn có địa chỉ hợp đồng, vì ticker trùng nhau rất nhiều.

## Lưu và loại trùng (bắt buộc trước khi phân tích)

Ghi mọi kết quả liên quan vào file JSON rồi nạp vào sổ:

```json
[
  {"url": "https://x.com/proj/status/123", "source": "x", "category": "identity",
   "author": "@proj", "posted_at": "2026-09-22", "text": "Built by @creatorA. CA: 0x..."},
  {"url": "https://example-news.com/abc", "source": "news", "category": "event",
   "author": "Tên báo", "posted_at": "2026-09-21", "text": "tóm tắt 1-2 câu bằng lời của bạn"}
]
```

```bash
python3 scripts/ledger.py evidence add-batch --token 0xT --file /tmp/items.json
```

Kết quả trả về `new_items`. **Chỉ phân tích các mục mới.** Mục đã thấy (cùng URL hoặc cùng nội dung) bị bỏ qua, nên chu kỳ sau không tốn credit đọc lại. `category` nhận: `identity`, `event`, `narrative`, `claim`, `product`. Với bài báo, ghi tóm tắt ngắn bằng lời của bạn, không chép nguyên văn.

## Biến bằng chứng thành cầu nối và claim

- Bài của tài khoản dự án nêu tên creator → `bridge add --subject creator --type project_names_creator`.
- Creator tự đăng "I launched X" kèm địa chỉ → `creator_self_claim_with_contract`.
- Tài khoản dự án đăng địa chỉ hợp đồng → `bridge add --subject project --type x_links_contract`.
- Dự án tuyên bố cơ chế ("burn để lấy credit", "paired with NVDA", "team giữ 5%") → `claim add` rồi `claim verify`.

Chi tiết loại cầu nối và luật tính mức tin cậy nằm trong `attribution.md`.

## Mẫu nối X với blockchain (đây mới là giá trị)

```
CLAIM          Token được tiêu thụ để lấy credit AI.            [VERIFIED_OFFCHAIN]
MECHANISM      Có lệnh burn trên chuỗi.                          [VERIFIED_ONCHAIN]
ADOPTION       23 ví duy nhất đã đốt trong mẫu gần nhất.         [VERIFIED_ONCHAIN]
INTERPRETATION Utility đã chạy nhưng mức dùng còn hạn chế.       [LIKELY]
```

```
CLAIM          "ABC launched paired with NVDA"                   [VERIFIED_OFFCHAIN]
POOL           ABC / 0xd060...9EEC                               [VERIFIED_ONCHAIN]
QUOTE ASSET    Stock token NVDA chính chủ của Robinhood          [VERIFIED_ONCHAIN]
```

Nếu quote asset chỉ là token ngẫu nhiên tên NVDA: **tuyên bố của creator mâu thuẫn với dữ liệu chuỗi** → `CONFLICT`.

## Narrative: đo gì cho có ích

- Claim cốt lõi của narrative (một câu).
- Lần đầu thấy: ai, khi nào (từ `posted_at`).
- Số tài khoản **độc lập** nhắc lại. Tài khoản của team, tài khoản mới tạo, tài khoản đăng cùng câu chữ không tính là độc lập.
- On-chain có thay đổi tương ứng không (holder, burn, volume sau thời điểm công bố).
- Dấu hiệu phối hợp: nhiều tài khoản đăng gần như cùng nội dung trong thời gian ngắn → red flag xã hội.
