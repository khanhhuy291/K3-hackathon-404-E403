# Mini Hackathon AI | Zone 5 - Nhóm 403

## Dự án: Trợ lý Trích xuất & Cảnh báo Deadline Tự động từ Discord & Outlook

> **SPEC → Prototype → Demo.** Nền tảng trợ lý thông minh giúp sinh viên tự động trích xuất, phân loại và cảnh báo deadline bài tập, lịch học từ các thông báo thô trên kênh Discord và Email Outlook.

---

## Thành viên & Phân công công việc

| Mã Học Viên | Họ và Tên | Vai trò | Phân công cụ thể |
|---|---|---|---|
| **2A202601591** | **Nguyễn Bá Khánh Huy** | Product Owner / Spec Lead / Dev | Trưởng nhóm, viết `spec.md`, tổng hợp dữ liệu khảo sát ($n=20$), phụ trách các phần §1–§4, Dựng backend trong codebase/, tích hợp API LLM  |
| **2A202601549** | **Phạm Tiến Anh** | AI / Prompt Engineer Lead | Thiết kế & tối ưu System Prompt, xây dựng dataset `eval/golden_set.json`, chạy Eval R4 |
| **2A202601819** | **Ngô Quang Dũng** | Fullstack Developer (Backend) | Dựng backend trong `codebase/`, tích hợp API LLM, xử lý luồng trích xuất dữ liệu |
| **2A202601499** | **Đỗ Đức Trường** | Fullstack Developer (Frontend/UI) | Dựng UI/UX Web Prototype trong `codebase/`, xử lý luồng giao diện R5 |
| **2A202601987** | **Phạm Tuấn Việt** | User Researcher & Validation | Thu thập feedback log `validation/` ($\ge 5$ mẩu), tổng hợp dữ liệu đo lường chất lượng R6 |
| **2A202601894** | **Đinh Xuân Huy** | QA & Presentation Lead | Thiết kế slide `demo-slides.pdf`, kiểm thử chất lượng sản phẩm (QA), phụ trách Demo CP6 |

---

## Cấu trúc Repository

```text
Batch03-K3-AI-Product-Hackathon/
├── README.md         ← Thành viên (mã HV + tên) + phân công có tên từng phần
├── spec.md            ← AI Spec hoàn thiện theo 03-template-ai-spec.md
├── demo-slides.pdf    ← Slide 6 trang trình bày tại CP6
├── codebase/          ← Prototype Web (Working prototype với lời gọi AI thật)
├── eval/              ← Golden set 20 cases + bảng kết quả các lượt đo
├── validation/        ← Feedback log từ vòng user test (≥5 mẩu)
└── reflection/        ← Bài thu hoạch cá nhân của từng thành viên

