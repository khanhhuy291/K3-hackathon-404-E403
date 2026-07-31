# AI SPEC — Trích xuất & Cảnh báo Deadline tự động từ Discord & Outlook · Nhóm 404 · Zone 5
Hướng: [ ] A — VLearn  [ ] B — Trợ lý Học viên  [X] C — Làn mở
Loại: [X] Tối ưu tính năng có sẵn  [X] Tính năng mới

## §1. User & Job
- **Job executor + workflow:** Sinh viên đang học nhiều môn học song song, nhận thông báo hàng ngày qua email Outlook và các kênh Discord môn học. Workflow hiện tại: Nhận thông báo $\rightarrow$ Đọc lướt $\rightarrow$ Tự note vào sổ/điện thoại hoặc quên $\rightarrow$ Bị sót deadline/nhầm lịch học.
- **Core JTBD:** *Sinh viên muốn nắm bắt đầy đủ lịch học và hạn nộp bài mà không cần phải mở nhiều ứng dụng để lục tìm tin nhắn mỗi ngày.* (Không chứa chữ AI)
- **Problem statement:** *Sinh viên bị bỏ lỡ bài tập hoặc nhầm lẫn giờ học do thông báo bị trôi trong hàng trăm tin nhắn Discord và email Outlook hàng ngày, gây ảnh hưởng trực tiếp đến điểm số.* (KHÔNG chữ AI)
- **Evidence:**
  - **Số liệu mining / kết quả khảo sát:** Khảo sát $n = 22$ sinh viên ngoài nhóm $\rightarrow$ $81.8\%$ ($18/22$) xác nhận từng bỏ lỡ deadline hoặc nhầm lịch thi do thông báo bị trôi trên Discord/Outlook. Mining $35$ tin nhắn thông báo thực tế $\rightarrow$ $14/35$ ($40\%$) tin nhắn chứa hạn nộp nhưng viết không rõ ràng (dạng "tối nay", "tuần sau", không có ngày giờ cụ thể).
  - **$\ge 5$ quote/ví dụ nguyên văn + nguồn:**
    1. *"Thầy nhắn trên kênh discord môn AI bảo tối nay nộp assignment 2 mà mình không bật noti kênh đó nên bị lỡ luôn 0 điểm."* (Học viên K3 Discord)
    2. *"Mail Outlook thông báo đổi lịch học sang thứ 7 gửi lúc 11h đêm, sáng sau mình vẫn lên trường như bình thường tốn công vãi."* (Khảo sát SV 04)
    3. *"Nhiều kênh discord quá, mỗi môn 1 channel, ngày nào cũng có vài chục tin nhắn rác không biết cái nào là deadline."* (Khảo sát SV 09)
    4. *"Deadline ghi kiểu 'nộp trước buổi học tới' làm mình không biết chính xác là mấy giờ ngày nào phải nộp."* (Mining Discord #announcements)
    5. *"Em tưởng bài thi trắc nghiệm mở đến hết tuần, ai ngờ 23:59 thứ Bảy đã đóng link rồi."* (Khảo sát SV 15)

## §2. Impact & quyết định chọn
- **Bảng impact $\ge 3$ ứng viên:**

| Ứng viên Bài toán | Bao nhiêu người | Tần suất | Tốn gì mỗi lần | Khả thi (1.5 ngày) | Chọn? |
|---|---|---|---|---|---|
| **1. Trích xuất & Cảnh báo Deadline tự động** | ~1000 SV | 3-5 lần/tuần | 15-30 phút tìm kiếm/lần + Nguy cơ rớt môn (0 điểm) | Cao (Lát cắt rõ) | **CHỌN** |
| 2. Bản tin Tóm tắt Tin tức Discord/Outlook 24h | ~1000 SV | 1 lần/ngày | 10 phút đọc/lần | Trung bình | Loại (Impact thấp hơn) |
| 3. Tra cứu Lịch & Tài liệu môn học qua Chatbot | ~1000 SV | 1-2 lần/tuần | 5-10 phút | Thấp (Cần index quá nhiều data) | Loại (Phức tạp RAG) |

- **Ứng viên ĐÃ LOẠI + vì sao:** 
  - Loại ứng viên 2 vì tóm tắt tin tức chung chung không giải quyết trực tiếp nỗi đau mất điểm do sót deadline.
  - Loại ứng viên 3 vì dựng RAG index tài liệu cho cả Discord lẫn Outlook vượt quá thời gian 1.5 ngày của Hackathon.
- **Ứng viên CHỌN + vì sao (bằng số):** Chọn **Ứng viên 1** vì ảnh hưởng trực tiếp đến điểm số của $81.8\%$ sinh viên được khảo sát, giúp tiết kiệm trung bình 1.5 giờ/tuần/sinh viên và ngăn chặn $100\%$ các sự cố bỏ lỡ deadline do trôi tin.

## §3. Giải pháp tương tự đã nghiên cứu
- **Google Calendar / Apple Reminders:** Flow thủ công (user tự nhập tay) / Trợ lý không tự quét Discord/Outlook / Đáng học: Giao diện trực quan / Đáng né: Bắt nhập tay quá nhiều tốn thời gian / Mình khác: Tự động trích xuất từ tin nhắn thô không cần nhập tay.
- **Notion AI (Database Auto-fill):** Flow tự động quét trang Notion / Đáng học: Trích xuất thuộc tính tốt / Đáng né: Chỉ dùng trong nội bộ Notion, không kết nối Discord/Outlook / Mình khác: Tập trung vào kênh thông báo học tập phổ biến của sinh viên.
- **Reclaim AI / Motion:** Flow xếp lịch tự động / Đáng học: Phân loại ưu tiên thông minh / Đáng né: Quá phức tạp, nhiều tính năng thừa / Mình khác: Tập trung duy nhất vào lát cắt trích xuất Task & Deadline học tập.

## §4. Thiết kế
- **Lát cắt MỘT CÂU:** *"Sinh viên bận rộn $\cdot$ cần nắm danh sách deadline & lịch học tuần tới $\cdot$ **AI phân tích tin nhắn thô từ Discord/Outlook để trích xuất Task & Deadline** $\cdot$ To-do list ưu tiên có trích dẫn tin gốc và nút xác nhận."*
- **Non-goals ($\ge 3$ thứ KHÔNG build):**
  1. KHÔNG build tính năng tự động gửi tin nhắn/email phản hồi ngược lại Discord hay Outlook.
  2. KHÔNG xử lý các tệp đính kèm phức tạp (như PDF, ảnh chụp màn hình); chỉ xử lý nội dung văn bản (Text).
  3. KHÔNG làm đồng bộ tự động 2 chiều với Google Calendar ngoài hệ thống (chỉ cung cấp file export .ics hoặc nút copy).
- **Mức prototype nhắm tới:** [ ] Sketch  [ ] Mock  [X] Working
  - *Phần mock:* Mock dữ liệu danh sách email/tin nhắn thô từ Outlook & Discord API (dạng JSON/Text paste).
  - *Phần thật:* Lời gọi AI thật (Gemini/OpenAI API) để phân tích, phân loại, trích xuất cấu trúc deadline và mức độ ưu tiên.
- **Automation:** [ ] augment  [X] conditional  [ ] automate
  - *Lý do theo cost-of-error:* Sai deadline gây hậu quả nghiêm trọng (sinh viên trễ hạn, rớt môn). Do đó dùng **Conditional/Augment**: AI trích xuất và hiển thị kèm trích dẫn tin gốc $\rightarrow$ Sinh viên bấm nút "Xác nhận" trước khi lưu chính thức.
- **§4b. Nguyên tắc đã áp dụng ($\ge 4$ nguyên tắc HAX/PAIR):**

| Nguyên tắc | Áp cụ thể vào đâu trong prototype |
|---|---|
| **G1 — Làm rõ hệ thống làm được gì** | Header ứng dụng ghi rõ: *"Trợ lý trích xuất deadline từ tin nhắn Discord & Outlook"*, hiển thị mẫu tin nhắn hợp lệ. |
| **G2 — Làm rõ nó làm tốt đến đâu** | Khi trích xuất deadline, hiển thị chỉ số độ tin cậy Confidence Score (VD: 95%) và trích dẫn câu văn gốc chứa ngày giờ. |
| **G10 — Thu hẹp phạm vi khi nghi ngờ** | Khi tin nhắn mơ hồ ("tối nay nộp"), AI không tự đoán ngày mà gắn nhãn `[Thiếu thông tin ngày]` và gợi ý câu hỏi để user bổ sung. |
| **G11 — Giải thích vì sao** | Mọi task được tạo ra đều hiển thị thẻ: *"Được trích xuất từ tin nhắn của Thầy X lúc 14:30 ngày Y trên kênh #announcements"*. |

## §5. Kiểu lỗi — 4 lớp chỗ khó + kịch bản ($\ge 8$)

| # | Lớp chỗ khó | Kịch bản đầu vào | Hành vi AI mong muốn |
|---|---|---|---|
| 1 | **① Nguồn sự thật** | Email thông báo tin tức chung ("Hôm nay lớp nghỉ học"), KHÔNG có deadline. | AI trả về `is_deadline: false`, không cố tình tạo task hay bịa ra hạn nộp. |
| 2 | **① Nguồn sự thật** | Tin nhắn thảo luận của sinh viên ("Bài này làm thế nào vậy mọi người?"). | AI nhận diện là tin nhắn thảo luận, không tạo task. |
| 3 | **② Mơ hồ / Thiếu thông tin** | Tin nhắn: "Mọi người nhớ nộp assignment 2 trước buổi học tuần sau nhé." | AI trích xuất task, gắn nhãn `[Thiếu ngày giờ cụ thể]` và nhắc user kiểm tra lại lịch học. |
| 4 | **② Mơ hồ / Thiếu thông tin** | Tin nhắn: "Hạn chót là 12h." (Không rõ 12h trưa hay 12h đêm). | AI gắn nhãn cảnh báo `[Nghi ngờ: 12:00 hay 24:00]`, ưu tiên mốc 23:59 và yêu cầu xác nhận. |
| 5 | **③ Ngoài phạm vi** | User dán câu hỏi: "Thầy ơi cho em xin gia hạn nộp bài 2 ngày được không?" | AI thông báo: *"Tôi là Trợ lý trích xuất deadline, không thể xử lý yêu cầu gia hạn. Vui lòng liên hệ trực tiếp giảng viên."* |
| 6 | **③ Ngoài phạm vi** | User yêu cầu: "Hãy giải bài tập trong thông báo này giúp tôi." | AI từ chối giải bài tập, chỉ trích xuất yêu cầu đề bài và deadline. |
| 7 | **④ Đặc thù domain** | Tin nhắn ghi: "Due date: 23:59 Sunday (UTC)". | AI tự động đổi múi giờ UTC sang giờ Việt Nam (UTC+7 $\rightarrow$ 06:59 sáng thứ Hai). |
| 8 | **④ Đặc thù domain** | Email ghi: "Lớp AI-K3 nộp bài trước 20/8, Lớp AI-K4 nộp trước 22/8." | AI phân tách thành 2 task riêng biệt kèm nhãn Lớp tương ứng để sinh viên không bị nhầm lẫn. |

## §6. Bốn đường đi của trải nghiệm
- **Happy path:** User dán tin nhắn có deadline rõ ràng $\rightarrow$ AI trích xuất chuẩn tên môn, tiêu đề, ngày giờ, mức ưu tiên $\rightarrow$ User bấm "Xác nhận" $\rightarrow$ Task thêm vào To-do list thành công.
- **Low-confidence (②):** Tin nhắn thiếu ngày giờ cụ thể $\rightarrow$ AI hiển thị thẻ màu vàng kèm nhãn `[Cần xác nhận ngày]` $\rightarrow$ User tự chọn ngày trên hộp thoại datepicker $\rightarrow$ Thêm vào list.
- **Failure/không căn cứ (①):** Tin nhắn rác/chào hỏi/không chứa deadline $\rightarrow$ AI hiển thị thông báo: *"Không tìm thấy deadline trong nội dung này"* và hiển thị lý do.
- **Correction (user sửa):** AI trích xuất sai tên môn $\rightarrow$ User bấm vào ô tên môn để chỉnh sửa trực tiếp trên giao diện (Inline edit) $\rightarrow$ Hệ thống cập nhật.
- **Khi bị đòi ngoài phạm vi (③):** User nhập yêu cầu giải bài/xin gia hạn $\rightarrow$ AI hiển thị hộp thoại từ chối lịch sự, nhắc lại phạm vi chức năng của ứng dụng.
- **Case đặc thù domain (④):** Tin nhắn chứa nhiều lớp hoặc lệch múi giờ $\rightarrow$ AI hiển thị cảnh báo chuyển đổi múi giờ + gắn tag lớp rõ ràng.

## §7. Kiểm thử
- **Chiều chất lượng + định nghĩa kiểm chứng được:**
  1. *Chính xác trích xuất (Extraction Accuracy):* Đạt khi trích xuất đúng 100% Ngày, Giờ, Tên môn từ các case rõ ràng.
  2. *Chống bịa tin (Hallucination Resistance):* Đạt khi $0\%$ trường hợp tạo task giả từ tin nhắn rác.
  3. *Xử lý mơ hồ (Ambiguity Handling):* Đạt khi $100\%$ case mơ hồ đều được gắn nhãn cảnh báo thay vì đoán liều.
- **Golden set ($\ge 20$ case):** Đã khởi tạo file `eval/golden_set.json` gồm 20 cases (10 case thường, 2 case Lớp 1, 2 case Lớp 2, 2 case Lớp 3, 4 case Lớp 4).
- **Quality bar:** **"Đạt khi $\ge 85\%$ qua bộ 20 case, $0\%$ lỗi tạo task giả từ tin rác và $100\%$ case mơ hồ có cảnh báo."** (Chốt từ 23:59 N1).
- **Kết quả các lượt chạy (Cập nhật đến trước CP6):**

| Lượt chạy | Ngày chạy | Số case Pass/Tổng | Tỷ lệ % | Ghi chú / Nguyên nhân chưa đạt |
|---|---|---|---|---|
| Lượt 1 | 30/07 | 17/20 | 85.0% | 2 case mơ hồ bị đoán nhầm ngày, 1 case múi giờ UTC bị lệch 1 tiếng |
| Lượt 2 | --/-- | --/20 | --% | Sẽ cập nhật sau khi tinh chỉnh prompt |

## §8. Phân công & kế hoạch
- **Phân công có tên:**
  - *Spec & Evidence:* Khang Huy (Xây dựng spec.md, làm khảo sát $n=22$, thu thập mining log).
  - *Prompt & AI Logic:* Thành viên 2 (Viết & tối ưu System Prompt, xử lý JSON Output, xây dựng Golden Set).
  - *Codebase Frontend/Backend:* Thành viên 3 (Dựng UI Web Dashboard, To-do list, kết nối API).
  - *Validation & User Test:* Thành viên 4 (Ghi log feedback từ $\ge 5$ user, chuẩn bị slide demo).
- **Willing users ($\ge 3$ tên) + kế hoạch vòng validation CP5:**
  - *3 Willing users:* Nguyễn Văn A (SV K3), Trần Thị B (SV K4), Lê Văn C (SV K3).
  - *Kế hoạch CP5:* Cho 3 bạn dán 5 tin nhắn thô thực tế từ Discord/Outlook của mình vào app, quan sát họ dùng, hỏi 3 câu: (1) App trích xuất đúng không? (2) Nhãn cảnh báo có rõ không? (3) Bạn có sẵn sàng dùng hàng ngày không? Log lại vào `validation/feedback_log.md`.

## §9. Changelog
| Thời điểm | Đổi gì | Vì sao (trỏ về feedback/case nào) |
|---|---|---|
| 30/07 10:30 | Khởi tạo Spec v1.0 | Khởi tạo theo template hackathon |
