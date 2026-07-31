# SETUP — Chạy local (Windows)

## 1. Môi trường Python

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 2. Cấu hình `.env`

Copy `.env.example` → `.env` rồi điền key. File `.env` đã nằm trong `.gitignore`, **không commit**.

| Biến | Bắt buộc? | Ghi chú |
|---|---|---|
| `DISCORD_BOT_TOKEN` | Có (để chạy bot) | Lấy ở Developer Portal, xem §3 |
| `OPENROUTER_API_KEY` | Chọn 1 | Ưu tiên cao nhất |
| `GEMINI_API_KEY` | Chọn 1 | Dùng khi không có OpenRouter |
| `OPENAI_API_KEY` | Chọn 1 | |
| `MICROSOFT_GRAPH_ACCESS_TOKEN` | Không | Nhánh Outlook, tùy chọn |

Nếu **để trống hết** key LLM → `llm_engine.py` tự fallback sang `extract_deadline_local()`
(regex parser, không gọi mạng). Bot vẫn chạy được nhưng **không tính là "AI call thật"** theo rubric.

> Lưu ý: đừng để nguyên placeholder `your_openrouter_api_key_here` — `extract_deadline_gemini()`
> chỉ loại placeholder viết HOA (`YOUR_OPENROUTER_API_KEY`), nên chuỗi thường sẽ bị coi là key thật,
> gọi API thất bại rồi mới fallback. Để trống sạch hơn.

## 3. Tạo Discord Bot

1. https://discord.com/developers/applications → **New Application**
2. Tab **Bot** → **Reset Token** → copy vào `DISCORD_BOT_TOKEN` trong `.env`
3. Tab **Bot** → **Privileged Gateway Intents** → bật **MESSAGE CONTENT INTENT** ✅
   (bắt buộc — `discord_bot.py` dùng `intents.message_content = True`, thiếu sẽ crash `PrivilegedIntentsRequired`)
4. Tab **OAuth2 → URL Generator**:
   - Scopes: `bot`
   - Bot Permissions: `Read Messages/View Channels`, `Send Messages`, `Read Message History`, `Embed Links`
   - Mở URL sinh ra → invite bot vào server test
5. Bot chỉ đọc được channel mà nó có quyền xem — kiểm tra permission của channel.

## 4. Chạy

```powershell
.\run_bot.ps1     # Discord bot listener
.\run_api.ps1     # REST API backend tại http://localhost:8000
```

Web dashboard: mở `codebase/index.html` trực tiếp bằng trình duyệt.

> `PYTHONIOENCODING=utf-8` được set sẵn trong 2 script trên. Chạy `python discord_bot.py` tay
> trên PowerShell sẽ lỗi `UnicodeEncodeError: 'charmap' codec` vì console Windows mặc định cp1252.

## 5. Test bot

Trong channel bot đã join:

- Gõ tin thường: `Thầy gửi bài tập 2 môn Machine Learning. Hạn nộp trước 23:59 ngày 15/08/2026.`
  → bot reply embed có Hạn nộp / Ưu tiên / Trích dẫn, đồng thời ghi vào `codebase/data/storage.json`
- `!scan_history 30` → quét 30 tin cũ trong channel, tìm deadline bị trôi
