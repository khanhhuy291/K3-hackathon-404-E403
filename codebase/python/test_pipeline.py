import sys
import os

# Thêm đường dẫn hiện tại vào sys.path để import được các file khác
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm_engine import extract_deadline_gemini
from storage_manager import add_extracted_item

def run_test():
    print("🤖 [CLI Test Mode] Hệ thống bóc tách dữ liệu AI (Giả lập Discord Bot)")
    print("Nhập thông báo thô (Gõ 'exit' để thoát):")
    
    while True:
        try:
            raw_text = input("\n> ")
            if raw_text.strip().lower() in ['exit', 'quit']:
                break
            if not raw_text.strip():
                continue
                
            print("⏳ Đang phân tích...")
            extracted = extract_deadline_gemini(raw_text, api_key=None)
            
            is_valid = extracted.get("is_deadline") or extracted.get("is_relevant_announcement") or extracted.get("is_course_resource")
            
            if not is_valid:
                print(f"🙈 [BỎ QUA TIN RÁC]: Hệ thống nhận diện đây là tin nhắn trò chuyện bình thường.")
                continue
                
            print("✅ Đã nhận diện thành công. Đang lưu vào PostgreSQL...")
            result = add_extracted_item(extracted, source="CLI_Test")
            
            if result.get("is_duplicate"):
                print("⚠️ Cảnh báo: Thông báo này đã bị trùng lặp trong Database!")
            else:
                print("💾 Đã lưu thành công vào PostgreSQL. Bạn có thể F5 trang Web để xem kết quả!")
                print(f"   Tóm tắt: {extracted.get('title')} ({extracted.get('course')})")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Lỗi: {e}")

if __name__ == "__main__":
    run_test()
