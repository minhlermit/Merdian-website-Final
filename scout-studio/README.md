# Stock Scout Studio

Giao diện nghiên cứu token trên Robinhood Chain, xây từ **robinhood-token-research v2.4**. Frontend là React + TypeScript + Vite; engine Python/Claude Code gốc nằm nguyên trong `research-core/`. Asset hình được tách riêng trong `public/assets/`, UI chia thành các component trong `src/components/`.

## Có gì trong bản này

- Typography Inter Tight / DM Sans, intro mascot, con trỏ S của thương hiệu, hero chuyển động theo chuột, reveal khi cuộn, storyboard 5 bước của ZIP, nhân vật 3D và orbit tách asset.
- Nút **Run demo** trên bản host chạy một walkthrough giả lập rồi đưa tới candidate. Khi mở bridge cục bộ, nút **Run Scout** gọi chu kỳ Python gốc.
- Bảng candidate xoay theo các mốc UTC 00:00, 06:00, 12:00, 18:00. Candidate đang xem giữ nguyên tới mốc kế tiếp; sau đó board của tab được xóa, import cũ hết hạn và bridge chỉ xuất token/event của cửa sổ mới. Demo có thể chạy lại để xem bộ ví dụ giả lập. Web tĩnh không tự chạy cron hoặc tạo dữ liệu thật.
- Console lọc/tìm/sắp xếp ứng viên, đồ thị snapshot thanh khoản, timeline event, panel luận điểm/rủi ro/bằng chứng, so sánh tối đa 3 token.
- Xem `latest.html` trong một khung tách biệt, tải lại báo cáo, nhập JSON export hoặc HTML report, xuất snapshot JSON.
- Bridge cục bộ **chỉ đọc** SQLite + manifest + investor memo từ Scout; nút **Run Scout** gọi đúng `run_cycle.sh` gốc khi bridge đang chạy.
- **Connect MetaMask** ở header: kết nối địa chỉ, chuyển sang Robinhood Chain khi chủ ví đồng ý, và ký thông điệp đăng nhập. Chữ ký được kiểm tra ngay trong trình duyệt cho phiên xem trước; chưa có tài khoản/server session hoặc quyền premium thật.
- **Get MC** là ý tưởng sản phẩm: gói Explorer, Researcher, Studio; bảng giá lệnh minh họa, xác nhận chi phí trước khi chạy, đề xuất burn MC sau job thành công, nạp thêm từ ví bằng xác nhận riêng. Không có token contract, thanh toán, balance hay burn đang hoạt động. Xem `MC-PRODUCT-SPEC.md`.
- Trên Vercel, giao diện tĩnh có thể nhập JSON + HTML do máy chạy Scout xuất ra. Khi chưa có dữ liệu, nó hiện **demo giả lập được đánh dấu rõ**, không giả là dữ liệu thị trường thật.

## Chạy trên máy

Yêu cầu Node 20.19+ hoặc 22.12+ / Node 24, Python 3.9+. Để chạy research đầy đủ, cài Claude Code và đảm bảo máy truy cập được các nguồn công khai mà `research-core/README.md` liệt kê.

```bash
cd scout-studio
npm ci
npm run dev
```

Mở `http://127.0.0.1:5173/`. Nếu không mở bridge, app hiển thị demo.

Muốn xem dữ liệu Scout thật, mở **terminal thứ hai** trong `scout-studio`:

```bash
python3 bridge/server.py
```

Lúc đó console sẽ đọc `~/.stock-token-scout/scout.db`, `runs/current` và `reports/latest.html` do core tạo. Nút **Run Scout** chạy chu kỳ gốc; khi có ứng viên cần điều tra, Claude Code có thể mất nhiều phút. Tiến độ và lỗi nằm trong `~/.stock-token-scout/studio-run.log`. Bridge chỉ lắng nghe `127.0.0.1:8787`; Vite chuyển tiếp `/api` từ localhost. Không đưa bridge trực tiếp lên internet.

Bạn có thể đặt `STS_CACHE_DIR`, `STS_REPORT_DIR`, `STS_PROJECT_DIR` trước khi khởi động bridge nếu dữ liệu/core đặt nơi khác. `STS_PROJECT_DIR` trỏ tới thư mục chứa `.claude` của research-core.

## Xuất dữ liệu cho bản host

Trên máy đã chạy Scout:

```bash
python3 bridge/export.py --out scout-export.json
```

Trong bản web, chọn **Import** và chọn `scout-export.json` trong cùng cửa sổ sáu giờ UTC. Muốn xem investor report hoàn chỉnh, tiếp tục chọn **Import** và chọn `~/.stock-token-scout/reports/latest.html`. JSON chỉ chứa bản chiếu dữ liệu nghiên cứu hiện có; HTML vẫn là report chính thức của pipeline. File JSON nhập được lưu trong localStorage của **trình duyệt đó**, không gửi lên server. Xóa bằng **Clear import** hoặc tự hết hạn khi sang cửa sổ mới. Hãy tự xét nội dung export trước khi chia sẻ công khai vì bằng chứng và các link nghiên cứu sẽ có trong file.

## Build và Vercel

```bash
npm run build
npx vercel login
npx vercel deploy
```

Vercel nhận diện Vite, dùng lệnh `npm run build` và xuất thư mục `dist`. Với production, dùng `npx vercel deploy --prod` sau khi duyệt bản preview. `vercel.json` hỗ trợ đường dẫn SPA. `.vercelignore` loại core Python/bridge khỏi bản upload; engine vẫn có trong ZIP cho chạy cục bộ.

**Giới hạn deployment:** Vercel host giao diện tĩnh. Python CLI, SQLite cục bộ, Claude Code headless và cron sáu giờ không thể tự chạy trong tab trình duyệt hoặc từ static deployment này. Muốn dữ liệu tự cập nhật trên web cần một dịch vụ backend chạy Scout và một lớp lưu trữ/publication có kiểm soát; wallet sign-in production cần nonce/session xác thực phía server; MC cần hợp đồng, thanh toán, đối soát job và chính sách phí. Bản này không thu tiền.

## Cấu trúc

```text
public/assets/             3 asset PNG độc lập
src/components/            Hero, Story, Motion, RunExperience, WalletPanel, GetMC, card, panel
src/data/demo.ts            dữ liệu giả lập chỉ để duyệt UI
src/lib/                    định dạng, vòng 6 giờ, wallet, kiểm tra JSON, local import
src/App.tsx                 console, lọc, so sánh, report
bridge/export.py            đọc kết quả gốc → JSON schema 1
bridge/server.py            API localhost và nút Run Scout
research-core/              nguyên bộ v2.4 từ ZIP đầu vào
dist/                       bản build tĩnh
```

## Kiểm tra đã chạy

- `npm run build` (TypeScript và Vite).
- Bốn test suite đi kèm của research-core: pipeline, reader, report, fixes.
- Browser QA ở desktop 1440×900 và mobile 390×844: hero, storyboard, demo run, console, panel, so sánh, MC modal, ảnh asset, nhập JSON. Không có lỗi JavaScript hay tràn ngang trên mobile.
- Kiểm tra wallet với provider giả lập: Connect, ký hợp lệ, đổi chain và xóa trạng thái sign-in sau khi đổi chain.
- `bridge/export.py` với SQLite fixture đã trả đúng candidate, event, mức rủi ro và nhãn bằng chứng.

Đây là giao diện nghiên cứu, không phải công cụ giao dịch hay lời khuyên đầu tư. Điểm, giới hạn kết luận và mức rủi ro thoát hàng do luật trong core gốc tính; frontend chỉ hiển thị.
