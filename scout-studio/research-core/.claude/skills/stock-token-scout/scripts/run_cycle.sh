#!/usr/bin/env bash
# Chu kỳ tự động cho cron. Tầng tất định chạy trước; CHỈ gọi Claude khi scout_cycle.py báo có hàng đợi (mã 10).
#
# Crontab mỗi 6 giờ (sửa đường dẫn cho đúng máy; cron không đọc ~/.zshrc nên phải khai báo PATH chứa lệnh claude):
#   PATH=/Users/<bạn>/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin
#   0 */6 * * * /bin/bash $HOME/robinhood-token-research/.claude/skills/stock-token-scout/scripts/run_cycle.sh >> $HOME/.stock-token-scout/cron.log 2>&1
#
# Biến tuỳ chọn:
#   STS_MAX_QUEUE   số token điều tra tối đa mỗi chu kỳ (mặc định 5)
#   STS_MODEL       model cho phần điều tra, ví dụ "sonnet" để tiết kiệm hạn mức (mặc định: model mặc định của tài khoản)
#   STS_REPORT_DIR  thư mục memo và báo cáo HTML (mặc định ~/.stock-token-scout/reports)
#   STS_DEEP_N      số ứng viên được viết memo đầy đủ mỗi lần chạy (mặc định 5)
#   STS_PROJECT_DIR thư mục dự án Claude Code chứa .claude/agents
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
# scripts -> stock-token-scout -> skills -> .claude -> thư mục dự án
PROJECT_DIR="${STS_PROJECT_DIR:-$(cd "$DIR/../../../.." 2>/dev/null && pwd)}"
OUT="${STS_REPORT_DIR:-$HOME/.stock-token-scout/reports}"
RENDER="$PROJECT_DIR/.claude/skills/scout-reader/scripts/render_report.py"
mkdir -p "$OUT"
echo "=== $(date -u +%FT%TZ) ==="

cd "$DIR" || exit 1
python3 scout_cycle.py --max-queue "${STS_MAX_QUEUE:-5}"
code=$?
if [ "$code" -eq 2 ]; then echo "Không lấy được dữ liệu. Không gọi LLM."; exit 1; fi
if [ "$code" -eq 3 ]; then echo "Chế độ tải hộ còn thiếu dữ liệu (fetched.py missing). Không gọi LLM."; exit 1; fi
if [ "$code" -ne 10 ]; then echo "Không có tín hiệu đủ mạnh (mã $code). Không gọi LLM."; exit 0; fi

command -v claude >/dev/null 2>&1 || { echo "Không thấy lệnh claude (Claude Code) trong PATH. Xem README, mục Chạy tự động."; exit 1; }
cd "$PROJECT_DIR" || { echo "Không vào được thư mục dự án $PROJECT_DIR"; exit 1; }
# Headless: chỉ web search + web fetch cho lớp X-Lite, KHÔNG điều khiển trình duyệt.
# Tên công cụ trong --allowedTools có thể đổi theo phiên bản: kiểm tra bằng `claude --help`.
# Muốn cho phép connector (MCP), thêm tên công cụ của nó, ví dụ "mcp__<tên>__<công cụ>"; xem tên bằng /mcp.
TOOLS="Bash,Read,Write,Edit,Glob,Grep,WebSearch,WebFetch,Task"
if [ -n "${STS_MODEL:-}" ]; then
  claude -p "/investigate" --model "$STS_MODEL" --allowedTools "$TOOLS"
else
  claude -p "/investigate" --allowedTools "$TOOLS"
fi

# Tầng tất định lần nữa, không tốn credit AI: dựng HTML của lần chạy (deliverable) và thư viện memo.
# Chạy cả khi Claude dừng giữa chừng: token chưa xong vẫn hiện, kèm lý do.
python3 "$PROJECT_DIR/.claude/skills/scout-reader/scripts/run_report.py" render || echo "Không dựng được báo cáo lần chạy (xem lỗi ở trên)."
python3 "$RENDER" --dir "$OUT" || echo "Không dựng được index.html (xem lỗi ở trên)."
