# Bài Thu Hoạch Cá Nhân (Personal Reflection) — Hackathon AI Batch 03

- **Họ và tên:** Nguyễn Bá Khánh Huy
- **Mã học viên:** 2A202601591
- **Vai trò:** Product Owner / Spec Lead / Lead Developer
- **Nhóm:** Nhóm 03 — Zone 1 (Batch 03)
- **Tên dự án:** Trợ lý Trích xuất & Cảnh báo Deadline Tự động từ Discord (SVK3 VinAI Action)

---

## 1. Đóng góp cá nhân vào dự án

Trong suốt đợt Mini Hackathon AI Batch 03, với vai trò **Product Owner / Spec Lead / Lead Developer**, tôi đã chịu trách nhiệm chính ở các công việc sau:

1. **Định hình Sản phẩm & Viết AI Spec (`spec.md`):**
   - Định nghĩa Lát cắt giải pháp 1 câu và Job Statement chuẩn xác: *"Giúp sinh viên tự động trích xuất bài tập, deadline và tài liệu từ tin nhắn Discord rác, hiển thị dưới dạng Bảng & Lịch Tuần/Tháng để không bao giờ bị trễ hạn."*
   - Tổng hợp và phân tích dữ liệu khảo sát từ $n=20$ sinh viên để xác định đúng 3 nỗi đau lớn nhất: Trôi tin nhắn deadline, thất lạc link tài liệu và tốn thời gian chép tay thủ công.
   - Chịu trách nhiệm hoàn thiện các phần §1 đến §4 trong hồ sơ đặc tả `spec.md`.

2. **Dựng Core Backend & Tích hợp LLM API (`codebase/`):**
   - Thiết kế và phát triển REST API Server bằng Python (`codebase/python/main_api.py`) kết nối với bộ lưu trữ local JSON (`storage.json`).
   - Xây dựng Engine LLM (`llm_engine.py`) tích hợp API OpenRouter (Model `openai/gpt-4o-mini`) và Gemini API với Structured JSON Schema.
   - Phát triển thuật toán **Chống trùng lặp thông minh (Deduplication)** không phân biệt hoa thường và trích xuất URL linh hoạt an toàn tuyệt đối (`extract_url_from_text`).

3. **Điều phối Nhóm & Kiểm soát Chất lượng:**
   - Phân công nhiệm vụ rõ ràng cho 6 thành viên trong nhóm theo đúng thế mạnh.
   - Đảm bảo dự án vượt qua đầy đủ 6 cột mốc Checkpoint (CP1 đến CP6) đúng thời hạn.

---

## 2. Bài học kinh nghiệm & Chiêm nghiệm (Key Learnings)

### 2.1. Tư duy Product-First & SPEC-First
Trước đây, khi tham gia các đợt phát triển sản phẩm, tôi thường bắt tay vào viết code ngay. Tuy nhiên, qua quá trình làm bài `spec.md` tại Hackathon, tôi nhận ra rằng việc định hình rõ bài toán, xác định ranh giới (In-Scope / Out-of-Scope) và chốt Quality Bar (Pass Rate $\ge 85\%$) từ đầu giúp tiết kiệm $80\%$ thời gian chỉnh sửa và tránh lan man tính năng.

### 2.2. Làm chủ Kỹ thuật Prompt Engineering & Structured Outputs
Việc trích xuất thông tin thô từ các tin nhắn trò chuyện tự do trên Discord sang dạng JSON chuẩn đòi hỏi thiết kế System Prompt rất chặt chẽ. Tôi đã học được cách kết hợp Pydantic Schema với LLM để ép kiểu dữ liệu trả về chính xác, đồng thời kiểm soát tỷ lệ ảo giác AI (Hallucination Rate) về $0\%$.

### 2.3. Tối ưu trải nghiệm Người dùng (UX/UI)
Người dùng (sinh viên) không chỉ cần AI trích xuất đúng, mà còn cần một giao diện **trực quan và dễ thao tác**. Việc thiết kế góc nhìn kép **Bảng danh sách** và **Lịch Tuần/Tháng** cùng tính năng **Tích chọn hoàn thành (`✓ Hoàn thành`)** gạch ngang bài tập đã giúp trải nghiệm sản phẩm trở nên thực tế và gần gũi với nhu cầu hằng ngày hơn.

---

## 3. Tự đánh giá mức độ hoàn thành

| Tiêu chí | Tự đánh giá | Ghi chú |
|---|---|---|
| **Hoàn thành công việc được giao** | **100%** | Nộp đầy đủ spec.md, codebase backend, API LLM đúng hạn |
| **Tinh thần làm việc nhóm & Trách nhiệm** | **Xuất sắc** | Lắng nghe ý kiến đồng đội, hỗ trợ xử lý lỗi kỹ thuật phát sinh |
| **Kỹ năng giải quyết vấn đề (Problem Solving)** | **Tốt** | Xử lý triệt để các lỗi Regex URL, trùng lặp tin nhắn & khôi phục UI Web |

---

## 4. Lời cảm ơn

Tôi xin chân thành cảm ơn Ban tổ chức **Mini Hackathon AI — Batch 03**, các Mentors từ **VinAI** đã tận tình hướng dẫn và đưa ra những lời khuyên chuyên môn quý báu. Cảm ơn 5 thành viên trong **Nhóm 03 (Zone 1)** đã cùng nhau chiến đấu hết mình để hoàn thành sản phẩm đúng tiến độ!
