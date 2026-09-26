# 🧭 Hành trình phát triển (Development Journey)

Thư mục này lưu lại **toàn bộ quá trình xây dựng AI Research Agent từ con số 0**, đi từng bước một, không dùng template có sẵn. Mỗi file giải quyết đúng 1 vấn đề cụ thể, tận dụng lại những gì đã học ở bước trước — thay vì "prompt AI viết hộ rồi copy", đây là quá trình hiểu rõ từng cơ chế trước khi ráp thành sản phẩm hoàn chỉnh ở `app.py`.

## Tổng quan các giai đoạn

| # | File | Mục tiêu | Khái niệm chính học được |
|---|---|---|---|
| 01 | `01_goi_api_dau_tien.py` | Gọi LLM API lần đầu tiên | Cơ chế request/response; LLM sinh câu trả lời theo xác suất (autoregressive), không tra cứu dữ liệu thật |
| 02 | `02_prompt_engineering.py` | Điều khiển cách model trả lời | System Prompt vs User Prompt; Temperature (độ ngẫu nhiên khi sinh token) |
| 03 | `03_function_calling.py` | Cho LLM khả năng "hành động" thật | Cơ chế Function Calling — model chỉ **đề xuất** gọi hàm, code mới là bên **thực thi** hành động thật |
| 04 | `04_web_search.py` | Tích hợp tìm kiếm web thật | Áp dụng Function Calling vào 1 tool hữu ích, khắc phục giới hạn "không tra cứu được" của LLM |
| 05 | `05_react_loop.py` | Agent tự quyết định số bước cần thiết | ReAct pattern (Reasoning + Acting) — vòng lặp đa bước thay vì gọi tool cố định 1 lần |
| 06 | `06_planning.py` | Xử lý chủ đề nghiên cứu rộng, mơ hồ | Task decomposition (chia nhỏ nhiệm vụ); ép định dạng output bằng `response_schema` |
| 07 | `07_synthesize_report.py` | Tổng hợp báo cáo hoàn chỉnh có trích dẫn | Kết hợp LLM (viết văn liền mạch) với code thường (regex trích xuất URL — ưu tiên độ chính xác tuyệt đối cho phần không được phép sai) |
| 08 | `08_langchain_refactor.py` | Chuẩn hóa bằng framework công nghiệp | LangChain `create_agent` — đóng gói lại đúng cơ chế đã tự tay xây ở bước 03-05, giúp code gọn và chuẩn hóa |

## Cách chạy thử từng bước

```bash
# Từ thư mục gốc của project
source venv/Scripts/activate      # Windows Git Bash
export GEMINI_API_KEY="your-api-key"

python development-journey/01_goi_api_dau_tien.py
python development-journey/02_prompt_engineering.py
# ... tương tự cho các file còn lại
```

## Vì sao đi theo lộ trình này

Thay vì học lý thuyết Function Calling/Agent rồi mới code, cách tiếp cận ở đây là **xây dần từng mảnh nhỏ, hiểu rõ mảnh đó trước khi ráp thêm mảnh tiếp theo**:

- File 03 dạy cơ chế Function Calling với 2 tool đơn giản (đồng hồ, máy tính) — tách biệt hoàn toàn khỏi độ phức tạp của việc search web thật
- File 05 chỉ thay đổi ĐÚNG 1 điểm so với file 04: biến 2 lượt gọi cố định thành 1 vòng lặp linh hoạt — dễ thấy rõ điều gì thực sự thay đổi
- File 08 là bước "gặt hái": sau khi đã hiểu rõ cơ chế thủ công, mới chuyển sang dùng framework — tránh việc dùng công cụ như "hộp đen" mà không biết bên trong đang làm gì

Kết quả cuối cùng — `app.py` ở thư mục gốc — kế thừa toàn bộ logic đã xây dựng và kiểm chứng qua 8 bước trên, chỉ thêm giao diện Streamlit để người dùng cuối sử dụng được.
