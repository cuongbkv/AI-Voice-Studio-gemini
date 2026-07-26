# AI Voice Studio

Công cụ desktop tạo giọng đọc AI bằng Google Gemini TTS API, dành cho người
sáng tạo nội dung TikTok / YouTube / Facebook.

## Kiến trúc

```
voice_studio/
├── app.py                    # Entry point, ghép nối UI + shared state
├── config.py                 # Đường dẫn, hằng số, AppSettings (settings.json)
├── utils.py                  # Đếm chữ/từ/câu, ước lượng thời lượng, convert ffmpeg
├── player.py                 # AudioPlayer (pygame.mixer) — play/pause/stop/seek/volume/loop
├── cache.py                  # Cache theo (text, voice, params) — tránh gọi API trùng lặp
├── logs.py                   # Logging có màu (INFO/SUCCESS/WARNING/ERROR) + hook vào UI
├── voice_repository.py       # Đọc voices.json, search/filter/sort/favorite
├── history_repository.py     # Đọc/ghi history.json
├── prompt_templates.py       # 12 prompt template dựng sẵn (có thể sửa trong UI)
├── voices.json               # 30 voice của Gemini TTS — SỬA FILE NÀY để thêm voice mới
├── settings.json             # Tự tạo khi chạy lần đầu — API key, theme, output folder...
├── api/
│   ├── models.py              # Voice, GenerationParams, GenerationResult, HistoryEntry
│   └── gemini.py              # GeminiTTSClient — lớp DUY NHẤT gọi Gemini TTS API
└── ui/
    ├── sidebar.py
    ├── pages/
    │   ├── dashboard.py
    │   ├── voice_library.py
    │   ├── generate_voice.py
    │   ├── history.py
    │   ├── settings.py
    │   └── about.py
    └── components/
        ├── voice_detail_panel.py
        ├── audio_player_widget.py
        └── queue_widget.py
```

**Thêm nhà cung cấp TTS mới (OpenAI, ElevenLabs, Azure)**: tạo file mới trong
`api/` (ví dụ `api/openai_tts.py`) với cùng chữ ký hàm
`generate_speech(text, voice_id, params) -> (bytes, float)` như
`GeminiTTSClient`. Không cần sửa bất kỳ file nào trong `ui/`.

**Thêm voice mới**: chỉ cần sửa `voices.json`, không cần sửa code.

## Cài đặt (Windows)

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Cài thêm **ffmpeg** và đảm bảo `ffmpeg.exe` có trong PATH nếu muốn xuất
mp3/flac/aac (xuất wav không cần ffmpeg). Tải tại https://ffmpeg.org/download.html

## Chạy thử

```powershell
python app.py
```

Vào **Settings** để nhập Gemini API Key (lấy tại https://aistudio.google.com/apikey),
sau đó có thể dùng đầy đủ Voice Library / Generate Voice / History.

## Đóng gói thành file .exe (bắt buộc chạy trên Windows)

PyInstaller build ra file thực thi cho đúng hệ điều hành mà nó đang chạy
trên đó — vì vậy để có file `.exe` cho Windows, bạn phải chạy lệnh build
**trên máy Windows** (không thể build .exe từ Linux/macOS).

```powershell
pip install pyinstaller
python build_exe.py
```

File `.exe` sẽ nằm ở `dist/AI Voice Studio.exe`. Nếu dùng định dạng xuất
mp3/flac/aac, hãy copy `ffmpeg.exe` vào cùng thư mục với file .exe (hoặc để
người dùng cuối tự cài ffmpeg và thêm vào PATH).

## Ghi chú kỹ thuật

- Toàn bộ việc gọi API và convert ffmpeg chạy trên background thread
  (`threading`), UI không bao giờ bị treo.
- Cache được lưu tại `cache/` theo hash của (text, voice, params) — nếu
  sinh lại đúng nội dung + voice + tham số, tool sẽ đọc cache thay vì gọi
  API lần nữa.
- History được lưu tại `history.json`, hiển thị đầy đủ ở trang History.
- Favorite được lưu trong `settings.json` (trường `favorites`).
- Preview không lưu file vĩnh viễn — chỉ ghi tạm ra thư mục temp của hệ
  điều hành để phát, đúng như yêu cầu "Preview... Không lưu file."
