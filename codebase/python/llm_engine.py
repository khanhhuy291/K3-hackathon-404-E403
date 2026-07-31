"""
LLM Extraction Engine (Python Version)
Sử dụng Google Gemini API hoặc OpenAI API để trích xuất Deadline có cấu trúc JSON.
"""

import os
import json
import re
import requests
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Model Pydantic định nghĩa cấu trúc JSON trả về
class DeadlineExtractionResult(BaseModel):
    is_deadline: bool = Field(description="True nếu chứa deadline/bài tập/lịch nộp bài")
    is_relevant_announcement: bool = Field(description="True nếu là thông báo quan trọng từ giảng viên/lớp học")
    is_course_resource: bool = Field(description="True nếu chứa link tài liệu, slide, drive, file đính kèm")
    out_of_scope: bool = Field(description="True nếu người dùng hỏi xin gia hạn, nhờ giải bài tập")
    course: Optional[str] = Field(default=None, description="Tên môn học")
    title: Optional[str] = Field(default=None, description="Tiêu đề ngắn gọn thông báo/tài liệu/task")
    summary: Optional[str] = Field(default=None, description="Tóm tắt ngắn 1-2 câu nội dung cốt lõi của thông báo")
    due_date: Optional[str] = Field(default=None, description="Hạn nộp YYYY-MM-DD HH:mm (Quy đổi về giờ VN UTC+7)")
    priority: str = Field(default="MEDIUM", description="HIGH | MEDIUM | LOW")
    confidence: float = Field(default=95.0, description="Độ tự tin của AI (0-100)")
    warning_flag: Optional[str] = Field(default=None, description="MISSING_EXACT_DATE | CONVERTED_FROM_UTC | OUT_OF_SCOPE | NO_RELEVANCE")
    quote: str = Field(description="Trích dẫn đoạn văn gốc")


from datetime import datetime, timedelta
import re

# Thứ trong tuần: datetime.weekday() trả Monday=0 ... Sunday=6
_WEEKDAY_VI = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]

def _now_str() -> str:
    """Mốc thời gian hiện tại đưa vào prompt.

    KHÔNG đặt ký tự có dấu trong format string của strftime: trên Windows strftime
    đi qua locale codec (cp1258) và ném UnicodeEncodeError, khiến lời gọi LLM chết
    trước khi kịp gửi request rồi bị except nuốt mất -> âm thầm rơi về local parser.
    """
    n = datetime.now()
    return f"{n.strftime('%Y-%m-%d %H:%M')} ({_WEEKDAY_VI[n.weekday()]})"


_RESOURCE_HINTS = ["http://", "https://", "docs.google", "drive.google", "slide", "tài liệu"]

def _normalize_extraction(res: Dict[str, Any], raw_text: str) -> Dict[str, Any]:
    """Chuẩn hoá output của LLM về đúng contract mà discord_bot.py / storage_manager.py trông đợi.

    LLM hay trả thiếu field hoặc sai thang đo; discord_bot.py lọc tin bằng
    is_deadline / is_relevant_announcement / is_course_resource nên field thiếu (None)
    sẽ khiến tin bị bỏ qua oan.
    """
    for flag in ("is_deadline", "is_relevant_announcement", "is_course_resource", "out_of_scope"):
        res[flag] = bool(res.get(flag))

    # confidence: một số model trả thang 0-1, embed lại hiển thị dạng phần trăm
    try:
        conf = float(res.get("confidence") or 0)
    except (TypeError, ValueError):
        conf = 0.0
    res["confidence"] = round(conf * 100, 1) if conf <= 1 else round(conf, 1)

    lower = raw_text.lower()
    if any(k in lower for k in _RESOURCE_HINTS):
        res["is_course_resource"] = True
        res["is_relevant_announcement"] = True
        if not res.get("title"):
            res["title"] = "Tài liệu môn học"

    res.setdefault("priority", "MEDIUM")
    if not res.get("quote"):
        res["quote"] = raw_text[:150]
    return res

def extract_deadline_local(raw_text: str) -> Dict[str, Any]:
    """Engine xử lý AI local linh hoạt: Phân loại thông báo quan trọng vs Tin rác trò chuyện"""
    lower = raw_text.lower()
    
    # 1. Out of scope Check
    if any(k in lower for k in ["gia hạn", "xin nghỉ", "giải giúp", "giải bài", "thầy ơi cho em xin"]):
        return {
            "is_deadline": False,
            "is_relevant_announcement": False,
            "is_course_resource": False,
            "out_of_scope": True,
            "course": None,
            "title": None,
            "due_date": None,
            "priority": "LOW",
            "confidence": 98.0,
            "warning_flag": "OUT_OF_SCOPE",
            "quote": raw_text[:150]
        }

    # 2. Check Document / Course Resource (Drive, Google Docs, Presentation, PDF, File)
    has_resource_link = any(k in lower for k in ["http://", "https://", "drive.google", "docs.google", "slide", "tài liệu", "presentation", ".pdf", ".docx"])
    
    # 3. Check Deadline / Official Announcement Keywords
    deadline_keywords = ["hạn nộp", "due date", "nộp bài", "nộp trước", "mở đến", "thi cuối kỳ", "quiz", "chốt slide", "bài tập", "hạn cuối", "close at", "nộp lại", "update", "submission"]
    has_deadline = any(k in lower for k in deadline_keywords)

    announcement_keywords = ["thông báo", "thầy", "cô", "hoãn buổi", "dời lịch", "đăng ký", "nhắc nhở", "nhắc", "lớp", "học kỳ", "kick-off", "workshop"]
    has_announcement = any(k in lower for k in announcement_keywords)

    # Nếu KHÔNG có deadline, KHÔNG có tài liệu, KHÔNG phải thông báo chính thức -> TIN RÁC / TRÒ CHUYỆN -> BỎ QUA
    if not has_deadline and not has_resource_link and not has_announcement:
        return {
            "is_deadline": False,
            "is_relevant_announcement": False,
            "is_course_resource": False,
            "out_of_scope": False,
            "course": None,
            "title": None,
            "due_date": None,
            "priority": "LOW",
            "confidence": 90.0,
            "warning_flag": "NO_RELEVANCE",
            "quote": raw_text[:150]
        }

    # 4. Extract Dynamic Course & Title
    course_match = re.search(r'môn\s+([A-Za-z0-9\s]+?)(?=\.|\,|\n|hạn|lúc|$)', raw_text, re.IGNORECASE)
    course = course_match.group(1).strip() if course_match else ("Workshop/Lớp học" if "workshop" in lower or "kick-off" in lower else "Môn học chung")

    title_match = re.search(r'([A-Za-z0-9\s\-_]+(?:workshop|kick-off|assignment|quiz|bài tập|thông báo|slide)[A-Za-z0-9\s\-_]*)', lower)
    title = title_match.group(1).strip().title() if title_match else ("Tài liệu " + course if has_resource_link else "Thông báo lớp học")

    # 5. Extract Dynamic Date
    now = datetime.now()
    due_date = None
    warning_flag = None

    if has_deadline:
        date_match = re.search(r'(\d{1,2})[/.-](\d{1,2})(?:[/.-](\d{4}))?', raw_text)
        time_match = re.search(r'(\d{1,2})[h:](\d{2})?', lower)

        hour = time_match.group(1).zfill(2) if time_match else "23"
        minute = time_match.group(2).zfill(2) if time_match and time_match.group(2) else ("00" if time_match else "59")

        if date_match:
            day = date_match.group(1).zfill(2)
            month = date_match.group(2).zfill(2)
            year = date_match.group(3) if date_match.group(3) else str(now.year)
            due_date = f"{year}-{month}-{day} {hour}:{minute}"
        elif "utc" in lower:
            warning_flag = "CONVERTED_FROM_UTC"
            due_date = (now + timedelta(days=2)).strftime("%Y-%m-%d 06:59")
        elif any(term in lower for term in ["tối nay", "hôm nay", "tuần sau", "buổi học tới"]):
            warning_flag = "MISSING_EXACT_DATE"
            due_date = None
        else:
            due_date = (now + timedelta(days=3)).strftime(f"%Y-%m-%d {hour}:{minute}")

    return {
        "is_deadline": has_deadline,
        "is_relevant_announcement": has_announcement or has_deadline,
        "is_course_resource": has_resource_link,
        "out_of_scope": False,
        "course": course,
        "title": title,
        "due_date": due_date,
        "priority": "HIGH" if any(k in lower for k in ["thi", "assignment", "cuối kỳ"]) else "MEDIUM",
        "confidence": 95.0,
        "warning_flag": warning_flag,
        "quote": raw_text[:150]
    }


def extract_deadline_openrouter(raw_text: str, api_key: str = None, model: str = None) -> Dict[str, Any]:
    """Trích xuất deadline bằng OpenRouter API (Hỗ trợ tất cả mô hình Gemini/GPT-4o/Claude/DeepSeek)"""
    key = api_key or os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not key or "YOUR_OPENROUTER_API_KEY" in key or key.startswith("sk-or-v1-YOUR"):
        return extract_deadline_local(raw_text)

    chosen_model = model or os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    url = "https://openrouter.ai/api/v1/chat/completions"
    current_time_str = _now_str()

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "Smart Deadline Assistant"
    }

    system_prompt = f"""
Bạn là Trợ lý AI chuyên phân loại và trích xuất thông tin Thông báo, Deadline, và Tài liệu từ tin nhắn Discord.
Thời điểm hiện tại của hệ thống: {current_time_str}.
Hãy quy đổi các từ tương đối ("tối nay", "ngày mai", "thứ 6 tuần sau", "UTC") thành ngày giờ chính xác YYYY-MM-DD HH:mm.

Trả về duy nhất 1 JSON object chuẩn chứa các trường bắt buộc sau:
{{
  "is_deadline": boolean (true nếu có thông tin về bài tập/quiz/thi/hạn nộp bài),
  "is_relevant_announcement": boolean (true nếu là thông báo chính thức từ thầy cô/lớp học/workshop/thay đổi lịch),
  "is_course_resource": boolean (true nếu chứa link tài liệu, slide, drive, google docs, presentation, file đính kèm),
  "out_of_scope": boolean (true nếu người dùng xin gia hạn, nhờ giải bài tập),
  "course": string hoặc null (Tên môn học hoặc tên Workshop/Lớp học),
  "title": string hoặc null (Tiêu đề ngắn gọn của thông báo hoặc tài liệu),
  "due_date": string hoặc null (định dạng YYYY-MM-DD HH:mm nếu có deadline, null nếu không có),
  "priority": "HIGH" | "MEDIUM" | "LOW",
  "confidence": number (từ 0 đến 100),
  "warning_flag": string hoặc null,
  "quote": string (trích dẫn câu văn gốc)
}}
"""

    payload = {
        "model": chosen_model,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": raw_text}
        ]
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        res_json = json.loads(content)
        
        # Bổ sung hậu xử lý an toàn nếu LLM thiếu field
        return _normalize_extraction(res_json, raw_text)
    except Exception as e:
        print(f"⚠️ Gọi OpenRouter API thất bại ({e}). Tự động dùng Local Parser...")
        return extract_deadline_local(raw_text)


def extract_deadline_gemini(raw_text: str, api_key: str = None) -> Dict[str, Any]:
    """Trích xuất deadline bằng Google Gemini API hoặc OpenRouter API"""
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key and not "YOUR_OPENROUTER_API_KEY" in openrouter_key:
        print("🌐 Dùng OpenRouter API để trích xuất Metadata AI...")
        return extract_deadline_openrouter(raw_text)

    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key or "YOUR_GEMINI_API_KEY" in key or key.startswith("AIzaSy_YOUR"):
        print("ℹ️ Dùng Chế độ AI Local Parser (Do chưa có API Key hợp lệ trong .env)")
        return extract_deadline_local(raw_text)

    try:
        current_time_str = _now_str()
        gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={key}"
        
        prompt = f"""
Bạn là Trợ lý AI chuyên trích xuất thông tin Deadline và Lịch học từ thông báo thô.
Thời điểm hiện tại của hệ thống: {current_time_str}.
Hãy sử dụng thời điểm hiện tại này để quy đổi các từ tương đối ("tối nay", "ngày mai", "thứ 6 tuần sau", "UTC") thành ngày giờ chính xác YYYY-MM-DD HH:mm.

Nội dung thông báo thô:
"{raw_text}"

Cấu trúc JSON bắt buộc (KHÔNG thêm markdown hay chữ thừa):
{{
  "is_deadline": boolean (true nếu có thông tin về bài tập/quiz/thi/hạn nộp bài),
  "is_relevant_announcement": boolean (true nếu là thông báo chính thức từ thầy cô/lớp học/workshop/thay đổi lịch),
  "is_course_resource": boolean (true nếu chứa link tài liệu, slide, drive, google docs, presentation, file đính kèm),
  "out_of_scope": boolean (CHỈ true khi người dùng xin gia hạn, xin nghỉ, hoặc nhờ giải hộ bài tập.
      Tin nhắn tán gẫu không liên quan KHÔNG phải out_of_scope — để tất cả cờ boolean là false),
  "course": string hoặc null (Tên môn học hoặc tên Workshop/Lớp học),
  "title": string hoặc null (Tiêu đề ngắn gọn của thông báo hoặc tài liệu),
  "due_date": string hoặc null (định dạng YYYY-MM-DD HH:mm, null nếu không có deadline),
  "priority": "HIGH" | "MEDIUM" | "LOW",
  "confidence": number nguyên từ 0 đến 100 (KHÔNG dùng thang 0-1),
  "warning_flag": string hoặc null (chỉ dùng 1 trong: MISSING_EXACT_DATE | CONVERTED_FROM_UTC | OUT_OF_SCOPE | NO_RELEVANCE),
  "quote": string (trích dẫn nguyên văn câu gốc)
}}
"""

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"}
        }

        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
        response.raise_for_status()

        data = response.json()
        json_str = data["candidates"][0]["content"]["parts"][0]["text"]
        return _normalize_extraction(json.loads(json_str), raw_text)
    except Exception as e:
        print(f"⚠️ Gọi Gemini API thất bại ({e}). Tự động dùng Local Parser...")
        return extract_deadline_local(raw_text)


def extract_deadline_openai(raw_text: str, api_key: str = None) -> Dict[str, Any]:
    """Trích xuất deadline bằng OpenAI API (gpt-4o-mini)"""
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError("Chưa cung cấp OPENAI_API_KEY")

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4o-mini",
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": "Bạn là Trợ lý trích xuất deadline học tập. Trả về JSON với các trường: is_deadline, out_of_scope, course, title, due_date, priority, confidence, warning_flag, quote."
            },
            {
                "role": "user",
                "content": raw_text
            }
        ]
    }

    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    data = response.json()
    return json.loads(data["choices"][0]["message"]["content"])


if __name__ == "__main__":
    sample = "[Discord #announcements] Thầy gửi assignment 2 môn Machine Learning. Hạn nộp bài là trước 23:59 ngày 15/08/2026."
    print("Test Sample:", sample)
    # res = extract_deadline_gemini(sample, "YOUR_GEMINI_KEY")
    # print(json.dumps(res, indent=2, ensure_ascii=False))
