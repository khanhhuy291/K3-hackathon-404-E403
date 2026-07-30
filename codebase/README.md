# Discord Course AI Agents

Prototype đọc `../discord_message.json`, tách **backend** và **frontend**, tạo dashboard deadline/thông báo và Q&A agent dùng tools.

## Cấu trúc mới

```txt
codebase/
├─ app.py                    # launcher tương thích: gọi backend/server.py
├─ backend/
│  ├─ agents.py              # các agent + tool framework
│  └─ server.py              # HTTP API backend, serve frontend
├─ frontend/
│  ├─ index.html             # dashboard UI
│  ├─ app.js
│  └─ styles.css
├─ structured_discord.json   # output structured chính
└─ .env.example

codebase copy/
└─ structured_discord.json   # file search target được sync tự động
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

### 2) `DeadlineReminderAgent`
Tools:
- `get_current_time()` — lấy thời gian hiện tại Asia/Saigon.
- `check_deadlines(within_hours=72)` — kiểm tra deadline trong N giờ tới hoặc đã quá hạn.
- `latest_deadline(include_overdue=False)` — so sánh với thời gian hiện tại và trả về deadline gần nhất sắp tới.
- `make_reminders(within_hours=72)` — tạo nhắc nhở deadline.
- `run_tool(tool, **kwargs)` — API chung để gọi tool.

### 3) `StructuredSearchAgent`
Tools search trong file yêu cầu:

```txt
codebase copy/structured_discord.json
```

- `search(query, sections=None, limit=10)`
- `search_deadlines(query, limit=10)`

### 4) `AutoToolQAAgent`
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
- `GET /api/time`
- `GET /api/deadlines/check?hours=72`
- `GET /api/deadlines/latest`
- `GET /api/reminders?hours=72`
- `GET /api/search?q=venture&section=deadlines`
- `GET /api/qa?q=Deadline%20gần%20nhất%20là%20gì?`
- `POST /api/qa` với body `{ "question": "Deadline gần nhất là gì?" }`
- `GET /api/agent/tool?tool=latest_deadline`
- `GET /api/agent/tool?tool=check_deadlines&hours=72`
