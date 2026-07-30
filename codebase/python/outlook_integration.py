"""
Microsoft Outlook & Graph API Integration (Python Version)
Thư viện cần cài: pip install requests
"""

import os
import requests
from typing import List, Dict, Any
from llm_engine import extract_deadline_gemini

def fetch_unread_outlook_emails(access_token: str) -> List[Dict[str, Any]]:
    """Lấy danh sách các Email chưa đọc từ Outlook qua Microsoft Graph API"""
    url = "https://graph.microsoft.com/v1.0/me/messages?$filter=isRead eq false&$top=10"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json().get("value", [])


def create_outlook_calendar_event(access_token: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """Tự động đẩy sự kiện vào Outlook Calendar của người dùng"""
    url = "https://graph.microsoft.com/v1.0/me/events"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    due_date_str = task_data.get("due_date") or "2026-08-15 23:59"
    formatted_date = due_date_str.replace(" ", "T") + ":00"

    payload = {
        "subject": f"[Deadline] {task_data.get('course')}: {task_data.get('title')}",
        "body": {
            "contentType": "HTML",
            "content": f"<p>Được trích xuất tự động từ Trợ lý AI.</p><p><b>Trích dẫn:</b> {task_data.get('quote')}</p>"
        },
        "start": {
            "dateTime": formatted_date,
            "timeZone": "SE Asia Standard Time"
        },
        "end": {
            "dateTime": formatted_date,
            "timeZone": "SE Asia Standard Time"
        },
        "reminderMinutesBeforeStart": 120
    }

    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()


def process_outlook_emails_pipeline(access_token: str, gemini_api_key: str):
    """Luồng xử lý tự động (Pipeline): Đọc mail -> Gọi AI -> Tạo Lịch Outlook"""
    print("📥 Đang quét email mới từ Outlook...")
    emails = fetch_unread_outlook_emails(access_token)
    
    for email in emails:
        raw_text = f"Subject: {email.get('subject')}\nBody: {email.get('bodyPreview')}"
        print(f"🔎 Đang phân tích email: '{email.get('subject')}'")

        extracted = extract_deadline_gemini(raw_text, gemini_api_key)

        if extracted.get("is_deadline") and extracted.get("due_date"):
            print("📌 Phát hiện Deadline! Đang tạo sự kiện Lịch...", extracted)
            create_outlook_calendar_event(access_token, extracted)
            print("✅ Đã tự động thêm deadline vào Lịch Outlook của bạn thành công!")


if __name__ == "__main__":
    print("💡 Module tích hợp Microsoft Graph API Python sẵn sàng!")
