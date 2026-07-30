# Discord Course AI Agents

Prototype đọc `../discord_message.json` và tạo dashboard deadline/thông báo.

## 2 agent

### 1) `RawJsonExtractorAgent`
- Input: JSON Discord crawl thô.
- Output: `codebase/structured_discord.json` gồm:
  - `announcements`
  - `deadlines`
  - `meetings`
  - `resources`
  - `documents`
  - `questions`
  - `timeline`
  - `stats`
- Có thể dùng Llama qua OpenAI-compatible API của NVIDIA nếu cấu hình `.env`:

```env
OPENAI_API_KEY=nvapi-...
OPENAI_BASE_URL=https://integrate.api.nvidia.com/v1
OPENAI_MODEL=meta/llama-3.1-70b-instruct
```

Nếu chưa có key hoặc API lỗi, agent tự fallback sang rule-based extraction để demo luôn chạy được.

### 2) `DeadlineReminderAgent`
Tools:
- `get_current_time()` — trả về thời gian hiện tại theo Asia/Saigon.
- `check_deadlines(within_hours=72)` — kiểm tra deadline trong N giờ tới hoặc đã quá hạn.
- `make_reminders(within_hours=72)` — tạo câu nhắc deadline với level `info/warning/danger`.

## Chạy

Từ root repo:

```bash
python codebase/app.py
```

Mở: <http://localhost:8000>

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
- `GET /api/reminders?hours=72`
