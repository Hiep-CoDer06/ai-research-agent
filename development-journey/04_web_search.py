"""
MILESTONE 4: Tích hợp Web Search thật
Mục tiêu: Cho agent "giác quan" thật để tự tìm thông tin trên internet
Cấu trúc y hệt M3 (thực đơn -> gửi câu hỏi -> đọc phiếu order -> chạy hàm thật -> trả kết quả)
chỉ khác: "cái bếp" bây giờ là 1 công cụ tìm kiếm web thật.
"""

import os
from google import genai
from google.genai import types
from ddgs import DDGS

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("Chưa tìm thấy GEMINI_API_KEY.")

client = genai.Client(api_key=api_key)


# ============================================================
# BƯỚC 1: "Cái bếp mới" - hàm tìm kiếm web THẬT
# ============================================================

def search_web(query: str) -> str:
    """Tìm kiếm thông tin trên internet, trả về danh sách kết quả dạng text."""
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=5))

    if not results:
        return "Không tìm thấy kết quả nào."

    # Gộp các kết quả thành 1 đoạn text để model "đọc" được
    formatted = []
    for i, r in enumerate(results, 1):
        formatted.append(f"[{i}] {r['title']}\n{r['body']}\nNguồn: {r['href']}")
    return "\n\n".join(formatted)


AVAILABLE_TOOLS = {"search_web": search_web}


# ============================================================
# BƯỚC 2: "Thực đơn" mô tả tool cho model
# ============================================================

search_tool = types.FunctionDeclaration(
    name="search_web",
    description=(
        "Tìm kiếm thông tin mới nhất trên internet. "
        "Dùng khi câu hỏi cần thông tin cập nhật, sự kiện gần đây, "
        "hoặc bất kỳ điều gì bạn không chắc chắn / có thể đã lỗi thời."
    ),
    parameters=types.Schema(
        type="OBJECT",
        properties={
            "query": types.Schema(
                type="STRING",
                description="Từ khóa tìm kiếm, ngắn gọn và cụ thể",
            ),
        },
        required=["query"],
    ),
)

tools = types.Tool(function_declarations=[search_tool])


# ============================================================
# BƯỚC 3-6: Vòng lặp agent - y hệt cấu trúc M3, chỉ đổi tool
# ============================================================

def ask_research_agent(question: str) -> str:
    print(f"\n>>> Câu hỏi: {question}")

    # Lượt 1: gửi câu hỏi kèm thực đơn
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=question,
        config=types.GenerateContentConfig(tools=[tools]),
    )

    if not response.function_calls:
        print("(Model tự trả lời được, không cần search)")
        return response.text

    # Đọc phiếu order
    call = response.function_calls[0]
    func_name = call.name
    func_args = dict(call.args)
    print(f"(Model quyết định search: {func_args['query']!r})")

    # Tra sổ tay, chạy hàm thật - lần này là search thật trên internet
    result = AVAILABLE_TOOLS[func_name](**func_args)
    print("(Đã lấy kết quả thật từ internet)")

    # Lượt 2: mang kết quả quay lại cho model viết câu trả lời cuối cùng
    follow_up = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Content(role="user", parts=[types.Part(text=question)]),
            response.candidates[0].content,
            types.Content(
                role="user",
                parts=[types.Part.from_function_response(
                    name=func_name,
                    response={"result": result},
                )],
            ),
        ],
        config=types.GenerateContentConfig(tools=[tools]),
    )
    return follow_up.text


if __name__ == "__main__":
    # Câu hỏi này CẦN search vì đòi hỏi thông tin cập nhật
    print(ask_research_agent(
        "Xu hướng kỹ năng AI nào đang được tuyển dụng nhiều nhất hiện tại?"
    ))

    # Câu hỏi này KHÔNG cần search - model tự trả lời được
    print(ask_research_agent("2 cộng 2 bằng mấy?"))
