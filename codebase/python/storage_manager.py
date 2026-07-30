"""
PostgreSQL Storage Manager (Python)
Quản lý lưu trữ local các thông báo, deadline và tài liệu dưới dạng Database.
"""

import os
import json
import re
import uuid
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, Any, List

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5433/deadline_db")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def load_storage() -> Dict[str, Any]:
    """Đọc dữ liệu từ file storage.json -> Giờ là PostgreSQL"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Load stats
        cur.execute("SELECT * FROM stats LIMIT 1")
        stats = cur.fetchone()
        if not stats:
            stats = {"user_name": "Minh", "synced_sources": 1}
        else:
            stats = dict(stats)
            
        # Load deadlines
        cur.execute("SELECT * FROM deadlines ORDER BY due_date ASC")
        deadlines = [dict(row) for row in cur.fetchall()]
        
        # Load notifications
        cur.execute("SELECT * FROM notifications ORDER BY id DESC")
        notifications = [dict(row) for row in cur.fetchall()]
        
        # Load documents
        cur.execute("SELECT * FROM documents ORDER BY id DESC")
        documents = [dict(row) for row in cur.fetchall()]
        
        cur.close()
        conn.close()
        return {
            "stats": stats,
            "deadlines": deadlines,
            "notifications": notifications,
            "documents": documents
        }
    except Exception as e:
        print(f"Lỗi đọc Database: {e}")
        return {"stats": {}, "deadlines": [], "notifications": [], "documents": []}

def save_storage(data: Dict[str, Any]) -> bool:
    """Ghi dữ liệu vào storage.json -> Khong can thiet khi dung DB"""
    pass

def extract_url_from_text(text: Any) -> str:
    """Hàm trích xuất URL an toàn 100% không bao giờ gây lỗi crash"""
    if not text:
        return "#"
    try:
        text_str = str(text)
        match = re.search(r'https?://[^\s<>"]+', text_str)
        if match:
            url = match.group(0)
            while url and url[-1] in ").,;:'\"":
                url = url[:-1]
            return url if url else "#"
    except Exception as e:
        print(f"Lỗi trích xuất URL: {e}")
    return "#"

def add_extracted_item(extracted_data: Dict[str, Any], source: str = "Discord") -> Dict[str, Any]:
    """Tự động thêm dữ liệu đã trích xuất vào DB (có chống trùng lặp)"""
    quote = (extracted_data.get("quote") or "Nội dung thông báo").strip()
    title = (extracted_data.get("title") or "Thông báo mới").strip()
    course = (extracted_data.get("course") or "Chung").strip()
    summary = (extracted_data.get("summary") or quote[:120]).strip()

    title_norm = title.lower().strip()
    quote_norm = quote.lower().strip()

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 1. KIỂM TRA CHỐNG TRÙNG LẶP CHO THÔNG BÁO
        cur.execute("SELECT * FROM notifications")
        existing_notifs = cur.fetchall()
        for n in existing_notifs:
            n_title = (n.get("title") or "").lower().strip()
            n_content = (n.get("content") or "").lower().strip()
            if n_title == title_norm or (len(quote_norm) > 10 and (quote_norm in n_content or n_content in quote_norm)):
                print(f"⚠️ [ĐÃ TỒN TẠI]: Bỏ qua tin trùng lặp \"{title}\"")
                cur.close()
                conn.close()
                return {"notification": dict(n), "is_duplicate": True}

        # 1. Thêm Notification mới
        notif_id = f"notif-{uuid.uuid4().hex[:8]}"
        cur.execute(
            "INSERT INTO notifications (id, title, summary, course, source, time_relative, content, is_read) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (notif_id, title, summary, course, source, "Vừa xong", quote, False)
        )
        new_notif = {
            "id": notif_id, "title": title, "summary": summary, "course": course,
            "source": source, "time_relative": "Vừa xong", "content": quote, "is_read": False
        }

        # 2. Thêm Deadline
        new_deadline = None
        if extracted_data.get("is_deadline"):
            cur.execute("SELECT id FROM deadlines WHERE LOWER(title) = %s", (title_norm,))
            if not cur.fetchone():
                dl_id = f"dl-{uuid.uuid4().hex[:8]}"
                due_date = extracted_data.get("due_date") or "2026-08-15 23:59"
                priority = extracted_data.get("priority") or "Trung bình"
                cur.execute(
                    "INSERT INTO deadlines (id, title, course, due_date, due_relative, source, status, priority) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (dl_id, title, course, due_date, "Sắp tới", source, "Đang làm", priority)
                )
                new_deadline = {
                    "id": dl_id, "title": title, "course": course, "due_date": due_date,
                    "due_relative": "Sắp tới", "source": source, "status": "Đang làm", "priority": priority
                }

        # 3. Thêm Document
        doc_url = extract_url_from_text(quote)
        if extracted_data.get("is_course_resource") or doc_url != "#":
            cur.execute("SELECT id FROM documents WHERE LOWER(name) = %s", (title_norm,))
            if not cur.fetchone():
                doc_id = f"doc-{uuid.uuid4().hex[:8]}"
                file_type = "SLIDE/LINK" if any(k in doc_url.lower() for k in ["google.com", "drive", "presentation", "slide"]) else "LINK"
                cur.execute(
                    "INSERT INTO documents (id, name, file_type, course, source, updated_date, url) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (doc_id, title, file_type, course, source, "Hôm nay", doc_url)
                )

        conn.commit()
        cur.close()
        conn.close()
        return {"notification": new_notif, "deadline": new_deadline, "is_duplicate": False}
    except Exception as e:
        print(f"Lỗi thêm dữ liệu: {e}")
        return {"error": str(e), "is_duplicate": False}


def mark_notification_read(notif_id: str = None) -> Dict[str, Any]:
    """Đánh dấu 1 hoặc tất cả thông báo là đã đọc"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        if notif_id is None:
            cur.execute("UPDATE notifications SET is_read = TRUE")
        else:
            cur.execute("UPDATE notifications SET is_read = TRUE WHERE id = %s", (notif_id,))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Lỗi cập nhật notification: {e}")
    return load_storage()


def toggle_deadline_status(dl_id: str) -> Dict[str, Any]:
    """Chuyển đổi trạng thái giữa Đang làm và Hoàn thành cho Deadline"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE deadlines SET status = CASE WHEN status = 'Hoàn thành' THEN 'Đang làm' ELSE 'Hoàn thành' END WHERE id = %s",
            (dl_id,)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Lỗi cập nhật deadline: {e}")
    return load_storage()
