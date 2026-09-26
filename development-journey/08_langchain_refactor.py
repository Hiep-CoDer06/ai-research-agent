"""
MILESTONE 8: Refactor bằng LangChain/LangGraph - framework chuẩn công nghiệp
Mục tiêu: Thay vòng lặp ReAct viết tay (M5) bằng create_agent -
bên trong nó làm ĐÚNG 6 bước bạn đã hiểu rõ ở M3, chỉ là đã được đóng gói sẵn.
"""

import os
import re
import json
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from google import genai
from google.genai import types
from ddgs import DDGS

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("Chưa tìm thấy GEMINI_API_KEY.")

# Vẫn giữ client "thô" của google-genai cho phần Planning & Synthesis (M6, M7) -
# 2 phần đó chỉ cần gọi model 1 lần, không cần vòng lặp tool-calling, nên viết
# trực tiếp bằng SDK gốc vẫn đơn giản hơn, không cần "mượn" qua LangChain.
raw_client = genai.Client(api_key=api_key)


# ============================================================
# PHẦN 1: MỚI - Tool viết bằng decorator @tool
# So sánh với M3-M7: KHÔNG cần tự viết types.FunctionDeclaration + types.Schema
# nữa - @tool tự đọc docstring của hàm để sinh ra "thực đơn" cho model.
# Đây là lý do vì sao viết docstring rõ ràng từ đầu (thói quen từ M1) rất đáng giá.
# ============================================================

@tool
def search_web(query: str) -> str:
    """Tìm kiếm thông tin mới nhất trên internet. Dùng khi câu hỏi cần thông tin cập nhật."""
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=5))
    if not results:
        return "Không tìm thấy kết quả nào."
    formatted = []
    for i, r in enumerate(results, 1):
        formatted.append(f"[{i}] {r['title']}\n{r['body']}\nNguồn: {r['href']}")
    return "\n\n".join(formatted)


# ============================================================
# PHẦN 2: MỚI - create_agent thay thế TOÀN BỘ vòng lặp ReAct viết tay ở M5
# ============================================================

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key, temperature=0.2)

RESEARCH_SYSTEM_PROMPT = (
    "Bạn là một trợ lý nghiên cứu nghiêm túc. "
    "Khi dùng thông tin từ kết quả tìm kiếm, LUÔN ghi kèm URL nguồn ngay sau thông tin đó. "
    "TUYỆT ĐỐI không bịa thêm thông tin không có trong kết quả tìm kiếm."
)

agent = create_agent(
    model=llm,
    tools=[search_web],
    system_prompt=RESEARCH_SYSTEM_PROMPT,
)


def research_agent(question: str) -> str:
    """Thay thế hoàn toàn hàm research_agent() ~40 dòng viết tay ở M5-M7."""
    result = agent.invoke({"messages": [("user", question)]})
    return result["messages"][-1].content


# ============================================================
# PHẦN 3: plan_research + synthesize_report - GIỮ NGUYÊN từ M6, M7
# (2 phần này không liên quan đến vòng lặp tool-calling nên không cần đổi)
# ============================================================

def plan_research(topic: str, so_cau_hoi: int = 3) -> list:
    prompt = (
        f'Chủ đề nghiên cứu: "{topic}"\n\n'
        f"Hãy chia chủ đề này thành đúng {so_cau_hoi} câu hỏi con cụ thể, "
        f"mỗi câu hỏi tập trung vào MỘT khía cạnh riêng biệt."
    )
    response = raw_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema={"type": "ARRAY", "items": {"type": "STRING"}},
        ),
    )
    return json.loads(response.text)


def extract_urls(text: str) -> list:
    return re.findall(r'https?://[^\s\)\]]+', text)


def synthesize_report(topic: str, results: dict) -> str:
    raw_data = "\n\n".join(f"### Câu hỏi con: {q}\n{a}" for q, a in results.items())
    system_prompt = (
        "Bạn là một chuyên gia viết báo cáo nghiên cứu. "
        "Viết báo cáo bằng tiếng Việt, định dạng Markdown, mạch lạc. "
        "Giữ nguyên các trích dẫn (URL) đã có trong dữ liệu gốc."
    )
    prompt = (
        f'Chủ đề: "{topic}"\n\n'
        f"Dựa trên dữ liệu nghiên cứu thô dưới đây, viết một báo cáo hoàn chỉnh gồm: "
        f"Mở đầu, Thân bài theo từng khía cạnh, Kết luận.\n\n"
        f"DỮ LIỆU NGHIÊN CỨU THÔ:\n{raw_data}"
    )
    response = raw_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(system_instruction=system_prompt, temperature=0.4),
    )
    bao_cao = response.text

    tat_ca_url = []
    for answer in results.values():
        for url in extract_urls(answer):
            if url not in tat_ca_url:
                tat_ca_url.append(url)
    if tat_ca_url:
        bao_cao += "\n\n## Tài liệu tham khảo\n"
        for i, url in enumerate(tat_ca_url, 1):
            bao_cao += f"{i}. {url}\n"
    return bao_cao


# ============================================================
# PHẦN 4: Orchestration - giống hệt M7
# ============================================================

def deep_research(topic: str) -> str:
    print(f"\n>>> Chủ đề: {topic}")
    sub_questions = plan_research(topic)
    print(f"Đã chia thành {len(sub_questions)} câu hỏi con.")

    ket_qua = {}
    for q in sub_questions:
        print(f"Đang nghiên cứu: {q}")
        ket_qua[q] = research_agent(q)

    print("Đang tổng hợp báo cáo...")
    return synthesize_report(topic, ket_qua)


if __name__ == "__main__":
    bao_cao = deep_research("Xu hướng Agentic AI trong tuyển dụng năm 2026")
    with open("bao_cao_nghien_cuu_m8.md", "w", encoding="utf-8") as f:
        f.write(bao_cao)
    print("\nĐã lưu: bao_cao_nghien_cuu_m8.md")
    print(bao_cao)
