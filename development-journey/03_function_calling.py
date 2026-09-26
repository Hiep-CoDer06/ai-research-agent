"""
MILESTONE 3: Function Calling - "trái tim" của một AI Agent
Mục tiêu: Hiểu cơ chế model YÊU CẦU gọi hàm, còn code của bạn mới THỰC SỰ thực thi
"""

import os
import datetime
from google import genai
from google.genai import types

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("Chưa tìm thấy GEMINI_API_KEY.")

client = genai.Client(api_key=api_key)


# ============================================================
# BƯỚC 1: Các hàm Python THẬT - đây là những gì thực sự chạy trên máy
# ============================================================

def get_current_time() -> str:
    """Trả về ngày giờ hiện tại."""
    now = datetime.datetime.now()
    return now.strftime("%H:%M:%S ngày %d/%m/%Y")


def calculate(expression: str) -> str:
    """Tính một biểu thức số học đơn giản, ví dụ: '12 * 7 + 3'."""
    # LƯU Ý: eval() chỉ dùng ở đây cho MỤC ĐÍCH HỌC TẬP với input đơn giản.
    # Trong dự án thực tế, không nên dùng eval() trực tiếp vì rủi ro bảo mật -
    # nên dùng thư viện tính toán an toàn hơn (vd: numexpr) hoặc validate kỹ input.
    try:
        result = eval(expression, {"__builtins__": {}})
        return str(result)
    except Exception as e:
        return f"Lỗi tính toán: {e}"


# "Bảng tra cứu" - ánh xạ tên hàm (string model trả về) -> hàm Python thật
AVAILABLE_TOOLS = {
    "get_current_time": get_current_time,
    "calculate": calculate,
}


# ============================================================
# BƯỚC 2: Mô tả các hàm trên cho model hiểu (model CHỈ đọc mô tả này)
# ============================================================

time_tool = types.FunctionDeclaration(
    name="get_current_time",
    description="Lấy ngày giờ hiện tại. Dùng khi người dùng hỏi về thời gian/ngày tháng bây giờ.",
    parameters=types.Schema(type="OBJECT", properties={}),
)

calc_tool = types.FunctionDeclaration(
    name="calculate",
    description="Tính toán một biểu thức số học. Dùng khi người dùng cần tính con số cụ thể.",
    parameters=types.Schema(
        type="OBJECT",
        properties={
            "expression": types.Schema(
                type="STRING",
                description="Biểu thức toán học cần tính, ví dụ: '15 * 8'",
            ),
        },
        required=["expression"],
    ),
)

tools = types.Tool(function_declarations=[time_tool, calc_tool])


# ============================================================
# BƯỚC 3: Vòng lặp - gọi model, phát hiện yêu cầu gọi hàm, thực thi, gửi kết quả lại
# ============================================================

def ask_agent(user_question: str) -> str:
    print(f"\n>>> Câu hỏi: {user_question}")

    # LƯỢT 1: gửi câu hỏi kèm danh sách tool đang có
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_question,
        config=types.GenerateContentConfig(tools=[tools]),
    )

    function_calls = response.function_calls

    if not function_calls:
        print("(Model trả lời trực tiếp - không cần gọi tool nào)")
        return response.text

    # Model YÊU CẦU gọi hàm - đây là lúc code của bạn (không phải model) thực thi THẬT
    call = function_calls[0]
    func_name = call.name
    func_args = dict(call.args)
    print(f"(Model yêu cầu gọi: {func_name}({func_args}))")

    real_function = AVAILABLE_TOOLS[func_name]
    result = real_function(**func_args)
    print(f"(Đã thực thi thật - kết quả: {result})")

    # LƯỢT 2: gửi kết quả thật ngược lại cho model để nó viết câu trả lời cuối cùng
    follow_up = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Content(role="user", parts=[types.Part(text=user_question)]),
            response.candidates[0].content,          # phần model yêu cầu gọi hàm
            types.Content(
                role="user",
                parts=[
                    types.Part.from_function_response(
                        name=func_name,
                        response={"result": result},
                    )
                ],
            ),
        ],
        config=types.GenerateContentConfig(tools=[tools]),
    )
    return follow_up.text


if __name__ == "__main__":
    print(ask_agent("Bây giờ là mấy giờ rồi?"))
    print(ask_agent("15 nhân 24 cộng 8 bằng bao nhiêu?"))
    print(ask_agent("Thủ đô của Pháp là gì?"))  # câu này KHÔNG cần tool nào cả
