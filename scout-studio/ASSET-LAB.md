# Asset lab (v3)

Mở `/lab` trên bản dev hoặc bản deploy. Trang này là bản duyệt asset theo brief 3D motion: mỗi mẫu dùng đúng engine của trang chính và có thể thay độc lập.

## Bốn mẫu duyệt

| # | Mẫu | Cách xem | Ảnh chụp |
|---|---|---|---|
| 01 | **Scout 3D tương tác** — hình khối thật, ánh sáng, chuyển động idle (thở, nháy mắt, lắc nhẹ), kéo xoay có quán tính, hotspot, reset | Kéo ngang, rê chuột để đổi hướng nhìn, bấm Front / Three-quarter / Side, bấm **Capture front · ¾ · side** để render 3 góc | `previews/v3/lab-subject.png`, `previews/v3/scout-angles-front-3q-side.png`, `previews/v3/hotspot-explore-panel.png` |
| 02 | **Nền chuyển động** — bản trình bày 4K và biến thể mobile | Readout báo viewport, DPR, drawing buffer thật, bậc chất lượng; chọn Auto/High/Balanced/Low; khung điện thoại 390×844 dùng giới hạn thiết bị cầm tay | `previews/v3/hero-3840x2160-uhd.png` |
| 03 | **Một chuyển cảnh story** — Discover → Verify, cuộn hai chiều | Cuộn trong dải bên phải hoặc kéo thanh trượt; mọi trạng thái là hàm của tiến độ nên đảo chiều chính xác | `previews/v3/lab-story-transition.png`, `previews/v3/story-1-discover.png`, `previews/v3/story-2-verify.png` |
| 04 | **Hero hoàn chỉnh** — chữ mới, điều hướng, thứ bậc nút, con trỏ thương hiệu, tiền cảnh + nền | Khung desktop 1440×900 và mobile 390×844 tải trang thật, đặt cạnh ảnh baseline v2; có bảng thang chữ và dòng kiểm tra dấu tiếng Việt | `previews/v3/lab-hero-vs-baseline.png`, `previews/v3/desktop-hero-1440.png`, `previews/v3/mobile-hero-390.png` |

**Video tham khảo:** `https://www.youtube.com/shorts/yVXsS59LYJ0` không truy cập được từ môi trường dựng (mạng chặn YouTube). Chuyển động hiện tại là đề xuất dựa trên brief và sản phẩm sẵn có, **không phải bản khớp từng cảnh** với clip. Gửi trực tiếp file video để so sánh chính xác.

## Kiểm kê asset

| Asset | Loại | Vị trí | Dùng ở |
|---|---|---|---|
| Scout (đầu chibi, tóc bạc + lớp đen, kính không viền, tai, khuyên bạc, áo khoác cổ đứng, khóa kéo) | **Hình học procedural**, dựng lúc chạy (~60 mesh, vật liệu vật lý) | `src/scene/ScoutModel.ts` | Hero, story, lab |
| Vòng tín hiệu, node, lớp bằng chứng, đường nghiên cứu, khung chấm điểm, sàn exit-risk, cổng hoàn tất, báo cáo | **Hình học procedural** + canvas texture tạo lúc chạy | `src/scene/EvidenceScene.ts` | Story, lab |
| Nền studio chuyển động | **Shader GLSL thời gian thực** | `src/scene/AnimatedBackground.ts` | Hero, story, lab |
| Phản chiếu studio | RoomEnvironment của three.js (procedural) | `src/scene/ScoutEngine.ts` | Mọi scene |
| `scout-avatar-3d.png` | **Raster** — tham chiếu nhận dạng, poster lúc tải, fallback khi không có WebGL | `public/assets/` | Hero |
| `signal-orbit-3d.png` | **Raster** — fallback story, thẻ protocol trong console | `public/assets/` | Story (fallback), console |
| `scout-mascot-pixel.png` | **Raster** — trạng thái trống, demo có hướng dẫn | `public/assets/` | Console, Run demo |
| Geist Sans / Geist Mono | WOFF2 variable, SIL OFL 1.1 | `public/fonts/geist/` | Toàn trang |
| Model 3D nhập ngoài (GLB/glTF) | **Không có** trong bản này | — | — |

Không có model tạo sẵn nào dùng được, nên Scout được dựng procedural trong code. Nếu muốn độ giống cao hơn (điêu khắc tóc, nếp áo), bước sản xuất tiếp theo là tạo GLB (ví dụ image-to-3D từ `scout-avatar-3d.png` rồi dọn lưới và rig đầu), nén Draco/meshopt ≤ 450 KB, đặt trong `public/models/` và thay `createScout()` bằng loader trả về cùng giao diện `ScoutRig` (root/body/head/eyes/hotspots). Phần còn lại của engine không cần đổi.

## Ngân sách và chính sách chất lượng

Khai báo trong `src/scene/config.ts`:

- Model: ≤ 450 KB nếu thay bằng GLB (bản procedural: 0 KB tải về).
- Nền: ≤ 6 MB nếu thay bằng video 4K (bản shader: 0 KB).
- Texture: ≤ 512 KB (bản hiện tại tạo bằng canvas lúc chạy).
- Font: ≤ 160 KB (Geist + Geist Mono ≈ 141 KB).
- Chunk 3D (three.js + scene), lazy-load sau first paint: mục tiêu ≤ 200 KB gzip; đo thử bằng Bun minify ≈ 160 KB gzip (612 KB minified).

Pixel ratio thích ứng: bậc **High** tối đa DPR 2 và 3840×2160 pixel; **Balanced** DPR 1,5 / 1440p; **Low** DPR 1 / 1080p. Thiết bị cầm tay (pointer thô hoặc rộng < 760 px) bị giới hạn DPR 2 và 1,5 MP. Ở chế độ Auto, nếu thời gian khung hình trung bình vượt 24 ms trong 90 khung, engine hạ một bậc và ghi lý do (xem readout trong lab hoặc `?debug=scene`). Scene dừng khi ra khỏi màn hình hoặc ẩn tab; khi tắt motion, chỉ render lúc có thay đổi.

## Thông số chuyển động (để tinh chỉnh)

Phản hồi hover/press ~200 ms; tiêu đề và section vào 700 ms, lệch 70 ms; hero ổn định camera 900 ms, light sweep 1,5 s; nghiêng theo con trỏ 7°; kéo ±70° với 17° đàn hồi; cuộn story làm mượt theo hàm mũ (tốc độ 6,5/s). Đây là giá trị đề xuất, không phải đo từ clip tham khảo.
