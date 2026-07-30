# Mini Hackathon AI — Batch 03 | Zone 1 - Nhóm 03

## Dự án: Trợ lý Trích xuất & Cảnh báo Deadline Tự động từ Discord & Outlook

> **SPEC → Prototype → Demo.** Nền tảng trợ lý thông minh giúp sinh viên tự động trích xuất, phân loại và cảnh báo deadline bài tập, lịch học từ các thông báo thô trên kênh Discord và Email Outlook.

### Thành viên & Phân công công việc

| Mã Học Viên | Họ và Tên | Vai trò | Phân công cụ thể |
|---|---|---|---|
| 2A202601591 | Nguyễn Bá Khánh Huy | Product Owner / Spec Lead | Viết `spec.md`, khảo sát bằng chứng $n=22$, chịu trách nhiệm phần §1-§4 |
| HV002 | Thành viên 2 | AI / Prompt Engineer | Tối ưu System Prompt, xây dựng bộ `eval/golden_set.json`, chạy Eval R4 |
| HV003 | Thành viên 3 | Fullstack Developer | Dựng Web Prototype trong `codebase/`, kết nối API LLM, xử lý UI/UX R5 |
| HV004 | Thành viên 4 | User Researcher & QA | Thu thập feedback log `validation/`, làm slide demo `demo-slides.pdf`, R6 |

---

## Cấu trúc Repository

```text
Batch03-K3-AI-Product-Hackathon/
├── README.md          ← Thành viên (mã HV + tên) + phân công có tên từng phần
├── spec.md            ← AI Spec hoàn thiện theo 03-template-ai-spec.md
├── demo-slides.pdf    ← Slide 6 trang trình bày tại CP6
├── codebase/          ← Prototype Web (Working prototype với lời gọi AI thật)
├── eval/              ← Golden set 20 cases + bảng kết quả các lượt đo
├── validation/        ← Feedback log từ vòng user test (≥5 mẩu)
└── reflection/        ← Bài thu hoạch cá nhân của từng thành viên
```

---

## Lịch 6 Checkpoints & Tiến độ

- [x] **CP1 · Canvas (10:00 N1):** Đã thông qua Lát cắt 1 câu, Job statement & bằng chứng ban đầu.
- [ ] **CP2 · Bấm được (12:00 N1):** Dựng khung UI Web bấm thông luồng.
- [ ] **CP3 · AI thật + đo lượt 1 (16:00 N1):** Gọi API AI thật + Đo lường lượt 1 trên 20 test cases.
- [ ] **CP4 · Spec nộp 23:59 N1:** Finalize file `spec.md` & chốt cứng Quality Bar ($85\%$).
- [ ] **CP5 · Validation & Dry run (09:00 N2):** Thu thập $\ge 5$ feedback log + Chạy thử trình bày.
- [ ] **CP6 · Demo (10:00 N2):** Trình bày 5 phút + Q&A.
