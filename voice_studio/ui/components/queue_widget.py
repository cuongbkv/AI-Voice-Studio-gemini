"""
ui/components/queue_widget.py
==============================
Displays a scrollable list of queued generation jobs with per-item status
(Pending / Generating / Done / Failed), plus overall progress bar and
Cancel / Retry controls. Pure display + local state; the actual generation
work is driven by generate_voice.py, which calls back into this widget to
update statuses.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import customtkinter as ctk

STATUS_COLORS = {
    "Pending": "#9E9E9E",
    "Generating": "#4FC3F7",
    "Done": "#66BB6A",
    "Failed": "#EF5350",
    "Cancelled": "#FFA726",
}


@dataclass
class QueueItem:
    index: int
    text_preview: str
    status: str = "Pending"
    error: Optional[str] = None


class QueueWidget(ctk.CTkFrame):
    """Batch queue list + progress bar + cancel/retry controls."""

    def __init__(
        self,
        master,
        on_cancel: Callable[[], None],
        on_retry_failed: Callable[[], None],
    ) -> None:
        super().__init__(master, corner_radius=10)
        self._on_cancel = on_cancel
        self._on_retry_failed = on_retry_failed
        self._items: list[QueueItem] = []
        self._row_labels: dict[int, ctk.CTkLabel] = {}

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(header, text="Hàng đợi (Queue)", font=ctk.CTkFont(weight="bold")).pack(
            side="left"
        )

        self._progress_bar = ctk.CTkProgressBar(self)
        self._progress_bar.set(0)
        self._progress_bar.pack(fill="x", padx=10, pady=(0, 6))

        self._progress_label = ctk.CTkLabel(self, text="0 / 0 hoàn thành")
        self._progress_label.pack(anchor="w", padx=10)

        self._scroll_frame = ctk.CTkScrollableFrame(self, height=180)
        self._scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkButton(
            btn_frame, text="Cancel", fg_color="#B23B3B", hover_color="#8C2E2E",
            command=self._on_cancel, width=90,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            btn_frame, text="Retry Failed", fg_color="transparent", border_width=1,
            command=self._on_retry_failed, width=110,
        ).pack(side="left")

    # ------------------------------------------------------------------ #
    def set_items(self, texts: list[str]) -> None:
        """Reset the queue with a fresh list of texts (one job per text)."""
        for widget in self._scroll_frame.winfo_children():
            widget.destroy()
        self._row_labels.clear()

        self._items = [
            QueueItem(index=i, text_preview=(t[:50] + "…") if len(t) > 50 else t)
            for i, t in enumerate(texts)
        ]

        for item in self._items:
            row = ctk.CTkFrame(self._scroll_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            row.grid_columnconfigure(0, weight=1)

            text_lbl = ctk.CTkLabel(
                row, text=f"{item.index + 1}. {item.text_preview}", anchor="w"
            )
            text_lbl.grid(row=0, column=0, sticky="ew")

            status_lbl = ctk.CTkLabel(
                row, text=item.status, text_color=STATUS_COLORS[item.status], width=90
            )
            status_lbl.grid(row=0, column=1, sticky="e")
            self._row_labels[item.index] = status_lbl

        self._update_progress()

    def update_status(self, index: int, status: str, error: Optional[str] = None) -> None:
        """Update one item's status (called from the generation worker thread
        via `.after()` to stay on the main thread)."""
        if index >= len(self._items):
            return
        self._items[index].status = status
        self._items[index].error = error
        label = self._row_labels.get(index)
        if label is not None:
            label.configure(text=status, text_color=STATUS_COLORS.get(status, "#9E9E9E"))
        self._update_progress()

    def _update_progress(self) -> None:
        total = len(self._items)
        done = sum(1 for i in self._items if i.status in ("Done", "Failed", "Cancelled"))
        self._progress_label.configure(text=f"{done} / {total} hoàn thành")
        self._progress_bar.set(done / total if total else 0)

    def failed_indices(self) -> list[int]:
        return [i.index for i in self._items if i.status == "Failed"]
