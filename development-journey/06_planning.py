"""
MILESTONE 6: Agent tự chia nhỏ chủ đề nghiên cứu (Planning)
Mục tiêu: Từ 1 chủ đề RỘNG, tự tạo ra nhiều câu hỏi con CỤ THỂ trước khi bắt đầu search,
thay vì để agent tự "đoán mò" nên tìm kiếm gì.
"""

import os
import json
from google import genai
from google.genai import types
from ddgs import DDGS

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("Chưa tìm thấy GEMINI_API_KEY.")

client = genai.Client(api_key=api_key)


# ============================================================
# PHẦN 1: search_web + vòng lặp ReAct - TÁI SỬ DỤNG y hệt M5
# ============================================================

def search_web(query: str) -> str:
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
    description="Tìm kiếm thông tin mới nhất trên internet.",
    parameters=types.Schema(
        type="OBJECT",
        properties={"query": types.Schema(type="STRING", description="Từ khóa tìm kiếm")},
        required=["query"],
    ),
)
tools = types.Tool(function_declarations=[search_tool])


def research_agent(question: str, max_steps: int = 4) -> str:
    """Vòng lặp ReAct để trả lời 1 câu hỏi CỤ THỂ - giống hệt logic ở M5."""
    conversation = [types.Content(role="user", parts=[types.Part(text=question)])]
    for _ in range(max_steps):
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=conversation,
            config=types.GenerateContentConfig(tools=[tools]),
        )
        if not response.function_calls:
            return response.text
        conversation.append(response.candidates[0].content)
        call = response.function_calls[0]
        result = AVAILABLE_TOOLS[call.name](**dict(call.args))
        conversation.append(
            types.Content(role="user", parts=[types.Part.from_function_response(
                name=call.name, response={"result": result})])
        )
    return "Không đủ bước để hoàn thành."


# ============================================================
# PHẦN 2: MỚI - Bước lập kế hoạch (Planning)
# ============================================================

def plan_research(topic: str, so_cau_hoi: int = 3) -> list:
    """
    Từ 1 chủ đề RỘNG, yêu cầu model tự chia thành các câu hỏi con CỤ THỂ.
    response_schema ÉP BUỘC model trả đúng định dạng JSON list các chuỗi text -
    không cần tự viết code regex để "đoán" xem model trả lời theo cấu trúc nào.
    """
    prompt = (
        f'Chủ đề nghiên cứu: "{topic}"\n\n'
        f"Hãy chia chủ đề này thành đúng {so_cau_hoi} câu hỏi con cụ thể, "
        f"mỗi câu hỏi tập trung vào MỘT khía cạnh riêng biệt, "
        f"đủ cụ thể để tìm kiếm được trên internet."
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema={"type": "ARRAY", "items": {"type": "STRING"}},
        ),
    )
    return json.loads(response.text)


# ============================================================
# PHẦN 3: Ráp lại - Plan trước, rồi Execute từng câu hỏi con
# ============================================================

def deep_research(topic: str) -> dict:
    print(f"\n>>> Chủ đề: {topic}")
    print("Đang lập kế hoạch...")

    sub_questions = plan_research(topic)
    print(f"Đã chia thành {len(sub_questions)} câu hỏi con:")
    for q in sub_questions:
        print(f"  - {q}")

    ket_qua = {}
    for q in sub_questions:
        print(f"\nĐang nghiên cứu: {q}")
        ket_qua[q] = research_agent(q)

    return ket_qua


if __name__ == "__main__":
    ket_qua = deep_research("Xu hướng Agentic AI trong tuyển dụng năm 2026")

    print("\n" + "=" * 50)
    print("KẾT QUẢ NGHIÊN CỨU THEO TỪNG CÂU HỎI CON:")
    print("=" * 50)
    for q, a in ket_qua.items():
        print(f"\n### {q}")
        print(a)
