"""
ui/pages/about.py
===================
Static information page: version, credits, architecture note.
"""

from __future__ import annotations

import customtkinter as ctk

from config import APP_NAME, APP_VERSION


class AboutPage(ctk.CTkFrame):
    """Simple static About screen."""

    def __init__(self, master) -> None:
        super().__init__(master, fg_color="transparent")

        ctk.CTkLabel(
            self, text=APP_NAME, font=ctk.CTkFont(size=32, weight="bold")
        ).pack(anchor="w", padx=20, pady=(40, 4))
        ctk.CTkLabel(
            self, text=f"Phiên bản {APP_VERSION}", text_color="#8A8A8A"
        ).pack(anchor="w", padx=20)

        info = (
            "AI Voice Studio là công cụ tạo giọng đọc AI sử dụng Google Gemini "
            "TTS API, được thiết kế dành riêng cho người sáng tạo nội dung "
            "TikTok, YouTube và Facebook.\n\n"
            "Kiến trúc phần mềm được xây dựng theo hướng module hoá: lớp API "
            "(api/gemini.py) hoàn toàn tách biệt với lớp giao diện (ui/), nên "
            "trong tương lai có thể bổ sung OpenAI TTS, ElevenLabs hoặc Azure "
            "Speech mà không cần sửa đổi giao diện người dùng.\n\n"
            "Công nghệ sử dụng: Python, CustomTkinter, requests, threading, "
            "ffmpeg, pygame.\n\n"
            "Nếu bạn không biết sử dụng hãy liên hệ mình tele @cuongbkv"
        )
        ctk.CTkLabel(
            self, text=info, wraplength=700, justify="left"
        ).pack(anchor="w", padx=20, pady=20)
