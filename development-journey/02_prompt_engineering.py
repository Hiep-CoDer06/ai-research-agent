"""
MILESTONE 2: Prompt Engineering - điều khiển cách LLM trả lời
Mục tiêu: Hiểu System Prompt, Temperature, và cách ép model trả lời đúng format
"""

import os
from google import genai
from google.genai import types

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("Chưa tìm thấy GEMINI_API_KEY.")

client = genai.Client(api_key=api_key)


def summarize_text(text: str) -> str:
    """
    Tóm tắt một đoạn văn bản dài thành 3 gạch đầu dòng ngắn gọn.
    Dùng system_instruction để "khóa" hành vi của model.
    """

    # SYSTEM PROMPT: quy tắc cố định, áp dụng cho MỌI lần gọi hàm này
    system_prompt = """Bạn là một trợ lý tóm tắt văn bản chuyên nghiệp.

QUY TẮC BẮT BUỘC:
- LUÔN trả lời bằng tiếng Việt
- LUÔN tóm tắt thành ĐÚNG 3 gạch đầu dòng
- Mỗi gạch đầu dòng không quá 20 từ
- KHÔNG thêm lời dẫn, KHÔNG thêm nhận xét cá nhân
- KHÔNG bịa thêm thông tin không có trong văn bản gốc"""

    # USER PROMPT: nội dung cụ thể của lượt gọi này
    user_prompt = f"Tóm tắt đoạn văn bản sau:\n\n{text}"

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.2,          # thấp -> ưu tiên chính xác, hạn chế "bịa"
            max_output_tokens=300,    # giới hạn độ dài output, tránh model lan man
        ),
    )
    return response.text


if __name__ == "__main__":
    van_ban_mau = """
    Trí tuệ nhân tạo tạo sinh (Generative AI) đã phát triển vượt bậc trong giai đoạn
    2023-2026, đặc biệt với sự xuất hiện của các mô hình ngôn ngữ lớn (LLM) có khả năng
    lý luận đa bước. Xu hướng Agentic AI - nơi AI không chỉ trả lời câu hỏi mà còn tự
    lên kế hoạch và thực hiện các tác vụ phức tạp bằng cách gọi các công cụ bên ngoài -
    đang trở thành kỹ năng được săn đón nhất trong ngành công nghệ. Theo báo cáo tuyển
    dụng năm 2026, kỹ năng Agentic AI có tốc độ tăng trưởng nhanh nhất trong các tin
    tuyển dụng liên quan đến AI, vượt qua cả các kỹ năng như prompt engineering truyền
    thống hay phát triển chatbot đơn thuần.
    """

    print("Đang tóm tắt...")
    ket_qua = summarize_text(van_ban_mau)

    print("\n" + "=" * 50)
    print("KẾT QUẢ TÓM TẮT:")
    print("=" * 50)
    print(ket_qua)
