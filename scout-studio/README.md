# Stock Scout Studio

Giao diện nghiên cứu token trên Robinhood Chain, xây từ **robinhood-token-research v2.4**. Frontend là React + TypeScript + Vite; engine Python/Claude Code gốc nằm nguyên trong `research-core/`. Bản **v3** (tháng 10/2026) làm lại toàn bộ phần trình bày theo `CLAUDE-3D-MOTION-BRIEF.md`: Scout 3D tương tác thật, nền chuyển động procedural đạt buffer UHD, bố cục và hệ chữ mới kiểu website công ty công nghệ. Logic sản phẩm, dữ liệu demo và engine nghiên cứu giữ nguyên.

Bản v2 đã duyệt vẫn khôi phục được: commit `Add Stock Scout Studio v2 baseline from uploaded ZIP` trong lịch sử git chứa nguyên ZIP gốc, còn ảnh chụp v2 nằm ở `previews/*.png`.

## Có gì mới trong v3

- **Scout 3D thật** (`src/scene/ScoutModel.ts`): lưới dựng procedural bằng three.js, có khối, vật liệu vật lý và ánh sáng studio. Giữ các dấu hiệu nhận dạng của avatar: tóc bạc vuốt ngược trên lớp đen có viền răng cưa, kính không viền có bản lề, mắt capsule, má hồng, khuyên bạc tai trái, áo khoác đen cổ đứng có khóa kéo. PNG gốc chỉ còn làm ảnh tham chiếu, poster lúc tải và fallback.
- **Tương tác**: nghiêng đầu theo con trỏ (tối đa 7°), kéo ngang để xoay có quán tính, giới hạn ±70° và bật đàn hồi; ba hotspot (kính, khuyên tai, khóa kéo) mở bảng năng lực **Explore Scout**; **Reset view**, nút xoay trái/phải, phím mũi tên / R / Enter. Trên cảm ứng, vuốt ngang có chủ đích để xoay, vuốt dọc vẫn cuộn trang (`touch-action: pan-y`). Tương tác trang trí không bao giờ gọi ví hay lệnh nghiên cứu.
- **Nền chuyển động** (`src/scene/AnimatedBackground.ts`): shader GLSL chạy thời gian thực — sóng không gian chậm, lưới 80 px, ánh amber trôi, sương chiều sâu, vùng yên tĩnh sau tiêu đề, light sweep khi vào trang, dithering theo pixel thật để không bị banding. Không phải video nên không có mối nối vòng lặp.
- **Một scene WebGL dùng chung** cho hero và phần How it works, chuyển liên tục theo tiến độ cuộn (đảo chiều chính xác): Discover → Verify → Investigate → Evaluate → Deliver (`src/scene/EvidenceScene.ts`). Góc xoay do người dùng kéo tách riêng khỏi chuyển động của story nên không giằng co nhau. Khi tới console, scene lùi xa rồi tạm dừng.
- **Bố cục mới**: header cố định (Get MC + Connect wallet căn phải), hero chia cột 6/6, Product value (3 lợi ích có dẫn nguồn file thật), How it works (5 chương, scene ghim bên phải; mobile dùng dải ghim trên cùng + thẻ chương), chuyển cảnh vào console, MC plans kèm bảng so sánh ghi rõ *concept*, FAQ về reset/nghiên cứu/MC/ví, footer có điều khiển Motion và 3D quality.
- **Hệ chữ Geist**: Geist Sans cho tiêu đề/nội dung/điều hướng, Geist Mono cho số liệu và nhãn kỹ thuật; WOFF2 variable tự host trong `public/fonts/geist/` kèm giấy phép SIL OFL 1.1, `font-display: swap`. Thang chữ dùng `clamp()` (hero ~40 px mobile → ~72 px ở 1440 → 96 px), số tabular cho chỉ số. Đã kiểm tra 77 ký tự có dấu tiếng Việt: cả Geist và Geist Mono đều có đủ glyph.
- **Con trỏ thương hiệu**: dấu S vẽ đúng tại điểm trỏ ở mỗi lần di chuột (không làm mượt), chỉ vòng trang trí bên ngoài là trễ nhẹ. Tự trả về con trỏ gốc ở ô nhập, select, iframe report và trên thiết bị cảm ứng.
- **Dialog dùng chung** (`src/components/Dialog.tsx`): bẫy focus, Escape, click nền để đóng, trả focus về nút đã mở, hiệu ứng vào/ra. Áp dụng cho ví, Get MC, demo, chi tiết ứng viên, so sánh, report, setup.
- **Asset lab** tại `/lab`: bốn mẫu duyệt theo brief (Scout tương tác + chụp 3 góc, nền + readout buffer thật + biến thể mobile, chuyển cảnh Discover → Verify cuộn hai chiều, hero mới cạnh bản v2) và bảng kiểm kê asset. Xem `ASSET-LAB.md`.
- **Hiệu năng và fallback**: code 3D được lazy-load sau first paint (poster hiện ngay); chính sách pixel-ratio thích ứng (desktop tối đa 3840×2160, thiết bị cầm tay tối đa 1,5 MP, tự hạ bậc khi khung hình chậm); dừng khi ra khỏi màn hình hoặc ẩn tab; render theo yêu cầu khi tắt motion. Không có WebGL, mất context hay lỗi tải → poster tĩnh, sản phẩm vẫn chạy đầy đủ. `prefers-reduced-motion` hoặc Motion: Off giữ nguyên nội dung, gần như không chuyển động camera.

Những gì **không đổi**: bảng ứng viên, lọc, sắp xếp, chi tiết, so sánh, import/export, link bằng chứng, trình xem report HTML; ứng viên demo giả lập có nhãn rõ; cửa sổ reset 6 giờ UTC và hành vi hết hạn import (reset không có nghĩa là đã chạy nghiên cứu mới); **Run demo** trên bản host và **Run Scout** qua bridge cục bộ; engine Python, cổng nghiên cứu và luật chấm điểm; hành vi kết nối/ký ví và giới hạn phiên xem trước; MC vẫn chỉ là concept, không có số dư, thanh toán hay burn.

## Chạy trên máy

Yêu cầu Node 20.19+ hoặc 22.12+ / Node 24, Python 3.9+.

```bash
cd scout-studio
npm ci             # hoặc npm install
npm run dev
```

Mở `http://127.0.0.1:5173/` (trang chính) và `http://127.0.0.1:5173/lab` (Asset lab). Thêm `?debug=scene` vào URL để xem độ phân giải render thực tế (viewport, DPR, drawing buffer, bậc chất lượng).

> `package-lock.json` đã được GitHub Actions tạo lại bằng npm thật (commit `Update package-lock.json for three and @types/three`), nên `npm ci` cũng dùng được.

Muốn xem dữ liệu Scout thật, mở **terminal thứ hai** trong `scout-studio`:

```bash
python3 bridge/server.py
```

Lúc đó console đọc `~/.stock-token-scout/scout.db`, `runs/current` và `reports/latest.html` do core tạo. Nút **Run Scout** chạy chu kỳ gốc; khi có ứng viên cần điều tra, Claude Code có thể mất nhiều phút. Tiến độ và lỗi nằm trong `~/.stock-token-scout/studio-run.log`. Bridge chỉ lắng nghe `127.0.0.1:8787`; Vite chuyển tiếp `/api` từ localhost. Không đưa bridge trực tiếp lên internet.

Có thể đặt `STS_CACHE_DIR`, `STS_REPORT_DIR`, `STS_PROJECT_DIR` trước khi khởi động bridge nếu dữ liệu/core đặt nơi khác. `STS_PROJECT_DIR` trỏ tới thư mục chứa `.claude` của research-core.

## Xuất dữ liệu cho bản host

Trên máy đã chạy Scout:

```bash
python3 bridge/export.py --out scout-export.json
```

Trong bản web, chọn **Import** và chọn `scout-export.json` trong cùng cửa sổ sáu giờ UTC. Muốn xem investor report hoàn chỉnh, tiếp tục chọn **Import** và chọn `~/.stock-token-scout/reports/latest.html`. JSON nhập được lưu trong localStorage của **trình duyệt đó**, không gửi lên server. Xóa bằng **Clear import** hoặc tự hết hạn khi sang cửa sổ mới. Hãy tự xét nội dung export trước khi chia sẻ công khai.

## Build và Vercel

```bash
npm run build
npx vercel login
npx vercel deploy          # preview
npx vercel deploy --prod   # chỉ sau khi duyệt preview
```

`vercel.json` chuyển mọi đường dẫn SPA (kể cả `/lab`) về `index.html`; file tĩnh trong `public/` (asset, font, ảnh baseline) được phục vụ trực tiếp. `.vercelignore` loại core Python/bridge khỏi bản upload.

**Giới hạn deployment:** Vercel chỉ host giao diện tĩnh. Python CLI, SQLite cục bộ, Claude Code headless và cron sáu giờ không tự chạy trong trình duyệt. Dữ liệu tự cập nhật cần backend chạy Scout; đăng nhập ví production cần nonce/session phía server; MC cần hợp đồng, thanh toán và đối soát job. Bản này không thu tiền.

## Cấu trúc

```text
public/assets/              3 PNG: tham chiếu nhận dạng, poster, fallback, mascot
public/fonts/geist/         Geist Sans + Geist Mono (WOFF2 variable) + OFL.txt
public/lab/                 ảnh baseline v2 cho Asset lab
src/scene/                  config (motion/chất lượng/storyboard/ngân sách), ScoutModel, EvidenceScene,
                            AnimatedBackground, ScoutEngine, ScoutStage (lazy), bridge
src/components/             SiteHeader, Hero, SubjectControls, ValueSection, Story, Plans, FAQ, SiteFooter,
                            SceneLayer, Dialog, Motion (cursor/reveal), các panel console cũ
src/lab/AssetLab.tsx        trang duyệt asset tại /lab
src/lib/motion.ts           tùy chọn Motion / 3D quality (localStorage, có fallback)
src/styles/                 fonts, tokens, site, lab
src/style.css, enhancements.css   style console/modal cũ (đã bỏ phần hero/story v2, đổi sang Geist)
previews/v3/                ảnh chụp bản v3; previews/*.png là v2
bridge/, research-core/     giữ nguyên
```

## Kiểm tra đã chạy (v3)

**GitHub Actions** (`.github/workflows/scout-studio-check.yml`, chạy mỗi lần push lên nhánh `claude/**`) dùng npm thật:

- `npm install` → `npm run build` (`tsc -b && vite build`, React 19 + Vite 7.3): **thành công**. Bundle: trang chính 318 KB (100 KB gzip); chunk 3D `ScoutEngine` 589 KB (154 KB gzip), chỉ tải lazy sau first paint nên Vite có cảnh báo chunk > 500 KB. Đây là kích thước của three.js, nằm trong ngân sách 200 KB gzip.
- `ci/smoke.mjs` chạy Chromium headless trên bản build production (`vite preview`): **40/40 kiểm tra đạt**.
  - Scene 3D và hotspot; kéo chuột xoay, reset, phím mũi tên, Explore Scout, bấm hotspot.
  - Dialog Get MC: bẫy focus, Escape, trả focus. Ví báo thiếu MetaMask.
  - Run demo hoàn tất rồi chuyển sang console; drawer chi tiết; so sánh; lọc/tìm; export và import lại; từ chối export của cửa sổ trước; `/#console`.
  - Mốc reset 6 giờ UTC với đồng hồ giả.
  - Tắt WebGL → poster tĩnh, sản phẩm vẫn chạy.
  - Cảm ứng 390×844: vuốt ngang xoay, vuốt dọc vẫn cuộn, không tràn ngang.
  - Asset lab và chụp 3 góc.
  - Không có lỗi JavaScript chưa bắt.
- Độ phân giải render đo được (`?debug=scene`):

| Viewport | Drawing buffer |
|---|---|
| 3840×2160 @DPR1 | **3840×2160** |
| 1920×1080 @DPR2 | **3840×2160** |
| 1440×900 @DPR2 | 2880×1800 |
| 390×844 @DPR3 | 780×1688 (giới hạn thiết bị cầm tay) |

Ảnh chụp của mỗi lần chạy nằm trong artifact `scout-studio-screenshots` ở trang Actions.

Giới hạn còn lại: máy CI và trình duyệt headless dùng WebGL phần mềm nên **chưa đo được FPS hay hiệu năng trên GPU và màn hình 4K vật lý**. Hãy mở bản dev hoặc bản preview trên máy thật để đánh giá độ mượt. Font đã kiểm tra: 77 ký tự tiếng Việt có dấu đều có glyph trong Geist và Geist Mono.

Chưa deploy Vercel (session dựng không có quyền Vercel).

Đây là giao diện nghiên cứu, không phải công cụ giao dịch hay lời khuyên đầu tư. Điểm, giới hạn kết luận và mức rủi ro thoát hàng do luật trong core gốc tính; frontend chỉ hiển thị.
