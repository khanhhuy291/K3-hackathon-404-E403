# Feedback Log — Vòng User Validation (CP5)

> Mục tiêu: Thu thập phản hồi thực tế từ ít nhất 5 người ngoài nhóm dùng thử Prototype. 

---

## Danh sách người tham gia thử nghiệm (Willing Users)

1. **Nguyễn Văn A** — Học viên AI-K3 (Discord user)
2. **Trần Thị B** — Học viên AI-K4 (Discord user)
3. **Lê Văn C** — Học viên AI-K3 (Discord user)
4. **Phạm Hoàng D** — Sinh viên ngoài khóa học
5. **Hoàng Thị E** — Sinh viên ngoài khóa học

---

## Log phản hồi chi tiết

### User 1: Nguyễn Văn A (SV AI-K3)
- **Nội dung dán thử:** Tin nhắn từ kênh #announcements Discord thông báo nộp Assignment 2 môn ML.
- **Kết quả AI trích xuất:** Trích đúng Ngày 15/08, Giờ 23:59, Tên môn Machine Learning.
- **Trích dẫn nguyên văn phản hồi:** *"Nhìn cái card hiển thị nguyên văn đoạn chat làm mình yên tâm hơn hẳn, không sợ AI bịa sai ngày. Tuy nhiên nên thêm nút copy nhanh vào Google Calendar."*
- **Hành động từ nhóm:** Đã cập nhật giao diện bổ sung nút "Export .ics / Add to Calendar".

---

### User 2: Trần Thị B (SV AI-K4)
- **Nội dung dán thử:** Email Outlook thông báo mở Quiz trắc nghiệm online.
- **Kết quả AI trích xuất:** Trích đúng 22:00 ngày 10/08, hiển thị badge màu vàng cảnh báo `[Cần xác nhận giờ làm bài]`.
- **Trích dẫn nguyên văn phản hồi:** *"Thẻ cảnh báo màu vàng khá rõ, biết ngay là tin này cần chú ý lại giờ giấc. Rất hữu ích."*
- **Hành động từ nhóm:** Giữ nguyên thiết kế thẻ cảnh báo (Áp dụng PAIR Error handling).

---

### User 3: Lê Văn C (SV AI-K3)
- **Nội dung dán thử:** Tin nhắn thảo luận bài tập chung trên kênh Discord (Không chứa deadline).
- **Kết quả AI trích xuất:** AI báo *"Không tìm thấy deadline trong nội dung này"*, không tạo task giả.
- **Trích dẫn nguyên văn phản hồi:** *"Nhiều app khác cứ bắt tạo task bậy bạ, cái này từ chối đúng làm mình thích nè."*
- **Hành động từ nhóm:** Xác nhận chiều chống bịa tin (Hallucination resistance) hoạt động chuẩn.

---

### User 4: Phạm Hoàng D (Sinh viên ngoài)
- **Nội dung dán thử:** Tin nhắn có múi giờ UTC (`23:59 Sunday UTC`).
- **Kết quả AI trích xuất:** Tự đổi sang 06:59 sáng thứ Hai (UTC+7) kèm nhãn `[Đã quy đổi từ UTC]`.
- **Trích dẫn nguyên văn phản hồi:** *"Cái này cứu mình luôn, lần trước mình bị lầm múi giờ bài thi Coursera rớt môn lãng xẹt."*
- **Hành động từ nhóm:** Ghi nhận impact thực tế của lớp chỗ khó ④.

---

### User 5: Hoàng Thị E (Sinh viên ngoài)
- **Nội dung dán thử:** Dán câu hỏi xin gia hạn bài tập.
- **Kết quả AI trích xuất:** AI từ chối: *"Tôi là Trợ lý trích xuất deadline, không thể xử lý yêu cầu gia hạn."*
- **Trích dẫn nguyên văn phản hồi:** *"Nó trả lời rõ ràng là nó làm được gì và không làm được gì, không bị ngáo câu hỏi."*
- **Hành động từ nhóm:** Xác nhận áp dụng thành công HAX Principle G1 & G10.

---

## Tổng kết thay đổi từ Feedback (Cập nhật vào §9 spec.md)

1. Bổ sung nút **"Add to Calendar / Export .ics"** theo góp ý của User 1.
2. Giữ nguyên các nhãn cảnh báo màu vàng và thông báo từ chối lịch sự theo phản hồi tích cực của User 2, 3, 5.
