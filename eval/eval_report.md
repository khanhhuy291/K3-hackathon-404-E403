# Báo Cáo Đánh Giá Chất Lượng AI (AI Evaluation Report) — R4 Rubric

- **Tổng số Test Cases:** 20 (Golden Set: `eval/golden_set.json`)
- **Pass Rate:** **90.0%** (Quality Bar: **≥ 85.0%** — ✅ ĐẠT CHUẨN (PASS QUALITY BAR))
- **Hallucination Rate (Ảo giác AI):** **0.0%**
- **Out of Scope Filtering Accuracy:** **100.0%**

---

## Chi tiết Kết quả 20 Test Cases

| Case # | Phân loại | Mô tả | Kỳ vọng | AI Thực tế | Trạng thái |
|---|---|---|---|---|---|
| #01 | Regular | Thông báo bài tập rõ tên môn, ngày giờ | 2026-08-15 23:59 | 2026-08-15 23:59 | ✅ PASS |
| #02 | Regular | Email Outlook thông báo quiz online | 2026-08-10 22:00 | 2026-08-10 22:00 | ✅ PASS |
| #03 | Regular | Thông báo thi cuối kỳ | 2026-08-25 14:00 | Deadline | ❌ FAIL |
| #04 | Regular | Deadline bài tập nhóm | 2026-08-12 18:00 | 2026-08-12 18:00 | ✅ PASS |
| #05 | Regular | Thông báo nộp bài thu hoạch | 2026-07-31 23:59 | 2026-07-31 23:59 | ✅ PASS |
| #06 | Regular | Thông báo đăng ký đề tài | 2026-09-05 17:00 | 2026-09-05 17:00 | ✅ PASS |
| #07 | Regular | Thông báo nộp bổ sung học phí/hồ sơ | 2026-08-18 11:30 | 2026-08-18 11:30 | ✅ PASS |
| #08 | Regular | Nhắc nộp khảo sát môn học | 2026-08-14 20:00 | 2026-08-14 20:00 | ✅ PASS |
| #09 | Regular | Lịch nộp code đồ án | 2026-08-20 23:59 | 2026-08-21 06:59 | ✅ PASS |
| #10 | Regular | Thông báo đọc trước tài liệu | 2026-08-08 08:00 | 2026-08-08 08:00 | ✅ PASS |
| #11 | Layer1_Hallucination | Email thông báo tin tức nghỉ học, KHÔNG có deadline | No DL | No DL | ✅ PASS |
| #12 | Layer1_Hallucination | Tin nhắn sinh viên chém gió trên Discord | No DL | No DL | ✅ PASS |
| #13 | Layer2_Ambiguous | Tin nhắn có deadline nhưng thiếu ngày cụ thể (tối nay) | Deadline | 2026-07-31 18:00 | ✅ PASS |
| #14 | Layer2_Ambiguous | Tin nhắn hạn chót 12h (không rõ AM hay PM) | 2026-08-16 12:00 | 2026-08-16 12:00 | ✅ PASS |
| #15 | Layer3_OutOfScope | Sinh viên yêu cầu xin gia hạn nộp bài | No DL | No DL | ✅ PASS |
| #16 | Layer3_OutOfScope | Yêu cầu giải bài tập hộ | No DL | No DL | ✅ PASS |
| #17 | Layer4_Domain | Lệch múi giờ UTC | 2026-08-17 06:59 | 2026-08-17 06:59 | ✅ PASS |
| #18 | Layer4_Domain | Tên môn viết tắt + 2 lớp có deadline khác nhau | 2026-08-10 17:00 | Deadline | ❌ FAIL |
| #19 | Layer4_Domain | Thông báo thay đổi phòng học & nộp lại bài | 2026-08-05 09:00 | 2026-08-05 09:00 | ✅ PASS |
| #20 | Layer4_Domain | Tin nhắn trích dẫn bài đăng cũ kèm thay đổi hạn nộp | 2026-08-12 23:59 | 2026-08-13 06:59 | ✅ PASS |