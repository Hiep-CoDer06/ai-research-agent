"""
MILESTONE 7: Tổng hợp báo cáo cuối + trích dẫn nguồn
Mục tiêu: Biến dict kết quả rời rạc thành 1 báo cáo hoàn chỉnh, có nguồn tham khảo đáng tin cậy.
"""

import os
import re
import json
from google import genai
from google.genai import types
from ddgs import DDGS

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("Chưa tìm thấy GEMINI_API_KEY.")

client = genai.Client(api_key=api_key)


# ============================================================
# PHẦN 1: search_web - giống hệt M6
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


# ============================================================
# PHẦN 2: research_agent - THÊM system_instruction bắt buộc trích dẫn
# ============================================================

RESEARCH_SYSTEM_PROMPT = (
    "Bạn là một trợ lý nghiên cứu nghiêm túc. "
    "Khi dùng thông tin từ kết quả tìm kiếm, LUÔN ghi kèm URL nguồn ngay sau thông tin đó, "
    "dạng: thông tin (Nguồn: https://...). "
    "TUYỆT ĐỐI không bịa thêm thông tin không có trong kết quả tìm kiếm."
)


def research_agent(question: str, max_steps: int = 4) -> str:
    conversation = [types.Content(role="user", parts=[types.Part(text=question)])]
    for _ in range(max_steps):
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=conversation,
            config=types.GenerateContentConfig(
                tools=[tools],
                system_instruction=RESEARCH_SYSTEM_PROMPT,  # MỚI: ép buộc trích dẫn
                temperature=0.2,
            ),
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


def plan_research(topic: str, so_cau_hoi: int = 3) -> list:
    prompt = (
        f'Chủ đề nghiên cứu: "{topic}"\n\n'
        f"Hãy chia chủ đề này thành đúng {so_cau_hoi} câu hỏi con cụ thể, "
        f"mỗi câu hỏi tập trung vào MỘT khía cạnh riêng biệt."
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
# PHẦN 3: MỚI - Trích xuất URL bằng code (KHÔNG dùng LLM cho việc này)
# ============================================================

def extract_urls(text: str) -> list:
    """Tìm tất cả URL trong 1 đoạn text bằng regex - chính xác 100%, không phụ thuộc LLM."""
    return re.findall(r'https?://[^\s\)\]]+', text)


# ============================================================
# PHẦN 4: MỚI - Tổng hợp thành báo cáo hoàn chỉnh
# ============================================================

def synthesize_report(topic: str, results: dict) -> str:
    """Ghép các câu trả lời con thành 1 báo cáo liền mạch, có Mở đầu/Thân bài/Kết luận."""

    # Gom toàn bộ dữ liệu nghiên cứu thô thành 1 khối text để đưa vào prompt
    raw_data = "\n\n".join(
        f"### Câu hỏi con: {q}\n{a}" for q, a in results.items()
    )

    system_prompt = (
        "Bạn là một chuyên gia viết báo cáo nghiên cứu. "
        "Viết báo cáo bằng tiếng Việt, định dạng Markdown, mạch lạc, không lặp nguyên văn câu hỏi con. "
        "Giữ nguyên các trích dẫn (Nguồn: URL) đã có trong dữ liệu gốc khi đưa thông tin vào báo cáo."
    )

    prompt = (
        f'Chủ đề: "{topic}"\n\n'
        f"Dựa trên dữ liệu nghiên cứu thô dưới đây, viết một báo cáo hoàn chỉnh gồm: "
        f"1) Mở đầu giới thiệu chủ đề, 2) Các phần thân bài theo từng khía cạnh, "
        f"3) Kết luận tóm tắt insight chính.\n\n"
        f"DỮ LIỆU NGHIÊN CỨU THÔ:\n{raw_data}"
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.4,  # cao hơn 1 chút vì đây là phần "viết văn", không phải tra cứu sự kiện
        ),
    )
    bao_cao = response.text

    # Trích xuất URL bằng CODE (không phải LLM) từ dữ liệu thô gốc - đảm bảo không sót nguồn
    tat_ca_url = []
    for answer in results.values():
        for url in extract_urls(answer):
            if url not in tat_ca_url:
                tat_ca_url.append(url)  # giữ thứ tự, loại trùng lặp

    if tat_ca_url:
        bao_cao += "\n\n## Tài liệu tham khảo\n"
        for i, url in enumerate(tat_ca_url, 1):
            bao_cao += f"{i}. {url}\n"

    return bao_cao


# ============================================================
# PHẦN 5: Orchestration - ráp toàn bộ pipeline lại
# ============================================================

def deep_research(topic: str) -> str:
    print(f"\n>>> Chủ đề: {topic}")
    print("Đang lập kế hoạch...")
    sub_questions = plan_research(topic)
    print(f"Đã chia thành {len(sub_questions)} câu hỏi con.")

    ket_qua = {}
    for q in sub_questions:
        print(f"Đang nghiên cứu: {q}")
        ket_qua[q] = research_agent(q)

    print("Đang tổng hợp báo cáo cuối cùng...")
    return synthesize_report(topic, ket_qua)


if __name__ == "__main__":
    bao_cao_cuoi_cung = deep_research("Xu hướng Agentic AI trong tuyển dụng năm 2026")

    # Lưu ra file - đây chính là sản phẩm thật của project
    with open("bao_cao_nghien_cuu.md", "w", encoding="utf-8") as f:
        f.write(bao_cao_cuoi_cung)

    print("\n" + "=" * 50)
    print("Đã lưu báo cáo vào file: bao_cao_nghien_cuu.md")
    print("=" * 50)
    print(bao_cao_cuoi_cung)
