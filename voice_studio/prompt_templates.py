"""
prompt_templates.py
====================
Built-in, editable prompt/style templates offered in the Generate Voice page.

Each template pre-fills an "instruction" (natural language direction sent
ahead of the user's text) and a suggested `emotion` value for
GenerationParams. The user can freely edit the instruction text in the UI
before generating — these are starting points, not fixed presets.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PromptTemplate:
    name: str
    instruction: str
    emotion: str


PROMPT_TEMPLATES: list[PromptTemplate] = [
    PromptTemplate(
        "Narrator",
        "Đọc với giọng thuyết minh trầm ấm, tốc độ vừa phải, rõ ràng từng chữ.",
        "Điềm tĩnh",
    ),
    PromptTemplate(
        "Professional",
        "Đọc với giọng chuyên nghiệp, nghiêm túc, phù hợp môi trường công sở.",
        "Nghiêm túc",
    ),
    PromptTemplate(
        "Review Product",
        "Đọc với giọng nhiệt tình, tự nhiên như đang giới thiệu sản phẩm cho bạn bè.",
        "Thân thiện",
    ),
    PromptTemplate(
        "TikTok",
        "Đọc nhanh, năng lượng cao, nhấn nhá ở những từ khoá quan trọng, hợp video ngắn.",
        "Sôi nổi",
    ),
    PromptTemplate(
        "Podcast",
        "Đọc với giọng trò chuyện tự nhiên, thong thả, như đang tâm sự với người nghe.",
        "Thư giãn",
    ),
    PromptTemplate(
        "Storytelling",
        "Đọc với giọng kể chuyện cuốn hút, lên xuống theo diễn biến câu chuyện.",
        "Biểu cảm",
    ),
    PromptTemplate(
        "Scary Story",
        "Đọc chậm, giọng trầm, tạo cảm giác rùng rợn, hồi hộp, nhấn mạnh ở các chi tiết đáng sợ.",
        "Bí ẩn",
    ),
    PromptTemplate(
        "Documentary",
        "Đọc với giọng thuyết minh tài liệu, khách quan, giàu thông tin.",
        "Điềm tĩnh",
    ),
    PromptTemplate(
        "News",
        "Đọc với giọng đọc tin tức, dứt khoát, tốc độ ổn định, phát âm chuẩn.",
        "Nghiêm túc",
    ),
    PromptTemplate(
        "ASMR",
        "Đọc rất nhẹ, rất chậm, thì thầm gần micro, tạo cảm giác thư giãn tối đa.",
        "Nhẹ nhàng",
    ),
    PromptTemplate(
        "Motivational",
        "Đọc với giọng đầy năng lượng, truyền cảm hứng, nhấn mạnh ở các câu kêu gọi hành động.",
        "Tích cực",
    ),
    PromptTemplate(
        "Audiobook",
        "Đọc với giọng audiobook mượt mà, ổn định, dễ nghe trong thời gian dài.",
        "Ấm áp",
    ),
]


def get_template(name: str) -> PromptTemplate | None:
    return next((t for t in PROMPT_TEMPLATES if t.name == name), None)


def template_names() -> list[str]:
    return [t.name for t in PROMPT_TEMPLATES]
