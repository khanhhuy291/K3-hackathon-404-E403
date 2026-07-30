# Hướng dẫn Nâng cấp / Migration từ JSON sang PostgreSQL (For Humans & AI)

Tài liệu này hướng dẫn cách chuyển đổi hệ thống lưu trữ từ file `storage.json` cục bộ sang cơ sở dữ liệu **PostgreSQL** để tăng tính ổn định, hỗ trợ truy vấn phức tạp và an toàn dữ liệu. Tài liệu này được thiết kế để cả lập trình viên và AI Assistant có thể hiểu và thực thi.

---

## Dành cho Người dùng (For Humans)

Nếu bạn đang chạy phiên bản cũ (lưu dữ liệu vào `storage.json`) và muốn nâng cấp lên bản PostgreSQL mà **không làm mất dữ liệu hiện tại**, hãy làm theo 6 bước sau:

### Bước 1: Lấy mã nguồn mới nhất (Pull latest code)
Đảm bảo bạn đã pull/cập nhật phiên bản code mới nhất bao gồm các file `docker-compose.yml`, `init.sql`, `migrate_data.py` và các file mã nguồn đã được nâng cấp.

### Bước 2: Khởi động Database với Docker
Hệ thống sử dụng Docker để chạy PostgreSQL một cách cô lập.
Mở Terminal/Command Prompt tại thư mục gốc của dự án và chạy:
```bash
docker compose up -d
```
*Lưu ý: Hệ thống sử dụng cổng `5433` (map vào 5432 của container) để tránh xung đột với DB cục bộ của bạn.*

### Bước 3: Cập nhật biến môi trường (.env)
Mở file `.env` (nếu chưa có thì copy từ `.env.example`) và thêm chuỗi kết nối Database:
```env
DATABASE_URL=postgresql://postgres:password@localhost:5433/deadline_db
```

### Bước 4: Cài đặt thư viện Python mới
Cài đặt thư viện `psycopg2-binary` để Python có thể giao tiếp với PostgreSQL:
```bash
pip install psycopg2-binary
```

### Bước 5: Chạy Script chuyển đổi dữ liệu (Migrate Data)
Để không bị mất các thông báo và deadline cũ, hãy chạy script chuyển đổi. Nó sẽ đọc dữ liệu từ `storage.json` và đẩy vào Database mới.
```bash
python3 migrate_data.py
```
*Nếu bạn chưa từng có dữ liệu cũ, bạn có thể bỏ qua bước này.*

### Bước 6: Khởi động lại Server
Tắt server Python cũ nếu đang chạy và bật lại để áp dụng kết nối mới:
```bash
python3 codebase/python/main_api.py
```
Khởi động lại frontend web server (nếu cần) và F5 lại trang Dashboard trên trình duyệt.

---

## Dành cho AI Assistant (For AI / System Context)

**Context:** The architecture has been migrated from flat-file storage (`codebase/data/storage.json`) to a relational PostgreSQL database.

**Key Components & Changes:**
1. **Infrastructure:**
   - PostgreSQL 15 runs via `docker-compose.yml` on host port `5433`.
   - Database name: `deadline_db`, User: `postgres`, Password: `password`.
   - Initial schema is automatically provisioned via `codebase/data/init.sql`.

2. **Schema Definition (`init.sql`):**
   - `stats` (id, user_name, group_name, sub_title, synced_sources)
   - `deadlines` (id, title, course, due_date, due_relative, source, status, priority)
   - `notifications` (id, title, summary, course, source, time_relative, content, is_read)
   - `documents` (id, name, file_type, course, source, updated_date, url)

3. **Backend Logic (`codebase/python/storage_manager.py`):**
   - Uses `psycopg2` with `RealDictCursor` to return dictionary-like rows.
   - `load_storage()` executes `SELECT` across all tables and returns the exact same dictionary structure as the old JSON file to maintain 100% backward compatibility with the frontend.
   - ID Generation for new items uses `uuid.uuid4().hex[:8]` to prevent collisions.

4. **Frontend Integration:**
   - `app.js` and `index.html` have been scrubbed of "storage.json" local fallbacks.
   - The UI communicates strictly through the backend REST API (`/api/storage`, `/api/process-message`, etc.).

**Actionable Rule for Future Edits:** 
Any new data fields or features requiring persistence MUST be added as columns to the PostgreSQL schema (`init.sql`) and handled via SQL queries in `storage_manager.py`. DO NOT attempt to write back to `storage.json`.
