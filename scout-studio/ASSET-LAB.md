# Asset lab

Các file sau độc lập; thay một PNG không cần dựng lại component còn lại. Có thể duyệt trực tiếp tại mục **Asset lab** trong app.

| File | Vai trò | Prompt cô đọng |
|---|---|---|
| `public/assets/scout-avatar-3d.png` | Nhân vật hero | Chuyển avatar đầu vào thành tượng vinyl 3D; giữ tóc sáng có lớp tối, kính mảnh, mắt capsule, má hồng, khuyên bạc; áo khoác đen; nền alpha trong suốt. |
| `public/assets/signal-orbit-3d.png` | Vật thể nền hero và thẻ method | Torus kính graphite, trụ titanium, dải sáng amber xoay quanh, ánh sáng studio, nền alpha trong suốt; không logo/chữ. |
| `public/assets/scout-mascot-pixel.png` | Mascot lúc trống/đợi quét | Cùng nhân vật dưới dạng sprite pixel toàn thân, áo khoác đen và kính lúp amber, bảng màu giới hạn, nền alpha trong suốt. |

Ảnh đầu vào dùng làm reference/edit target cho avatar 3D và reference nhận dạng cho mascot pixel. Các asset được tạo bằng công cụ hình ảnh tích hợp. Motion Sites, Awwwards và Refero là nguồn cảm hứng về nhịp chuyển động, hero và dashboard; layout/copy/asset trong project là thiết kế riêng.

Các component tương ứng: `Hero.tsx` dùng avatar và orbit; `Story.tsx` dùng orbit trong 5 cảnh; `Motion.tsx` dùng mascot cho intro và con trỏ S dựng bằng CSS; `RunExperience.tsx` dùng mascot cho guided demo; `App.tsx` dùng mascot và orbit; thẻ token/đồ thị/panel trong `CandidateCard.tsx`, `Sparkline.tsx`, `DetailPanel.tsx`.

Typography dùng Inter Tight cho heading, DM Sans cho body và DM Mono cho nhãn máy. Cả ba được tải qua Google Fonts trong `index.html`; không đóng gói một bản Helvetica Now không có license. Chuyển động và reveal nằm trong `src/enhancements.css`, hỗ trợ `prefers-reduced-motion`, còn con trỏ thương hiệu chỉ hiện ở thiết bị pointer chính xác.
