# Changelog

## v2.4 (23/09/2026): giao đúng một file HTML, tự xử lý khi mạng bị chặn
- **Kết quả giao cho người dùng được viết vào skill.** Mọi yêu cầu kiểu "chạy / quét / đánh giá token / làm báo cáo" đều chạy trọn pipeline không hỏi lại và giao đúng một file HTML; tin nhắn cuối tối đa 6 dòng, không kể lại quy trình. Lệnh mới `/report`. Không có subagent (app Claude) thì agent tự đóng lần lượt từng vai.
- **Chế độ dữ liệu tải hộ.** `scripts/fetched.py` + lớp đọc trong `common.get_json`: khi proxy/Cloudflare chặn API, agent tải bằng web fetch và Blockscout MCP rồi lưu lại, script đọc như phản hồi API thật. `STS_OFFLINE=1` không chờ mạng; lỗi proxy/DNS được nhận diện ngay thay vì thử lại hàng phút; `scout_cycle.py` trả mã 3 khi còn thiếu dữ liệu và chưa ghi gì vào kho. Hướng dẫn: `references/data_fallback.md`.
- **Kiểm chất lượng dữ liệu tự động.** Giá DexScreener lệch tỉ giá Blockscout quá 20% thì cảnh báo; cảnh báo khi DexScreener cắt danh sách ở 30 cặp; báo cáo HTML có mục "Độ tin cậy dữ liệu của lần chạy" (thời điểm đo, token chưa có holder, nguồn thiếu, giá mâu thuẫn).
- **Holder trên Uniswap v4 tính đúng hơn.** Ví EIP-7702 (ví cá nhân dùng smart account) không còn bị tính là hợp đồng; PoolManager, hook khởi tạo Doppler và phần token tự giữ trong hợp đồng được tính là hạ tầng.
- **Phần kỹ thuật dễ đọc hơn.** "None" thành "chưa đọc được"; hợp đồng không đọc được ghi rõ "chưa kết luận về quyền owner" thay vì "hàm quyền lực: không thấy"; dòng nguồn chỉ liệt kê nguồn thực sự trả dữ liệu.
- **Quy tắc claim:** câu miễn trừ của dự án ("không đại diện cổ phần") không được ghi thành claim `stock_backed`.

## v2.3.1 (23/09/2026): vá 2 lỗi sinh event giả trong `scout_cycle.py`
- **LIQUIDITY_COLLAPSE giả khi pool rớt khỏi trending.** Thanh khoản tổng trước đây chỉ cộng những pool đang lọt danh sách trending/new của GeckoTerminal; pool rớt khỏi danh sách trông như thanh khoản sụt (mức 3, gọi Claude). Nay mọi token liên quan được bổ sung đủ pool từ DexScreener (`discover.complete_pools`), và không so thanh khoản khi số pool ít hơn lần trước (dấu hiệu nguồn dữ liệu thiếu).
- **VOLUME_ACCELERATION giả do đếm trùng vol 1h.** Một pool có thể xuất hiện ở trending 6h, 24h và new_pools; `vol1` trước đây cộng cả bản trùng (tới 3 lần) trong khi `vol24` đã gộp. Nay `vol1_usd` tính trong `summarize()` trên pool đã gộp.
- Dọn import thừa (`ledger.py`, `onchain.py`); `run_cycle.sh` dừng rõ ràng khi `cd` lỗi.
- Test hồi quy: `tests/test_fixes.py` mục 7.

## v2.3 (23/09/2026): vá lỗi phát hiện khi chạy thật trên Robinhood Chain
- **Pool bụi không còn được tính là ghép cổ phiếu.** Trước đây PONS (pool SPY $477, QQQ $982) và DELTA (pool AAPL $7) bị gắn nhãn "paired" và chen vào hàng đợi. Ngưỡng mặc định $5.000 (`STS_MIN_STOCK_PAIR_LIQ`).
- **Hàng đợi xếp theo điểm.** Cùng mức nghiêm trọng thì token điểm cao đứng trước, không còn ưu tiên event ghi sau cùng.
- **"Pool cổ phiếu mới" chỉ báo khi pool thật sự mới tạo** (≤ 72 giờ) và không phải pool bụi.
- **Luật chấm:** meme không có công dụng (điểm cơ chế ≤ 1) tối đa là ĐẦU CƠ THUẦN, dù thanh khoản cao.
- **Rủi ro thoát hàng tối thiểu** xét thêm mức sụt giá 7 ngày (≤ -50% → Trung bình, ≤ -75% → Cao).
- **Blockscout bị Cloudflare chặn:** ngắt mạch, một cảnh báo rõ ràng thay vì hàng loạt lỗi 403; holder lấy dự phòng từ GeckoTerminal (ghi rõ nguồn).
- **GeckoTerminal 429:** tôn trọng Retry-After, thử lại tối đa 5 lần.
- **Claim:** khi không đọc được hợp đồng/lệnh chuyển, ghi rõ "chưa kiểm được" thay vì "proxy hoặc chưa verify".
- Tên/ticker dự phòng từ DexScreener khi GeckoTerminal lỗi; giữ mọi pool ghép stock token để đối chiếu claim `paired_with`.
- Báo cáo HTML: nhãn cặp không còn cảnh báo sai với stablecoin; token bị kết luận DỪNG NGHIÊN CỨU không nằm trong dải "Ứng viên hàng đầu"; định dạng số.
- Thêm `tests/test_fixes.py`.

## v2.2
- Agent cuối **investor-memo-writer** (chỉ chạy khi `research_status = COMPLETE`), `run_report.py` (cổng COMPLETE, plan DEEP/BRIEF, gói bằng chứng, HTML duy nhất cho mỗi lần chạy), lệnh `/present`.

## v2.1
- Skill **scout-reader**: thang điểm 6 tiêu chí + cờ đỏ, xếp loại do luật tính, agent **potential-assessor**, lệnh `/verdict`, bảng HTML thư viện memo.
