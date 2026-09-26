"""
MILESTONE 1: Gọi API Gemini lần đầu tiên
Mục tiêu: Hiểu cách gửi 1 yêu cầu (request) đến LLM và nhận về kết quả (response)
"""

import os
from google import genai

# BƯỚC 1: Lấy API key từ biến môi trường (KHÔNG bao giờ viết thẳng key vào code!)
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    raise ValueError(
        "Chưa tìm thấy GEMINI_API_KEY. "
        "Hãy set biến môi trường trước khi chạy file này."
    )

# BƯỚC 2: Tạo client - đây là "cầu nối" giữa code của bạn và server của Google
client = genai.Client(api_key=api_key)


# BƯỚC 3: Hàm gửi prompt đến model và trả về câu trả lời dạng text
def ask_llm(prompt: str) -> str:
    response = client.models.generate_content(
        model="gemini-2.5-flash",  # model nằm trong free tier, tốc độ nhanh
        contents=prompt,
    )
    return response.text


# BƯỚC 4: Chạy thử
if __name__ == "__main__":
    cau_hoi = "Giải thích ngắn gọn Agentic AI là gì, bằng tiếng Việt, trong 3 câu."

    print("Đang gửi câu hỏi đến Gemini...")
    tra_loi = ask_llm(cau_hoi)

    print("\n" + "=" * 50)
    print("Câu hỏi:", cau_hoi)
    print("-" * 50)
    print("Trả lời từ Gemini:")
    print(tra_loi)
    print("=" * 50)
