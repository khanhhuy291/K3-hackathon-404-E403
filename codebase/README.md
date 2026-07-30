# Discord Course AI Agents

Prototype đọc `../discord_message.json`, tách **backend** và **frontend**, tạo dashboard deadline/thông báo và Q&A agent dùng tools.

## Cấu trúc mới

```txt
.env.example                 # copy thành ../.env (root repo), không commit key
codebase/
├─ app.py                    # launcher tương thích: gọi backend/server.py
├─ backend/
│  ├─ agents.py              # agents + tool framework + provider
│  ├─ server.py              # HTTP API/backend, serve frontend
│  ├─ discord_bot.py         # crawler Discord (process riêng, optional)
│  └─ discord_ingestion.py   # normalize + ingest Discord vào pipeline hiện có
├─ frontend/                 # dashboard UI đang được serve
└─ runtime/                  # crawl/output thực tế, gitignored
```

## Các agent

### 1) `RawJsonExtractorAgent`
- Input: JSON Discord crawl thô.
- Output: JSON có cấu trúc gồm `metadata`, `announcements`, `deadlines`, `meetings`, `resources`, `documents`, `questions`, `timeline`, `stats`.
- Có sửa lỗi mojibake tiếng Việt trong data crawl.
- Có thể dùng Llama qua OpenAI-compatible API của NVIDIA nếu cấu hình `.env`:

```env
OPENAI_API_KEY=nvapi-...
OPENAI_BASE_URL=https://integrate.api.nvidia.com/v1
OPENAI_MODEL=meta/llama-3.1-70b-instruct
```

Nếu không có key/API lỗi, agent fallback rule-based để demo luôn chạy.

### 2) `Discord crawler` (optional)
- `backend/discord_bot.py` nhận tin nhắn mới và có lệnh `!scan_history [limit]` để quét tối đa 100 tin gần nhất trong text channel.
- Mỗi Discord message được chuẩn hoá sang raw schema hiện có, giữ `message.jump_url`, links, attachments, author/channel/time và chống trùng theo Discord message ID.
- Chỉ dữ liệu có dấu hiệu logistics/tài liệu khoá học mới được ingest; tin nhắn bot và chat thông thường bị bỏ qua.
- Data crawl runtime được ghi vào `codebase/runtime/` (đã gitignore), sau đó dùng lại `RawJsonExtractorAgent` và provider/fallback hiện có. File fixture `../discord_message.json` vẫn là dữ liệu demo được track.

### 3) `DeadlineReminderAgent`
Tools:
- `get_current_time()` — lấy thời gian hiện tại Asia/Saigon.
- `check_deadlines(within_hours=72)` — kiểm tra deadline trong N giờ tới hoặc đã quá hạn.
- `latest_deadline(include_overdue=False)` — so sánh với thời gian hiện tại và trả về deadline gần nhất sắp tới.
- `make_reminders(within_hours=72)` — tạo nhắc nhở deadline.
- `run_tool(tool, **kwargs)` — API chung để gọi tool.

### 4) `StructuredSearchAgent`
- Fixture mode dùng structured output mẫu.
- Khi crawler hoạt động, search dùng `codebase/runtime/structured_discord.json`, cùng source với API/Q&A.

- `search(query, sections=None, limit=10)`
- `search_deadlines(query, limit=10)`

### 5) `AutoToolQAAgent`
Một mini tool-calling framework trong `backend/agents.py`:
- Tự gọi `get_current_time` trước.
- Nếu câu hỏi hỏi deadline gần nhất/mới nhất/tiếp theo → gọi `latest_deadline`.
- Nếu câu hỏi liên quan deadline → gọi `search_deadlines`.
- Ngược lại → gọi `search_structured_json`.
- Nếu có NVIDIA/OpenAI key, có thể dùng Llama để synthesize câu trả lời từ tool results; nếu không có, trả lời deterministic.

## Web dashboard

Mở dashboard sẽ thấy:
- Thống kê tổng quan
- Deadline gần nhất
- Q&A agent
- Deadline list
- Reminder list
- Announcements
- Meetings/resources
- Questions/discussions
- Search results
- Structured JSON viewer

## Chạy

Từ root repo:

```bash
python codebase/app.py
```

Mở:

```txt
http://localhost:8000
```

Hoặc chạy backend trực tiếp:

```bash
python codebase/backend/server.py
```

### Chạy crawler Discord thật (tuỳ chọn)

1. Trong Discord Developer Portal, bật **Message Content Intent**. Invite bot vào test guild với quyền **View Channel**, **Read Message History**, **Send Messages** và quyền đọc nội dung tin nhắn.
2. Copy **root** `.env.example` thành **root** `.env` (cùng cấp `README.md`), điền `DISCORD_BOT_TOKEN` và ít nhất một trong `DISCORD_ALLOWED_GUILD_IDS` / `DISCORD_ALLOWED_CHANNEL_IDS`. Chỉ dùng `DISCORD_ALLOW_ALL=1` cho private test bot.
3. Cài SDK tuỳ chọn, khởi động API/dashboard ở terminal 1, rồi chạy crawler ở terminal 2:

```bash
pip install -r codebase/requirements-discord.txt
python codebase/app.py
python codebase/backend/discord_bot.py
```

Bot ingest message mới, update/delete message và hỗ trợ `!scan_history 30` trong allowed text channel/thread. Xem trạng thái không có secret tại `GET /api/crawler/status`. Không có token hoặc `discord.py` thì chỉ crawler dừng với thông báo rõ ràng; dashboard/API vẫn chạy bình thường. Không commit token, Discord message thật, hoặc nội dung trong `codebase/runtime/`.

## Lệnh hữu ích

Trích xuất JSON bằng fallback local:

```bash
python codebase/app.py extract
```

Trích xuất bằng Llama/NVIDIA nếu `.env` có key:

```bash
python codebase/app.py extract --llm
python codebase/app.py --refresh --llm
```

## API

- `GET /api/raw`
- `GET /api/structured`
- `GET /api/structured?refresh=1&llm=1`
- `GET /api/crawler/status`
- `GET /api/time`
- `GET /api/deadlines/check?hours=72`
- `GET /api/deadlines/latest`
- `GET /api/reminders?hours=72`
- `GET /api/search?q=venture&section=deadlines`
- `GET /api/qa?q=Deadline%20gần%20nhất%20là%20gì?`
- `POST /api/qa` với body `{ "question": "Deadline gần nhất là gì?" }`
- `GET /api/agent/tool?tool=latest_deadline`
- `GET /api/agent/tool?tool=check_deadlines&hours=72`
