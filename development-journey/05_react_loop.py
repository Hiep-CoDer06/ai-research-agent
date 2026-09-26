"""
MILESTONE 5: Vòng lặp Agent (ReAct - Reasoning + Acting)
Mục tiêu: Agent tự quyết định search bao nhiêu lần là đủ, thay vì chỉ 1 lần cố định.
Chu trình: Suy nghĩ -> Hành động (gọi tool) -> Quan sát (nhận kết quả) -> lặp lại
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
# Tool: search_web (giống hệt M4)
# ============================================================

def search_web(query: str) -> str:
    """Tìm kiếm thông tin trên internet, trả về danh sách kết quả dạng text."""
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=5))
    if not results:
        return "Không tìm thấy kết quả nào."
    formatted = []
    for i, r in enumerate(results, 1):
        formatted.append(f"[{i}] {r['title']}\n{r['body']}\nNguồn: {r['href']}")
    return "\n\n".join(formatted)


AVAILABLE_TOOLS = {"search_web": search_web}

search_tool = types.FunctionDeclaration(
    name="search_web",
    description=(
        "Tìm kiếm thông tin mới nhất trên internet. "
        "Dùng khi câu hỏi cần thông tin cập nhật hoặc bạn chưa chắc chắn. "
        "Có thể gọi NHIỀU LẦN với các từ khóa khác nhau nếu câu hỏi có nhiều khía cạnh."
    ),
    parameters=types.Schema(
        type="OBJECT",
        properties={
            "query": types.Schema(type="STRING", description="Từ khóa tìm kiếm"),
        },
        required=["query"],
    ),
)
tools = types.Tool(function_declarations=[search_tool])


# ============================================================
# VÒNG LẶP REACT - trái tim của milestone này
# ============================================================

def research_agent(question: str, max_steps: int = 5) -> str:
    """
    max_steps: giới hạn số vòng lặp tối đa - "van an toàn" tránh agent
    lặp vô hạn (tốn quota API, tốn thời gian) nếu model cứ mãi search không dừng.
    """
    # "conversation" là danh sách sẽ nối dài dần - chính là trí nhớ của agent
    # trong suốt quá trình xử lý CÂU HỎI NÀY (không phải trí nhớ vĩnh viễn)
    conversation = [types.Content(role="user", parts=[types.Part(text=question)])]

    for step in range(1, max_steps + 1):
        print(f"\n--- Bước {step} ---")

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=conversation,
            config=types.GenerateContentConfig(tools=[tools]),
        )

        # SUY NGHĨ: model tự quyết định - đã đủ thông tin để trả lời chưa?
        if not response.function_calls:
            print("Agent quyết định: đã đủ thông tin, trả lời cuối cùng.")
            return response.text

        # Ghi lại "ý định" của model vào lịch sử hội thoại
        conversation.append(response.candidates[0].content)

        # HÀNH ĐỘNG: thực thi tool model yêu cầu
        call = response.function_calls[0]
        func_name = call.name
        func_args = dict(call.args)
        print(f"Agent quyết định: gọi {func_name}({func_args})")

        result = AVAILABLE_TOOLS[func_name](**func_args)

        # QUAN SÁT: ghi kết quả thật vào lịch sử, để vòng lặp sau model "nhìn thấy"
        conversation.append(
            types.Content(
                role="user",
                parts=[types.Part.from_function_response(
                    name=func_name,
                    response={"result": result},
                )],
            )
        )
        print("Đã ghi nhận kết quả, agent sẽ suy nghĩ tiếp ở bước sau...")

    return "Đã đạt giới hạn số bước tối đa mà agent vẫn chưa đưa ra câu trả lời cuối cùng."


if __name__ == "__main__":
    cau_hoi = "So sánh ngắn gọn LangGraph và CrewAI - 2 framework nào phù hợp hơn cho người mới bắt đầu?"
    ket_qua = research_agent(cau_hoi)

    print("\n" + "=" * 50)
    print("CÂU TRẢ LỜI CUỐI CÙNG:")
    print("=" * 50)
    print(ket_qua)
