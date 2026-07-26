"""
ui/pages/generate_voice.py
============================
The main generation workflow: pick a voice + prompt template, type/paste
text, tune voice parameters, then Generate (single) or queue many texts and
Generate All. Runs entirely on background threads so the UI never freezes.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from tkinter import filedialog
from typing import Callable, Optional

import customtkinter as ctk

from config import AppSettings, SUPPORTED_FORMATS
from api.models import GenerationParams, HistoryEntry, Voice
from api.gemini import GeminiTTSClient, GeminiAPIError
from cache import GenerationCache
from history_repository import HistoryRepository
from player import AudioPlayer
from prompt_templates import PROMPT_TEMPLATES, get_template, template_names
from voice_repository import VoiceRepository
import utils
from ui.components.audio_player_widget import AudioPlayerWidget
from ui.components.queue_widget import QueueWidget

logger = logging.getLogger("AI Voice Studio")


class GenerateVoicePage(ctk.CTkFrame):
    """Text -> speech generation workspace."""

    def __init__(
        self,
        master,
        settings: AppSettings,
        voice_repo: VoiceRepository,
        history_repo: HistoryRepository,
        cache: GenerationCache,
        player: AudioPlayer,
        get_client: Callable[[], Optional[GeminiTTSClient]],
        on_generation_complete: Callable[[], None],
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self._settings = settings
        self._voice_repo = voice_repo
        self._history_repo = history_repo
        self._cache = cache
        self._player = player
        self._get_client = get_client
        self._on_generation_complete = on_generation_complete

        self._cancel_event = threading.Event()
        self._last_output_path: Optional[str] = None
        self._preselect_voice_id: Optional[str] = None

        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self, text="Generate Voice", font=ctk.CTkFont(size=26, weight="bold")
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(20, 10))

        self._build_left_column()
        self._build_right_column()
        self.refresh_voice_list()

    # ------------------------------------------------------------------ #
    def _build_left_column(self) -> None:
        left = ctk.CTkScrollableFrame(self, fg_color="transparent")
        left.grid(row=1, column=0, sticky="nsew", padx=(20, 10), pady=(0, 20))

        # Voice + template row
        select_row = ctk.CTkFrame(left, fg_color="transparent")
        select_row.pack(fill="x", pady=(0, 10))
        select_row.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(select_row, text="Voice").grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(select_row, text="Prompt Template").grid(row=0, column=1, sticky="w")

        self._voice_var = ctk.StringVar()
        self._voice_menu = ctk.CTkOptionMenu(select_row, variable=self._voice_var, values=[""])
        self._voice_menu.grid(row=1, column=0, sticky="ew", padx=(0, 6))

        self._template_var = ctk.StringVar(value=template_names()[0])
        template_menu = ctk.CTkOptionMenu(
            select_row, variable=self._template_var, values=template_names(),
            command=self._on_template_selected,
        )
        template_menu.grid(row=1, column=1, sticky="ew", padx=(6, 0))

        ctk.CTkLabel(left, text="Chỉ dẫn phong cách (có thể sửa)").pack(anchor="w", pady=(6, 2))
        self._instruction_box = ctk.CTkTextbox(left, height=50)
        self._instruction_box.pack(fill="x", pady=(0, 10))
        self._on_template_selected(self._template_var.get())

        ctk.CTkLabel(left, text="Nội dung cần đọc").pack(anchor="w", pady=(0, 2))
        self._text_box = ctk.CTkTextbox(left, height=180)
        self._text_box.pack(fill="x", pady=(0, 4))
        self._text_box.bind("<KeyRelease>", lambda _e: self._update_counters())

        self._counter_label = ctk.CTkLabel(
            left, text="0 ký tự  •  0 từ  •  0 câu  •  ~0:00", text_color="#8A8A8A"
        )
        self._counter_label.pack(anchor="w", pady=(0, 14))

        self._build_parameter_sliders(left)
        self._build_output_row(left)
        self._build_action_buttons(left)

        self._player_widget = AudioPlayerWidget(left, self._player)
        self._player_widget.pack(fill="x", pady=(14, 0))

        self._status_label = ctk.CTkLabel(left, text="", text_color="#8A8A8A")
        self._status_label.pack(anchor="w", pady=(8, 0))

    def _build_parameter_sliders(self, parent) -> None:
        ctk.CTkLabel(
            parent, text="Voice Parameters", font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", pady=(0, 6))

        self._sliders: dict[str, ctk.CTkSlider] = {}
        self._slider_value_labels: dict[str, ctk.CTkLabel] = {}
        slider_specs = [
            ("speed", "Speed", 0.5, 2.0, 1.0),
            ("pitch", "Pitch", -20.0, 20.0, 0.0),
            ("volume", "Volume", 0.0, 2.0, 1.0),
            ("expressiveness", "Expressiveness", 0.0, 1.0, 0.5),
            ("pause_strength", "Pause Strength", 0.0, 1.0, 0.5),
            ("randomness", "Randomness", 0.0, 1.0, 0.3),
            ("stability", "Stability", 0.0, 1.0, 0.7),
        ]
        for key, label, lo, hi, default in slider_specs:
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", pady=3)
            row.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(row, text=label, width=130, anchor="w").grid(row=0, column=0)
            slider = ctk.CTkSlider(
                row, from_=lo, to=hi,
                command=lambda v, k=key: self._on_slider_change(k, v),
            )
            slider.set(default)
            slider.grid(row=0, column=1, sticky="ew", padx=8)
            value_lbl = ctk.CTkLabel(row, text=f"{default:.2f}", width=50)
            value_lbl.grid(row=0, column=2)
            self._sliders[key] = slider
            self._slider_value_labels[key] = value_lbl

        emotion_row = ctk.CTkFrame(parent, fg_color="transparent")
        emotion_row.pack(fill="x", pady=(6, 0))
        ctk.CTkLabel(emotion_row, text="Emotion", width=130, anchor="w").pack(side="left")
        self._emotion_var = ctk.StringVar(value="Trung tính")
        emotion_options = [
            "Trung tính", "Điềm tĩnh", "Nghiêm túc", "Thân thiện", "Thư giãn",
            "Biểu cảm", "Bí ẩn", "Nhẹ nhàng", "Tích cực", "Ấm áp", "Sôi nổi",
        ]
        ctk.CTkOptionMenu(
            emotion_row, values=emotion_options, variable=self._emotion_var
        ).pack(side="left", fill="x", expand=True, padx=8)

    def _build_output_row(self, parent) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(14, 0))
        row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(row, text="Format", width=60).grid(row=0, column=0, sticky="w")
        self._format_var = ctk.StringVar(value=self._settings.default_format)
        ctk.CTkOptionMenu(
            row, values=SUPPORTED_FORMATS, variable=self._format_var, width=90
        ).grid(row=0, column=1, sticky="w", padx=(6, 20))

        ctk.CTkLabel(row, text="Output Folder").grid(row=0, column=2, sticky="w")
        self._output_folder_var = ctk.StringVar(value=self._settings.output_folder)
        ctk.CTkEntry(row, textvariable=self._output_folder_var).grid(
            row=0, column=3, sticky="ew", padx=6
        )
        ctk.CTkButton(row, text="...", width=36, command=self._browse_output_folder).grid(
            row=0, column=4
        )
        row.grid_columnconfigure(3, weight=1)

    def _build_action_buttons(self, parent) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(14, 0))

        self._generate_btn = ctk.CTkButton(
            row, text="🪄 Generate", height=40, command=self._on_generate_clicked
        )
        self._generate_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self._add_queue_btn = ctk.CTkButton(
            row, text="➕ Thêm vào Queue (mỗi dòng 1 đoạn)", height=40,
            fg_color="transparent", border_width=1,
            command=self._on_generate_all_clicked,
        )
        self._add_queue_btn.pack(side="left", fill="x", expand=True, padx=(6, 0))

    def _build_right_column(self) -> None:
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=1, column=1, sticky="nsew", padx=(10, 20), pady=(0, 20))
        self._queue_widget = QueueWidget(
            right, on_cancel=self._on_cancel_queue, on_retry_failed=self._on_retry_failed
        )
        self._queue_widget.pack(fill="both", expand=True)

    # ------------------------------------------------------------------ #
    def refresh_voice_list(self) -> None:
        """Repopulate the voice dropdown (call after voices.json reload)."""
        voices = self._voice_repo.all()
        names = [f"{v.name} ({v.id})" for v in voices]
        self._voice_menu.configure(values=names or ["(Không có voice)"])
        if self._preselect_voice_id:
            match = next((v for v in voices if v.id == self._preselect_voice_id), None)
            if match:
                self._voice_var.set(f"{match.name} ({match.id})")
                self._preselect_voice_id = None
                return
        if names and not self._voice_var.get():
            self._voice_var.set(names[0])

    def preselect_voice(self, voice: Voice) -> None:
        """Called when the user clicks 'Use this voice' in Voice Library."""
        self._preselect_voice_id = voice.id
        self.refresh_voice_list()

    def _current_voice_id(self) -> Optional[str]:
        raw = self._voice_var.get()
        if "(" not in raw:
            return None
        return raw.rsplit("(", 1)[-1].rstrip(")")

    def _on_template_selected(self, name: str) -> None:
        template = get_template(name)
        if template:
            self._instruction_box.delete("1.0", "end")
            self._instruction_box.insert("1.0", template.instruction)
            if hasattr(self, "_emotion_var"):
                self._emotion_var.set(template.emotion)

    def _on_slider_change(self, key: str, value: float) -> None:
        self._slider_value_labels[key].configure(text=f"{float(value):.2f}")

    def _update_counters(self) -> None:
        text = self._text_box.get("1.0", "end-1c")
        speed = self._sliders["speed"].get()
        chars = utils.count_characters(text)
        words = utils.count_words(text)
        sentences = utils.count_sentences(text)
        duration = utils.estimate_duration_seconds(text, speed)
        self._counter_label.configure(
            text=f"{chars} ký tự  •  {words} từ  •  {sentences} câu  •  "
                 f"~{utils.format_duration(duration)}"
        )

    def _browse_output_folder(self) -> None:
        folder = filedialog.askdirectory(initialdir=self._output_folder_var.get() or ".")
        if folder:
            self._output_folder_var.set(folder)

    def _current_params(self) -> GenerationParams:
        return GenerationParams(
            speed=self._sliders["speed"].get(),
            pitch=self._sliders["pitch"].get(),
            volume=self._sliders["volume"].get(),
            emotion=self._emotion_var.get(),
            expressiveness=self._sliders["expressiveness"].get(),
            pause_strength=self._sliders["pause_strength"].get(),
            randomness=self._sliders["randomness"].get(),
            stability=self._sliders["stability"].get(),
        )

    # ------------------------------------------------------------------ #
    def _on_generate_clicked(self) -> None:
        text = self._text_box.get("1.0", "end-1c").strip()
        if not text:
            self._status_label.configure(text="Vui lòng nhập nội dung.", text_color="#EF5350")
            return
        voice_id = self._current_voice_id()
        if not voice_id:
            self._status_label.configure(text="Vui lòng chọn voice.", text_color="#EF5350")
            return
        client = self._get_client()
        if client is None:
            self._status_label.configure(
                text="Chưa cấu hình API Key. Vào Settings để thêm.", text_color="#EF5350"
            )
            return

        self._generate_btn.configure(state="disabled", text="Đang tạo...")
        self._status_label.configure(text="Đang xử lý...", text_color="#8A8A8A")
        self._queue_widget.set_items([text])

        thread = threading.Thread(
            target=self._run_single_generation, args=(client, text, voice_id), daemon=True
        )
        thread.start()

    def _run_single_generation(self, client: GeminiTTSClient, text: str, voice_id: str) -> None:
        result_path, error = self._generate_one(client, text, voice_id, index=0)
        self.after(0, lambda: self._finish_single(result_path, error))

    def _finish_single(self, result_path: Optional[str], error: Optional[str]) -> None:
        self._generate_btn.configure(state="normal", text="🪄 Generate")
        if error:
            self._status_label.configure(text=error, text_color="#EF5350")
            return
        self._status_label.configure(text=f"Đã tạo: {result_path}", text_color="#66BB6A")
        if result_path:
            duration = utils.estimate_duration_seconds(
                self._text_box.get("1.0", "end-1c"), self._sliders["speed"].get()
            )
            self._player_widget.load_file(result_path, duration)
        self._on_generation_complete()

    # ------------------------------------------------------------------ #
    def _on_generate_all_clicked(self) -> None:
        raw = self._text_box.get("1.0", "end-1c")
        lines = [line.strip() for line in raw.split("\n") if line.strip()]
        if not lines:
            self._status_label.configure(
                text="Nhập mỗi đoạn text trên một dòng để tạo hàng đợi.", text_color="#EF5350"
            )
            return
        voice_id = self._current_voice_id()
        client = self._get_client()
        if voice_id is None or client is None:
            self._status_label.configure(
                text="Cần chọn voice và cấu hình API Key trước.", text_color="#EF5350"
            )
            return

        self._cancel_event.clear()
        self._queue_widget.set_items(lines)
        self._add_queue_btn.configure(state="disabled")
        self._generate_btn.configure(state="disabled")

        thread = threading.Thread(
            target=self._run_queue, args=(client, lines, voice_id), daemon=True
        )
        thread.start()

    def _run_queue(self, client: GeminiTTSClient, lines: list[str], voice_id: str) -> None:
        for index, text in enumerate(lines):
            if self._cancel_event.is_set():
                self.after(0, lambda i=index: self._queue_widget.update_status(i, "Cancelled"))
                continue
            self.after(0, lambda i=index: self._queue_widget.update_status(i, "Generating"))
            result_path, error = self._generate_one(client, text, voice_id, index=index)
            if error:
                self.after(0, lambda i=index: self._queue_widget.update_status(i, "Failed", error))
            else:
                self.after(0, lambda i=index: self._queue_widget.update_status(i, "Done"))
        self.after(0, self._finish_queue)

    def _finish_queue(self) -> None:
        self._add_queue_btn.configure(state="normal")
        self._generate_btn.configure(state="normal")
        self._status_label.configure(text="Hoàn tất hàng đợi.", text_color="#66BB6A")
        self._on_generation_complete()

    def _on_cancel_queue(self) -> None:
        self._cancel_event.set()

    def _on_retry_failed(self) -> None:
        failed = self._queue_widget.failed_indices()
        if not failed:
            return
        voice_id = self._current_voice_id()
        client = self._get_client()
        if voice_id is None or client is None:
            return
        lines_raw = self._text_box.get("1.0", "end-1c")
        lines = [line.strip() for line in lines_raw.split("\n") if line.strip()]
        self._cancel_event.clear()

        def worker() -> None:
            for index in failed:
                if index >= len(lines):
                    continue
                self.after(0, lambda i=index: self._queue_widget.update_status(i, "Generating"))
                result_path, error = self._generate_one(client, lines[index], voice_id, index)
                status = "Failed" if error else "Done"
                self.after(0, lambda i=index, s=status, e=error: self._queue_widget.update_status(i, s, e))
            self.after(0, self._finish_queue)

        threading.Thread(target=worker, daemon=True).start()

    # ------------------------------------------------------------------ #
    def _generate_one(
        self, client: GeminiTTSClient, text: str, voice_id: str, index: int
    ) -> tuple[Optional[str], Optional[str]]:
        """Runs on a background thread. Returns (output_path, error_message)."""
        params = self._current_params()
        output_format = self._format_var.get()
        output_folder = self._output_folder_var.get() or self._settings.output_folder
        utils.ensure_directory(output_folder)

        cache_key = self._cache.make_key(text, voice_id, params)
        cached_path = self._cache.get(cache_key)
        api_time = 0.0
        from_cache = cached_path is not None

        try:
            if cached_path:
                wav_bytes = Path(cached_path).read_bytes()
                logger.info("Dùng cache cho đoạn text #%d", index + 1)
            else:
                wav_bytes, api_time = client.generate_speech(text, voice_id, params)
                self._cache.put(cache_key, wav_bytes)
                logger.success("Đã tạo audio thành công cho đoạn text #%d", index + 1)  # type: ignore[attr-defined]
        except GeminiAPIError as exc:
            logger.error("Lỗi tạo audio đoạn #%d: %s", index + 1, exc)
            return None, str(exc)

        filename = utils.generate_output_filename(output_format)
        final_path = str(Path(output_folder) / filename)

        if output_format == "wav":
            Path(final_path).write_bytes(wav_bytes)
        else:
            tmp_wav = str(Path(output_folder) / f"_tmp_{filename}.wav")
            Path(tmp_wav).write_bytes(wav_bytes)
            success = utils.convert_audio(tmp_wav, final_path, output_format)
            Path(tmp_wav).unlink(missing_ok=True)
            if not success:
                return None, "Chuyển đổi định dạng thất bại (kiểm tra ffmpeg)."

        voice = self._voice_repo.get(voice_id)
        entry = HistoryEntry.now(
            voice_id=voice_id,
            voice_name=voice.name if voice else voice_id,
            prompt_template=self._template_var.get(),
            text=text,
            duration_seconds=utils.estimate_duration_seconds(text, params.speed),
            output_path=final_path,
            api_time_seconds=round(api_time, 2),
        )
        self._history_repo.add(entry)
        self._last_output_path = final_path
        return final_path, None
