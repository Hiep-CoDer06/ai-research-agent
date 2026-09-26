"""
MILESTONE 9: Giao diện Streamlit cho Research Agent
File này gộp TOÀN BỘ logic từ M8 (search_web, research_agent, plan_research,
synthesize_report) và thêm giao diện web để người khác dùng thử được.
"""

import os
import re
import json
import streamlit as st
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from google import genai
from google.genai import types
from ddgs import DDGS

# ============================================================
# Cấu hình trang + kiểm tra API key
# ============================================================

st.set_page_config(page_title="AI Research Agent", page_icon="🔎")
st.title("🔎 AI Research Agent")
st.caption("Nhập một chủ đề, agent sẽ tự lập kế hoạch, tìm kiếm trên internet, "
           "và viết báo cáo hoàn chỉnh kèm trích dẫn nguồn.")

try:
    # Khi deploy trên Streamlit Community Cloud, secret được đọc qua st.secrets
    api_key = st.secrets["GEMINI_API_KEY"]
except (FileNotFoundError, KeyError):
    # Khi chạy local, đọc từ biến môi trường như mọi milestone trước
    api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error(
        "Chưa cấu hình GEMINI_API_KEY. "
        "Nếu chạy local: set biến môi trường trước khi chạy `streamlit run app.py`. "
        "Nếu đã deploy trên Streamlit Community Cloud: thêm secret GEMINI_API_KEY "
        "trong Settings > Secrets của app."
    )
    st.stop()

raw_client = genai.Client(api_key=api_key)
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key, temperature=0.2)


# ============================================================
# Toàn bộ logic agent - giữ nguyên y hệt M8
# ============================================================

@tool
def search_web(query: str) -> str:
    """Tìm kiếm thông tin mới nhất trên internet."""
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=5))
    if not results:
        return "Không tìm thấy kết quả nào."
    formatted = []
    for i, r in enumerate(results, 1):
        formatted.append(f"[{i}] {r['title']}\n{r['body']}\nNguồn: {r['href']}")
    return "\n\n".join(formatted)


RESEARCH_SYSTEM_PROMPT = (
    "Bạn là một trợ lý nghiên cứu nghiêm túc. "
    "Khi dùng thông tin từ kết quả tìm kiếm, LUÔN ghi kèm URL nguồn. "
    "TUYỆT ĐỐI không bịa thêm thông tin không có trong kết quả tìm kiếm."
)

agent = create_agent(model=llm, tools=[search_web], system_prompt=RESEARCH_SYSTEM_PROMPT)


def research_agent(question: str) -> str:
    result = agent.invoke({"messages": [("user", question)]})
    return result["messages"][-1].content


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

    urls = []
    for answer in results.values():
        for u in extract_urls(answer):
            if u not in urls:
                urls.append(u)
    if urls:
        bao_cao += "\n\n## Tài liệu tham khảo\n"
        bao_cao += "\n".join(f"{i}. {u}" for i, u in enumerate(urls, 1))
    return bao_cao


# ============================================================
# GIAO DIỆN - phần MỚI của M9
# ============================================================

topic = st.text_input(
    "Chủ đề nghiên cứu",
    placeholder="VD: Xu hướng Agentic AI trong tuyển dụng năm 2026",
)

if st.button("Bắt đầu nghiên cứu", type="primary"):
    if not topic.strip():
        st.warning("Vui lòng nhập chủ đề trước.")
    else:
        with st.status("Agent đang làm việc...", expanded=True) as status:
            st.write("🧭 Đang lập kế hoạch...")
            sub_questions = plan_research(topic)
            st.write(f"Đã chia thành {len(sub_questions)} câu hỏi con:")
            for q in sub_questions:
                st.write(f"- {q}")

            ket_qua = {}
            for q in sub_questions:
                st.write(f"🔍 Đang nghiên cứu: {q}")
                ket_qua[q] = research_agent(q)

            st.write("✍️ Đang tổng hợp báo cáo...")
            bao_cao = synthesize_report(topic, ket_qua)
            status.update(label="Hoàn thành!", state="complete")

        st.markdown("## Báo cáo")
        st.markdown(bao_cao)

        st.download_button(
            label="📥 Tải báo cáo (.md)",
            data=bao_cao,
            file_name="bao_cao_nghien_cuu.md",
            mime="text/markdown",
        )
