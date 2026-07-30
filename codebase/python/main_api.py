"""
Python Native Backend API cho Smart Deadline Assistant
Phục vụ Web Dashboard chuẩn sản phẩm thật + Đọc/Ghi local storage.json
Chạy: python3 codebase/python/main_api.py
"""

import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from llm_engine import extract_deadline_gemini
from storage_manager import load_storage, save_storage, add_extracted_item, mark_notification_read

class DeadlineAPIHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def do_GET(self):
        self._set_headers(200)
        if self.path.startswith("/api/storage"):
            storage = load_storage()
            self.wfile.write(json.dumps(storage, ensure_ascii=False).encode('utf-8'))
        else:
            response = {
                "status": "online",
                "service": "Smart Deadline Assistant Python API",
                "endpoints": ["GET /api/storage", "POST /api/extract-deadline", "POST /api/process-message", "POST /api/mark-read"]
            }
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        if self.path == "/api/mark-read":
            try:
                payload = json.loads(post_data.decode('utf-8')) if post_data else {}
                notif_id = payload.get("notif_id", None)
                updated_storage = mark_notification_read(notif_id)
                self._set_headers(200)
                self.wfile.write(json.dumps({"success": True, "updated_storage": updated_storage}, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

        elif self.path in ["/api/extract-deadline", "/api/process-message"]:
            try:
                payload = json.loads(post_data.decode('utf-8'))
                raw_text = payload.get("raw_text", "")
                api_key = payload.get("api_key", None)
                source = payload.get("source", "Discord")

                if not raw_text:
                    self._set_headers(400)
                    self.wfile.write(json.dumps({"error": "Thiếu nội dung raw_text"}).encode('utf-8'))
                    return

                extracted = extract_deadline_gemini(raw_text, api_key)
                
                # Tự động lưu vào local storage.json (có chống trùng)
                saved_res = add_extracted_item(extracted, source=source)
                
                self._set_headers(200)
                self.wfile.write(json.dumps({
                    "success": True,
                    "extracted": extracted,
                    "saved": saved_res,
                    "updated_storage": load_storage()
                }, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Endpoint không tồn tại"}).encode('utf-8'))

def run_server(port=8000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, DeadlineAPIHandler)
    print(f"🚀 Python REST API Server đang chạy tại: http://localhost:{port}/")
    print(f"📌 Storage API: GET http://localhost:{port}/api/storage")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()
