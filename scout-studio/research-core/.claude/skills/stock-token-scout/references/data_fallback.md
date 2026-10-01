# Chế độ dữ liệu tải hộ (khi script không gọi thẳng được API)

Dùng khi `scout_cycle.py` trả mã 2, hoặc cảnh báo có "không truy cập được (proxy/DNS)", "Cloudflare 403", "STS_OFFLINE". Hay gặp trong app Claude (Cowork), máy công ty có proxy, hoặc VPS bị Blockscout chặn.

**Không hỏi người dùng, không dừng lại giải thích.** Tự chuyển sang chế độ này và chạy tiếp tới báo cáo HTML. Chỉ báo cho người dùng khi không lấy được bất kỳ dữ liệu thị trường nào.

## Nguyên lý

Script vẫn là nơi tính toán, chấm điểm và dựng HTML. Agent chỉ làm "người đưa thư": tải phản hồi API bằng công cụ của mình và lưu lại bằng `scripts/fetched.py`. Script đọc dữ liệu đó như phản hồi API thật (`~/.stock-token-scout/fetched/`, hết hạn sau 6 giờ, đổi bằng `STS_FETCHED_MAX_AGE_H`).

## Quy trình

```bash
S=.claude/skills/stock-token-scout/scripts
export STS_OFFLINE=1                       # không chờ mạng; GeckoTerminal tự bỏ qua (STS_SKIP_HOSTS)
python3 $S/scout_cycle.py --max-queue 5    # mã 3 = còn thiếu dữ liệu, CHƯA ghi gì vào kho
python3 $S/fetched.py missing --clear      # danh sách URL cần tải, kèm cách tải
#   ... agent tải từng URL (bảng dưới) và lưu bằng fetched.py put-* ...
python3 $S/scout_cycle.py --max-queue 5    # lặp tới khi ra mã 0 hoặc 10
```

Vòng thứ hai đòi `token-pairs` của 10 ứng viên có thanh khoản cặp cổ phiếu lớn nhất (`STS_COMPLETE_TOP`), vì thiếu pool thì điểm và thanh khoản bị tính sai (token lớn nhất có thể rơi khỏi hàng đợi). Pool của các ứng viên còn lại là tuỳ chọn: `fetched.py missing` liệt kê ở mục `optional`, không cần tải.

Sau khi có hàng đợi: chạy `onchain.py <token>` cho từng token, xem `fetched.py missing`, tải những gì ngân sách cho phép (thứ tự ưu tiên ở dưới), lưu, rồi chạy lại `onchain.py <token>` một lần. Phần không tải được (deployer, lệnh chuyển, mã hợp đồng) cứ để trống: script ghi "chưa đọc được", báo cáo không kết luận thay. Sau đó làm tiếp INVESTIGATE như bình thường.

## Tải từng nguồn thế nào

| Nguồn | Công cụ | Lưu bằng | Ghi chú |
|---|---|---|---|
| DexScreener `token-pairs/v1/robinhood/<addr>` | web fetch | `fetched.py put-dex --url <URL gốc> --file lines.txt` | Yêu cầu web fetch trả **dòng rút gọn 22 trường** (xem `fetched.py --help`) và dòng cuối `TOTAL=<số phần tử>` để biết có bị cắt không. |
| Blockscout `/tokens/<addr>` | Blockscout MCP `direct_api_call`, chain `4663` | `fetched.py put-token --token <addr> --supply <total_supply> --holders <holders_count> --exchange-rate <exchange_rate>` | Luôn ghi `exchange_rate` nếu có: script dùng nó để kiểm chéo giá. |
| Blockscout `/tokens/<addr>/holders` | Blockscout MCP `direct_api_call` | `fetched.py put-holders --token <addr> --file holders.txt` | 25 dòng đầu là đủ. Dòng: `address|is_contract|proxy_type|name|value`. Giữ nguyên `proxy_type` (ví `eip7702` là ví cá nhân). |
| GeckoTerminal | thường bị chặn (robots) | bỏ qua | Thiếu lịch sử giá 7 ngày và số ví mua/bán; báo cáo tự ghi rõ. |
| Website dự án, tin tức | web fetch, web search | `ledger.py evidence add-batch` | Như X-Lite bình thường. |

### Ngân sách Blockscout MCP

Gói miễn phí chỉ có khoảng 8 lượt gọi mỗi phiên. Dùng theo thứ tự ưu tiên:
1. `/tokens/<addr>` cho mọi token trong hàng đợi (số holder, tổng cung, tỉ giá).
2. `/tokens/<addr>/holders` cho các token có điểm định lượng cao nhất.
3. Còn dư mới gọi `/addresses/<addr>` (deployer) hay `/smart-contracts/<addr>` (quyền hợp đồng).

Token nào không kịp lấy holder thì cứ để thiếu: luật chấm để `distribution = null`, báo cáo ghi "chưa đo được", không đoán.

## Bẫy dữ liệu đã gặp (bắt buộc làm theo)

1. **Dữ liệu web fetch có thể cũ.** Web fetch có cache, và DexScreener cũng có thể trả bản cũ. Thêm tham số chống cache `?t=<unix time>` vào URL khi tải (vẫn lưu bằng URL gốc không có `?t=`). Sau khi lưu, so giá với `exchange_rate` của Blockscout: `onchain.py` tự cảnh báo khi lệch quá 20%. Nếu lệch, tải lại DexScreener một lần; vẫn lệch thì để nguyên, báo cáo sẽ ghi.
2. **Tất cả số liệu của một token phải lấy cùng một lượt.** Không trộn cặp stock của lần tải đầu với danh sách pool của lần tải sau: nếu tải lại một token, cập nhật cả dòng của token đó trong file cặp của stock token.
3. **DexScreener trả tối đa 30 cặp mỗi stock token.** Với NVDA, SPY, META…, memecoin ghép cặp có thể bị cắt khỏi danh sách. `discover.py` tự cảnh báo; khi web fetch lọc hộ, luôn đếm lại (`TOTAL=`) và kiểm tra các cặp có thanh khoản lớn nhất không bị bỏ sót.
4. **Web fetch lọc bằng mô hình nhỏ có thể trả sai "NONE".** Khi kết quả rỗng bất thường, hỏi lại dạng liệt kê `base/quote + liquidity` cho toàn bộ mảng rồi mới lọc.
5. **Chỉ lưu dữ liệu đã tải được, không suy ra.** Không tự tính tổng cung từ FDV/giá, không điền số holder từ bài báo vào `put-token`. Số liệu từ bài báo đi vào sổ bằng chứng với nhãn `UNCONFIRMED`.
