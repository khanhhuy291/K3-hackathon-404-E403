"""
JSON Storage Manager (Python)
Quản lý lưu trữ local các thông báo, deadline và tài liệu dưới dạng JSON.
"""

import os
import json
from typing import Dict, Any, List

STORAGE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "storage.json")

def load_storage() -> Dict[str, Any]:
    """Đọc dữ liệu từ file storage.json"""
    if not os.path.exists(STORAGE_FILE):
        return {"stats": {}, "deadlines": [], "notifications": [], "documents": []}
    try:
        with open(STORAGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Lỗi đọc storage.json: {e}")
        return {"stats": {}, "deadlines": [], "notifications": [], "documents": []}

def save_storage(data: Dict[str, Any]) -> bool:
    """Ghi dữ liệu vào storage.json"""
    try:
        os.makedirs(os.path.dirname(STORAGE_FILE), exist_ok=True)
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Lỗi ghi storage.json: {e}")
        return False

def add_extracted_item(extracted_data: Dict[str, Any], source: str = "Discord") -> Dict[str, Any]:
    """Thêm một item được AI trích xuất từ Discord vào storage local (CÓ CHỐNG TRÙNG LẶP DEDUPLICATION)"""
    storage = load_storage()
    
    # Cập nhật số nguồn đồng bộ (Tập trung 100% vào Discord)
    storage.setdefault("stats", {})["synced_sources"] = 1
    
    quote = (extracted_data.get("quote") or "Nội dung thông báo").strip()
    title = (extracted_data.get("title") or "Thông báo mới").strip()
    course = (extracted_data.get("course") or "Chung").strip()

    # 1. KIỂM TRA CHỐNG TRÙNG LẶP (DEDUPLICATION) FOR NOTIFICATIONS
    existing_notifs = storage.get("notifications", [])
    for n in existing_notifs:
        if n.get("content", "").strip() == quote or (n.get("title", "").strip() == title and n.get("course", "").strip() == course):
            print(f"⚠️ [ĐÃ TỒN TẠI]: Bỏ qua tin trùng lặp \"{title}\"")
            return {"notification": n, "is_duplicate": True}

    # 1. Thêm Notification mới nếu chưa tồn tại
    notif_id = f"notif-{len(existing_notifs) + 1}"
    new_notif = {
        "id": notif_id,
        "title": title,
        "course": course,
        "source": source,
        "time_relative": "Vừa xong",
        "content": quote,
        "is_read": False
    }
    existing_notifs.insert(0, new_notif)
    storage["notifications"] = existing_notifs

    # 2. Thêm Deadline (Nếu có & Chưa trùng)
    new_deadline = None
    if extracted_data.get("is_deadline"):
        existing_dls = storage.get("deadlines", [])
        dl_exists = any(d.get("title", "").strip() == title and d.get("course", "").strip() == course for d in existing_dls)
        if not dl_exists:
            dl_id = f"dl-{len(existing_dls) + 1}"
            new_deadline = {
                "id": dl_id,
                "title": title,
                "course": course,
                "due_date": extracted_data.get("due_date") or "2026-08-15 23:59",
                "due_relative": "Sắp tới",
                "source": source,
                "status": "Đang làm",
                "priority": extracted_data.get("priority") or "Trung bình"
            }
            existing_dls.insert(0, new_deadline)
            storage["deadlines"] = existing_dls

    # 3. Thêm Document (Nếu có & Chưa trùng)
    if extracted_data.get("is_course_resource") or "http" in quote.lower():
        existing_docs = storage.get("documents", [])
        doc_exists = any(d.get("name", "").strip() == title for d in existing_docs)
        if not doc_exists:
            doc_id = f"doc-{len(existing_docs) + 1}"
            new_doc = {
                "id": doc_id,
                "name": title,
                "file_type": "SLIDE/LINK",
                "course": course,
                "source": source,
                "updated_date": "Hôm nay",
                "url": "#"
            }
            existing_docs.insert(0, new_doc)
            storage["documents"] = existing_docs

    save_storage(storage)
    return {"notification": new_notif, "deadline": new_deadline, "is_duplicate": False}

def mark_notification_read(notif_id: str = None) -> Dict[str, Any]:
    """Đánh dấu 1 hoặc tất cả thông báo là đã đọc"""
    storage = load_storage()
    for n in storage.get("notifications", []):
        if notif_id is None or n.get("id") == notif_id:
            n["is_read"] = True
    save_storage(storage)
    return storage
