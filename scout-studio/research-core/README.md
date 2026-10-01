# Robinhood Token Research & Evaluation (v2.4)

**Bộ skill nghiên cứu và đánh giá token trên Robinhood Chain**: tìm token ghép cặp cổ phiếu, điều tra on-chain và web, chấm tiềm năng bằng luật cố định, và xuất một báo cáo HTML cho nhà đầu tư mỗi lần chạy. Tên nội bộ của pipeline là Stock Token Scout.


> *English summary:* Stock Token Scout scans Robinhood Chain (chain 4663) every few hours for tokens paired with tokenized stocks (NVDA, TSLA, COIN…), investigates the interesting ones on-chain and on the web, and produces **one self-contained HTML investor report per run**: a comparison dashboard, full investment memos for the top 4–5 candidates, and honest "no sustainable-growth thesis" conclusions when the evidence doesn't support one. Deterministic Python does discovery, metrics, deduplication and rendering; Claude is only called when there is a signal, and only for reasoning. Research only, not financial advice. Docs are in Vietnamese.

---

## Nó làm gì

```
cron (6 giờ) → quét on-chain (miễn phí) → có tín hiệu? ─ không → dừng, 0 credit AI
                                              └ có → Claude điều tra từng token
                                                     → chấm tiềm năng bằng thang điểm cố định
                                                     → agent cuối viết investor memo cho token đã nghiên cứu xong
                                                     → 1 file HTML cho cả lần chạy
```

Mỗi lần chạy cho ra **`~/.stock-token-scout/reports/latest.html`**, gồm:
- **Bảng so sánh** mọi token đã xét: thanh khoản, holder, xếp loại tiềm năng, tăng trưởng bền vững, rủi ro thoát hàng, kết luận.
- **Memo đầy đủ cho 4–5 ứng viên hàng đầu**:
  - dự án giải quyết vấn đề gì; sản phẩm thật là gì; công nghệ và lợi thế
  - creator là ai, đang nói gì
  - người dùng đến từ đâu và vì sao quay lại; doanh thu
  - token có nắm được giá trị không; vòng tăng trưởng có bền không; traction; moat
  - thanh khoản và rủi ro thoát hàng; phân tích cặp cổ phiếu
  - catalyst và điều kiện làm luận điểm mất hiệu lực
  - một đoạn kết luận ngắn
- **Đánh giá rút gọn** cho token còn lại, và danh sách token chưa nghiên cứu xong (kèm lý do).
- Phần **Technical Evidence** thu gọn: địa chỉ hợp đồng, claim ledger, danh tính, lỗi API.

Memo `.md` trong thư mục `reports/` chỉ là bằng chứng trung gian.

## Nó KHÔNG làm gì

- Không giao dịch, không giữ private key, không ký gì.
- Không khuyên mua bán, không mục tiêu giá. Script từ chối memo có những cụm như "nên mua", "x10", "mục tiêu giá".
- Không cào X bằng trình duyệt, không dùng X API trả phí.
- Không tự nâng đánh giá: xếp loại, giới hạn kết luận và mức rủi ro thoát hàng tối thiểu do **luật trong code** tính từ dữ liệu. AI không nâng được bằng lời văn.

## Yêu cầu

- macOS hoặc Linux (Windows: dùng WSL)
- Python 3.9+ (chỉ thư viện chuẩn, không cần `pip install`)
- [Claude Code](https://claude.com/claude-code) đăng nhập bằng tài khoản Claude (Pro/Max) hoặc API key
- Mạng tới `api.dexscreener.com`, `api.geckoterminal.com`, `robinhoodchain.blockscout.com`

## Cài đặt (macOS, khoảng 10 phút)

**1. Giải nén vào thư mục nhà**, không để trên Desktop (macOS chặn cron đọc Desktop), và tránh tên thư mục có dấu cách:

```bash
mv ~/Downloads/robinhood-token-research ~/robinhood-token-research
mkdir -p ~/.stock-token-scout
cd ~/robinhood-token-research
```

**2. Kiểm thử không cần mạng.** Phải in ra 4 dòng `PASSED`:

```bash
python3 tests/test_pipeline.py && python3 tests/test_reader.py && python3 tests/test_run_report.py && python3 tests/test_fixes.py
```

**3. Cài Claude Code và thêm vào PATH:**

```bash
curl -fsSL https://claude.ai/install.sh | bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
which claude          # phải in ra đường dẫn, ví dụ /Users/<bạn>/.local/bin/claude
claude                # đăng nhập một lần, xong gõ /exit (bên trong Claude Code)
```

**4. Đối chiếu danh sách stock token chính chủ:** `.claude/skills/stock-token-scout/references/stock_tokens.json` với trang Token Contracts trong tài liệu Robinhood Chain. Muốn sửa thì đặt bản của bạn ở `~/.stock-token-scout/stock_tokens.json`.

**5. Chạy thử toàn bộ một lần:**

```bash
bash ~/robinhood-token-research/.claude/skills/stock-token-scout/scripts/run_cycle.sh
open ~/.stock-token-scout/reports/latest.html
```

Khi có tín hiệu, phần Claude chạy ngầm 5–15 phút và không in gì cho tới khi xong. Đừng đóng cửa sổ Terminal.

## Chạy tự động mỗi 6 giờ

```bash
EDITOR=nano crontab -e
```

Dán 2 dòng dưới, sửa `<bạn>` thành tên user, lưu bằng `Ctrl+O` → `Enter` → `Ctrl+X`:

```
PATH=/Users/<bạn>/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin
0 */6 * * * /bin/bash $HOME/robinhood-token-research/.claude/skills/stock-token-scout/scripts/run_cycle.sh >> $HOME/.stock-token-scout/cron.log 2>&1
```

Lưu ý:
- Dòng cron dán vào `crontab`, **không** dán vào file Python hay gõ thẳng vào Terminal.
- Dòng `PATH` bắt buộc: cron không đọc `~/.zshrc`, nên thiếu dòng này sẽ báo "không thấy lệnh claude".
- Mac phải bật và không ngủ lúc chạy (System Settings → Battery → Prevent automatic sleeping).
- Xem nhật ký bằng `cat ~/.stock-token-scout/cron.log`. Nếu thấy `Operation not permitted`: System Settings → Privacy & Security → Full Disk Access → thêm `/usr/sbin/cron`.

## Dùng trong Claude Code

Mở `claude` trong thư mục `~/robinhood-token-research`, rồi:

| Lệnh | Việc |
|---|---|
| `/report` | **Dùng lệnh này là đủ.** Chạy trọn bộ và giao một file HTML; tự xử lý khi mạng bị chặn; không hỏi lại, không giải thích quy trình |
| `/scout` | Quét, điều tra nếu có tín hiệu, dựng báo cáo HTML |
| `/investigate 0x…` | Điều tra một token cụ thể |
| `/present` | Chạy lại riêng bước cuối (investor memo + HTML), không nghiên cứu lại |
| `/verdict [ticker / file / thư mục]` | Hỏi đáp dễ hiểu về kết quả |

## Dùng trong app Claude (Cowork) hoặc máy bị chặn API

Không cần làm gì thêm: chỉ cần nói "chạy báo cáo token Robinhood" hoặc gõ `/report`. Nếu môi trường chặn `api.dexscreener.com` / `robinhoodchain.blockscout.com`, skill tự chuyển sang **chế độ tải hộ**: Claude tải dữ liệu bằng web fetch và Blockscout MCP, lưu bằng `fetched.py`, script tính toán và dựng HTML như bình thường. Báo cáo có mục "Độ tin cậy dữ liệu" ghi rõ nguồn nào thiếu. Chi tiết: `.claude/skills/stock-token-scout/references/data_fallback.md`.

| Biến môi trường | Tác dụng |
|---|---|
| `STS_OFFLINE=1` | Không gọi mạng, chỉ dùng dữ liệu tải hộ; URL thiếu ghi ở `~/.stock-token-scout/missing_urls.txt` |
| `STS_SKIP_HOSTS` | Nguồn bỏ qua ở chế độ không mạng (mặc định `api.geckoterminal.com`) |
| `STS_FETCHED_MAX_AGE_H` | Dữ liệu tải hộ hết hạn sau bao nhiêu giờ (mặc định 6) |

## Tiết kiệm hạn mức

| Biến môi trường | Tác dụng |
|---|---|
| `STS_MODEL=sonnet` | Dùng model rẻ hơn cho phần điều tra tự động |
| `STS_MAX_QUEUE=2` | Điều tra tối đa 2 token mỗi chu kỳ (mặc định 5) |
| `STS_DEEP_N=3` | Chỉ viết memo đầy đủ cho 3 ứng viên (mặc định 5) |
| `BLOCKSCOUT_API_KEY` | Key miễn phí của Blockscout, giảm lỗi giới hạn lượt gọi |

Ví dụ trong crontab: `0 */6 * * * STS_MODEL=sonnet STS_MAX_QUEUE=3 /bin/bash $HOME/robinhood-token-research/...`

Thiết kế đã tiết kiệm sẵn: không có tín hiệu thì không gọi AI; bằng chứng và trang web đã đọc (theo hash) không đưa lại cho AI; agent cuối đọc lại dữ liệu đã lưu thay vì tìm kiếm mới; logo, link, bảng và HTML do Python làm.

## Kiến trúc

| Thành phần | Loại | Vai trò |
|---|---|---|
| `scout_cycle.py` | Python | Quét, snapshot, so sánh với lần trước, sinh event |
| `onchain.py`, `ledger.py`, `context.py` | Python | Số liệu chuỗi, sổ bằng chứng, claim, danh tính |
| `onchain-analyst`, `social-researcher`, `project-analyst` | Agent | Điều tra từng mặt |
| `risk-synthesizer` | Agent | Viết memo nghiên cứu |
| `potential-assessor` | Agent | Chấm 6 tiêu chí + cờ đỏ; luật tính xếp loại |
| `run_report.py` | Python | Trạng thái lần chạy, cổng COMPLETE, chọn ứng viên, HTML |
| `investor-memo-writer` | Agent | Bước cuối: memo cho nhà đầu tư, chỉ cho token đã nghiên cứu xong |

Chi tiết: `ARCHITECTURE.md`. Thang điểm: `.claude/skills/scout-reader/references/scorecard.md`. Khung investor memo: `.claude/skills/scout-reader/references/investor-memo.md`.

## Giới hạn đã biết

- Ngưỡng và thang điểm là heuristic, chưa kiểm định thống kê trên Robinhood Chain (chuỗi chạy từ 01/07/2026).
- "Pool mới" nghĩa là mới với scout: pool cũ lần đầu lọt vào trending vẫn bị báo.
- Token launchpad có deployer là hợp đồng factory; token cùng launchpad có số liệu ban đầu giống nhau, không có nghĩa là cùng một người.
- Chưa phát hiện cụm ví liên kết; Uniswap v4 không cho đọc LP theo từng người.
- Chất lượng phần suy luận phụ thuộc bằng chứng mà các agent trước thu thập được. Báo cáo ghi rõ độ tin cậy và phần còn thiếu.

## Đóng góp

Issue và pull request đều được hoan nghênh. Trước khi gửi, chạy đủ 4 bộ test ở bước 2. Giữ nguyên tắc: chỉ thư viện chuẩn Python, luật tính điểm nằm trong code, không có lời khuyên giao dịch.

## Miễn trừ trách nhiệm

Xem `DISCLAIMER.md`. Tóm lại: đây là công cụ nghiên cứu, không phải lời khuyên đầu tư. Phần lớn token tạo qua launchpad mất gần hết giá trị.

## License

MIT, xem `LICENSE`.

## Prompts you can use

Các câu lệnh mẫu dưới đây gõ thẳng vào Claude (Claude Code trong thư mục dự án, hoặc app Claude có bộ skill này). Không cần nhớ tên lệnh: câu tiếng Việt thường là đủ, skill tự hiểu và tự chạy. Phần trong `<...>` là chỗ bạn thay bằng thông tin của mình.

Mặc định, mọi yêu cầu chạy báo cáo đều **trả về một file HTML** và một tin nhắn ngắn tối đa 6 dòng. Muốn biết thêm (quy trình, lỗi, memo gốc) thì hỏi riêng như ở mục 6.

### 1. Chạy nhanh: một câu ra báo cáo

| Bạn muốn | Gõ |
|---|---|
| Báo cáo đầy đủ cho các token đáng chú ý nhất lúc này | `/report` hoặc `Chạy báo cáo token Robinhood Chain cho tôi` |
| Chỉ quét xem có tín hiệu mới không, chưa cần nghiên cứu | `/scout` hoặc `Quét Robinhood Chain xem có gì mới, chưa cần viết báo cáo` |
| Báo cáo dù chuỗi đang yên (không có tín hiệu mới) | `Làm báo cáo cho 5 token ghép cổ phiếu có điểm cao nhất hiện tại` |

### 2. Chọn phạm vi nghiên cứu

```text
Nghiên cứu token 0x2e8c31162b855a2ffa90f6f8634643ad6f111e18 và xuất báo cáo HTML
```
```text
Làm báo cáo cho các token này: <địa chỉ 1>, <địa chỉ 2>, <địa chỉ 3>
```
```text
Đánh giá token có ticker <TICKER> trên Robinhood Chain (nếu trùng ticker, chọn token thanh khoản lớn nhất và ghi rõ trong báo cáo)
```
```text
Tôi chỉ quan tâm memecoin ghép với <NVDA / TSLA / AMZN / GOOGL / META / COIN / SPY / QQQ>. Chọn tối đa 5 token ghép cặp đó để làm báo cáo
```
```text
Nghiên cứu token này từ link: <link DexScreener / GeckoTerminal / Blockscout>
```

Mẹo: đưa **địa chỉ hợp đồng** luôn chính xác hơn ticker, vì ticker trùng rất phổ biến trên launchpad.

### 3. Điều chỉnh độ sâu, số lượng và chi phí

| Bạn muốn | Gõ |
|---|---|
| Ít token hơn, nhanh hơn | `Chạy báo cáo nhưng chỉ nghiên cứu tối đa 2 token` (tương đương `STS_MAX_QUEUE=2`) |
| Memo đầy đủ cho ít ứng viên, còn lại đánh giá ngắn | `Chỉ viết memo đầy đủ cho 3 token tốt nhất, các token khác đánh giá rút gọn` (`STS_DEEP_N=3`) |
| Tiết kiệm hạn mức | `Chạy báo cáo bằng model sonnet để tiết kiệm hạn mức` (`STS_MODEL=sonnet`) |
| Đào sâu một token | `Đào sâu phần creator và động cơ kinh tế của <TICKER>, được phép tìm kiếm web nhiều hơn bình thường` |

### 4. Hỏi đáp về kết quả (không chạy lại nghiên cứu)

```text
Giải thích dễ hiểu vì sao <TICKER> bị xếp ĐẦU CƠ THUẦN
```
```text
Trong báo cáo vừa rồi, token nào đáng nghiên cứu tiếp nhất và cần kiểm chứng điều gì trước?
```
```text
So sánh <TICKER 1> và <TICKER 2>: thanh khoản, phân bổ holder, rủi ro thoát hàng
```
```text
Tóm tắt báo cáo thành 5 gạch đầu dòng cho người không biết crypto
```
```text
Điều gì phải xảy ra để <TICKER> được nâng lên CÓ Ý TƯỞNG hoặc ĐÁNG NGHIÊN CỨU SÂU?
```

Các câu này dùng skill `scout-reader` (lệnh `/verdict`): chỉ đọc lại kết quả đã có, không tốn thời gian nghiên cứu lại.

### 5. Làm lại hoặc sửa đầu ra

| Bạn muốn | Gõ |
|---|---|
| Dựng lại HTML sau khi sửa memo, không nghiên cứu lại | `/present` hoặc `Dựng lại báo cáo HTML từ kết quả nghiên cứu hiện có` |
| Cập nhật số liệu mới cho token đã nghiên cứu | `Cập nhật lại báo cáo <TICKER> với số liệu on-chain mới nhất` |
| Xem thay đổi so với lần trước | `So với lần chạy trước, holder, thanh khoản và xếp loại của <TICKER> thay đổi thế nào?` |
| Chấm lại theo dữ kiện bạn bổ sung | `Tôi có thêm thông tin: <dữ kiện + link nguồn>. Ghi vào sổ bằng chứng rồi chấm lại <TICKER>` |
| Đổi tên file hoặc nơi lưu | `Lưu báo cáo HTML vào <thư mục> với tên <tên file>.html` |

Lưu ý: xếp loại tiềm năng, mức rủi ro thoát hàng tối thiểu và giới hạn kết luận do **luật trong code** tính. Yêu cầu kiểu "nâng xếp loại lên" sẽ không được làm nếu không có dữ kiện mới; hãy đưa dữ kiện kèm nguồn như ở dòng thứ tư.

### 6. Muốn xem chi tiết kỹ thuật (ngoài mặc định)

```text
Giải thích quy trình vừa chạy: đã lấy dữ liệu từ đâu, nguồn nào bị thiếu
```
```text
Gửi kèm memo nghiên cứu .md của <TICKER> để tôi đọc bằng chứng gốc
```
```text
Liệt kê các claim của <TICKER> và kết quả đối chiếu on-chain
```
```text
Mạng đang bị chặn: chạy ở chế độ tải hộ và cho tôi biết dữ liệu nào không lấy được
```

### 7. Tuỳ chỉnh ngưỡng và danh sách cổ phiếu

```text
Chỉ coi token là ứng viên khi thanh khoản từ $50.000 trở lên (ghi vào ~/.stock-token-scout/rules.json, khoá min_liq_candidate)
```
```text
Thêm stock token <TICKER> địa chỉ <0x...> vào danh sách trắng (bản ghi đè ~/.stock-token-scout/stock_tokens.json), đối chiếu với trang Token Contracts của Robinhood Chain trước khi thêm
```
```text
Kiểm tra lại danh sách stock token chính chủ trong references/stock_tokens.json với tài liệu Robinhood Chain hiện hành
```

### 8. Chạy tự động

```text
Cài lịch chạy báo cáo mỗi 6 giờ và chỉ báo cho tôi khi có event mức 3, claim CONFLICT hoặc token bị chấm TRÁNH XA
```
```text
Mỗi sáng 8 giờ (giờ Việt Nam) gửi tôi file báo cáo HTML mới nhất
```

### Mẹo để skill chạy trơn tru

- **Một yêu cầu, một mục tiêu.** "Làm báo cáo cho token X" chạy trọn quy trình; "giải thích token X" chỉ đọc kết quả có sẵn. Tách hai việc giúp nhanh và rẻ hơn.
- **Đưa địa chỉ, không chỉ ticker.** Tránh nghiên cứu nhầm token trùng tên.
- **Nói rõ số lượng** khi cần nhanh ("tối đa 2 token", "memo đầy đủ cho 3 token").
- **Bổ sung dữ kiện kèm link nguồn**, không yêu cầu đổi kết luận bằng lời. Skill chỉ đổi đánh giá khi có bằng chứng.
- **Hỏi ngay sau khi chạy** để tận dụng dữ liệu vừa thu thập; số liệu memecoin cũ hơn 24 giờ nên chạy lại.
- Skill **không** khuyên mua bán, không đưa mục tiêu giá; những yêu cầu đó sẽ được trả lời bằng dữ kiện và rủi ro thay vì khuyến nghị.
