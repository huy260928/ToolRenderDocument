"""
Audiobook Studio - Giao diện Đọc Văn Bản & Nghe Trực Tiếp
Thiết kế tinh gọn, tập trung vào trải nghiệm: Nhập văn bản -> Bấm Đọc -> Nghe ngay trên App.
"""

import os
import sys
import threading
from pathlib import Path

# Sửa lỗi Tcl/Tk trên Windows venv trước khi load tkinter
if sys.platform == "win32":
    base_prefix = getattr(sys, "base_prefix", sys.prefix)
    tcl_candidates = [
        os.path.join(base_prefix, "tcl", "tcl8.6"),
        os.path.join(sys.prefix, "tcl", "tcl8.6"),
        os.path.join(base_prefix, "lib", "tcl8.6"),
    ]
    tk_candidates = [
        os.path.join(base_prefix, "tcl", "tk8.6"),
        os.path.join(sys.prefix, "tcl", "tk8.6"),
        os.path.join(base_prefix, "lib", "tk8.6"),
    ]
    for p in tcl_candidates:
        if os.path.isdir(p):
            os.environ["TCL_LIBRARY"] = p
            break
    for p in tk_candidates:
        if os.path.isdir(p):
            os.environ["TK_LIBRARY"] = p
            break

import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from core.extractor import extract_text
from core.tts_engine import DEFAULT_VOICES
from core.stream_player import StreamingAudioPlayer


# Cấu hình giao diện ban đầu
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class VoiceReaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Cấu hình cửa sổ chính
        self.title("TTS Voice Reader - Nghe Văn Bản Trực Tiếp")
        self.geometry("960x650")
        self.minsize(820, 540)

        # Trạng thái Streaming Player
        self.stream_player: StreamingAudioPlayer = None

        # Xây dựng giao diện
        self._build_header()
        self._build_main_layout()

        # Xử lý khi đóng cửa sổ
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_header(self):
        """Thanh tiêu đề trên cùng với nút chuyển giao diện."""
        header_frame = ctk.CTkFrame(self, corner_radius=0, height=60, fg_color=("gray88", "gray14"))
        header_frame.pack(fill="x", side="top")
        header_frame.pack_propagate(False)

        # Tiêu đề & phụ đề
        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left", padx=20, pady=8)

        title_lbl = ctk.CTkLabel(
            title_box,
            text="🎧 TTS VOICE READER",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_lbl.pack(anchor="w")

        sub_lbl = ctk.CTkLabel(
            title_box,
            text="Đọc văn bản và nghe trực tiếp trên ứng dụng (100% Miễn phí với Edge-TTS)",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray65")
        )
        sub_lbl.pack(anchor="w")

        # Nút chuyển Dark/Light mode
        mode_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        mode_box.pack(side="right", padx=20, pady=12)

        self.mode_switch = ctk.CTkSwitch(
            mode_box,
            text="Chế độ Tối",
            command=self._toggle_theme,
            onvalue="Dark",
            offvalue="Light"
        )
        self.mode_switch.select()
        self.mode_switch.pack()

    def _build_main_layout(self):
        """Bố cục chính: Khung văn bản ở trên, Thanh điều khiển phát âm thanh ở dưới."""
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=15, pady=12)

        # ==================== THANH CÔNG CỤ VĂN BẢN (TOOLBAR) ====================
        toolbar = ctk.CTkFrame(container, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, 6))

        # Nút Tải file
        btn_open = ctk.CTkButton(
            toolbar,
            text="📂 Tải File (.txt, .pdf, .docx, .epub)",
            width=210,
            height=32,
            command=self._browse_file
        )
        btn_open.pack(side="left", padx=(0, 8))

        # Nút Dán
        btn_paste = ctk.CTkButton(
            toolbar,
            text="📋 Dán",
            width=80,
            height=32,
            fg_color=("gray75", "gray28"),
            hover_color=("gray65", "gray35"),
            command=self._paste_clipboard
        )
        btn_paste.pack(side="left", padx=(0, 8))

        # Nút Xóa
        btn_clear = ctk.CTkButton(
            toolbar,
            text="🗑 Xóa trắng",
            width=90,
            height=32,
            fg_color=("gray75", "gray28"),
            hover_color=("gray65", "gray35"),
            command=self._clear_text
        )
        btn_clear.pack(side="left")

        # Thống kê số từ
        self.lbl_stats = ctk.CTkLabel(
            toolbar,
            text="0 từ | 0 ký tự | Ước tính: ~0 giây nghe",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray65")
        )
        self.lbl_stats.pack(side="right")

        # ==================== KHUNG NHẬP VĂN BẢN ====================
        self.txt_content = ctk.CTkTextbox(
            container,
            wrap="word",
            font=ctk.CTkFont(size=13),
            corner_radius=8
        )
        self.txt_content.pack(fill="both", expand=True, pady=(0, 12))
        self.txt_content.bind("<KeyRelease>", self._update_text_stats)

        # Đoạn văn bản mẫu ban đầu
        sample_intro = (
            "Xin chào! Đây là công cụ đọc văn bản trực tiếp.\n\n"
            "Bạn chỉ cần dán đoạn văn bản cần nghe vào đây, chọn giọng đọc yêu thích bên dưới, "
            "sau đó bấm nút [ĐỌC VĂN BẢN] để bắt đầu nghe ngay lập tức.\n\n"
            "Hệ thống hỗ trợ cả đọc nhanh các tài liệu PDF, Word, Ebook hoặc tin tức hàng ngày."
        )
        self.txt_content.insert("1.0", sample_intro)
        self._update_text_stats()

        # ==================== THANH ĐIỀU KHIỂN & PHÁT ÂM THANH ====================
        control_deck = ctk.CTkFrame(container, corner_radius=10, fg_color=("gray85", "gray17"))
        control_deck.pack(fill="x", pady=(0, 0))

        # Hàng 1: Cài đặt Giọng, Tốc độ, Cao độ
        settings_row = ctk.CTkFrame(control_deck, fg_color="transparent")
        settings_row.pack(fill="x", padx=16, pady=(12, 8))

        # Giọng đọc mặc định duy nhất: Nam Minh (tối ưu tốc độ, không bao giờ timeout)
        voice_box = ctk.CTkFrame(settings_row, fg_color="transparent")
        voice_box.pack(side="left", padx=(0, 20))
        ctk.CTkLabel(voice_box, text="Giọng đọc:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")

        self.voice_badge = ctk.CTkLabel(
            voice_box,
            text="🎙 Nam Minh (Nam - Chuẩn Tiếng Việt)",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("gray78", "gray25"),
            text_color=("gray10", "gray95"),
            corner_radius=6,
            width=230,
            height=32
        )
        self.voice_badge.pack(anchor="w", pady=(2, 0))

        # Slider Tốc độ đọc
        rate_box = ctk.CTkFrame(settings_row, fg_color="transparent")
        rate_box.pack(side="left", fill="x", expand=True, padx=(0, 20))

        rate_lbl_frame = ctk.CTkFrame(rate_box, fg_color="transparent")
        rate_lbl_frame.pack(fill="x")
        ctk.CTkLabel(rate_lbl_frame, text="Tốc độ:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
        self.lbl_rate_val = ctk.CTkLabel(rate_lbl_frame, text="+0%", font=ctk.CTkFont(size=12, weight="bold"))
        self.lbl_rate_val.pack(side="right")

        self.slider_rate = ctk.CTkSlider(
            rate_box,
            from_=-30,
            to=40,
            number_of_steps=14,
            command=self._on_rate_change
        )
        self.slider_rate.set(0)
        self.slider_rate.pack(fill="x", pady=(4, 0))

        # Slider Cao độ giọng
        pitch_box = ctk.CTkFrame(settings_row, fg_color="transparent")
        pitch_box.pack(side="left", fill="x", expand=True)

        pitch_lbl_frame = ctk.CTkFrame(pitch_box, fg_color="transparent")
        pitch_lbl_frame.pack(fill="x")
        ctk.CTkLabel(pitch_lbl_frame, text="Cao độ (Pitch):", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
        self.lbl_pitch_val = ctk.CTkLabel(pitch_lbl_frame, text="+0Hz", font=ctk.CTkFont(size=12, weight="bold"))
        self.lbl_pitch_val.pack(side="right")

        self.slider_pitch = ctk.CTkSlider(
            pitch_box,
            from_=-20,
            to=20,
            number_of_steps=10,
            command=self._on_pitch_change
        )
        self.slider_pitch.set(0)
        self.slider_pitch.pack(fill="x", pady=(4, 0))

        # Hàng 2: Trạng thái & Các nút bấm điều khiển Play/Pause/Stop
        playback_row = ctk.CTkFrame(control_deck, fg_color="transparent")
        playback_row.pack(fill="x", padx=16, pady=(4, 14))

        # Nhãn trạng thái phát
        self.lbl_status = ctk.CTkLabel(
            playback_row,
            text="● Sẵn sàng",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("gray40", "gray70")
        )
        self.lbl_status.pack(side="left")

        # Cụm nút Play / Stop bên phải
        btn_box = ctk.CTkFrame(playback_row, fg_color="transparent")
        btn_box.pack(side="right")

        self.btn_play = ctk.CTkButton(
            btn_box,
            text="▶ ĐỌC VĂN BẢN (NGHE NGAY)",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#1f6aa5",
            hover_color="#144870",
            width=230,
            height=38,
            command=self._toggle_play_pause
        )
        self.btn_play.pack(side="left", padx=(0, 10))

        self.btn_stop = ctk.CTkButton(
            btn_box,
            text="⏹ DỪNG LẠI",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray38"),
            width=110,
            height=38,
            command=self._stop_playback,
            state="disabled"
        )
        self.btn_stop.pack(side="left")

    # ==================== XỬ LÝ SỰ KIỆN GIAO DIỆN ====================

    def _toggle_theme(self):
        mode = self.mode_switch.get()
        ctk.set_appearance_mode(mode)

    def _on_rate_change(self, value):
        val_int = int(value)
        sign = "+" if val_int >= 0 else ""
        self.lbl_rate_val.configure(text=f"{sign}{val_int}%")

    def _on_pitch_change(self, value):
        val_int = int(value)
        sign = "+" if val_int >= 0 else ""
        self.lbl_pitch_val.configure(text=f"{sign}{val_int}Hz")

    def _update_text_stats(self, event=None):
        text = self.txt_content.get("1.0", "end-1c").strip()
        words = len(text.split()) if text else 0
        chars = len(text)
        est_sec = round(words / 2.5)
        if est_sec >= 60:
            est_str = f"~{round(est_sec / 60, 1)} phút"
        else:
            est_str = f"~{est_sec} giây"
        self.lbl_stats.configure(text=f"{words:,} từ | {chars:,} ký tự | Ước tính: {est_str} nghe")

    def _browse_file(self):
        filetypes = [
            ("Tất cả tài liệu", "*.txt;*.md;*.pdf;*.docx;*.epub"),
            ("Text files", "*.txt;*.md"),
            ("PDF files", "*.pdf"),
            ("Word files", "*.docx"),
            ("Ebook EPUB", "*.epub")
        ]
        filename = filedialog.askopenfilename(title="Chọn file văn bản cần nghe", filetypes=filetypes)
        if not filename:
            return

        file_path = Path(filename)
        self.lbl_status.configure(text=f"Đang đọc file: {file_path.name}...", text_color="#1f6aa5")

        def load_task():
            try:
                content = extract_text(str(file_path))
                self.after(0, lambda: self._set_content(content, file_path.name))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Lỗi mở file", f"Không thể trích xuất nội dung: {e}"))
                self.after(0, lambda: self.lbl_status.configure(text="● Sẵn sàng", text_color=("gray40", "gray70")))

        threading.Thread(target=load_task, daemon=True).start()

    def _set_content(self, content: str, filename: str):
        self._stop_playback()
        self.txt_content.delete("1.0", "end")
        self.txt_content.insert("1.0", content)
        self._update_text_stats()
        self.lbl_status.configure(text=f"● Đã tải xong: {filename}", text_color="#2da44e")

    def _paste_clipboard(self):
        try:
            clip = self.clipboard_get()
            if clip:
                self.txt_content.insert("insert", clip)
                self._update_text_stats()
        except Exception:
            pass

    def _clear_text(self):
        self._stop_playback()
        self.txt_content.delete("1.0", "end")
        self._update_text_stats()
        self.lbl_status.configure(text="● Đã xóa trắng", text_color=("gray40", "gray70"))

    # ==================== ĐIỀU KHIỂN PHÁT ÂM THANH STREAMING ====================

    def _toggle_play_pause(self):
        """Xử lý nút Đọc / Tạm dừng / Tiếp tục."""
        # 1. Nếu đang có stream đang chạy
        if self.stream_player and self.stream_player.is_running:
            if not self.stream_player.is_paused():
                # Tạm dừng
                self.stream_player.pause()
                self.btn_play.configure(text="▶ TIẾP TỤC NGHE", fg_color="#1f6aa5")
                self.lbl_status.configure(text="⏸ Đang tạm dừng", text_color="#d97706")
            else:
                # Tiếp tục phát
                self.stream_player.unpause()
                self.btn_play.configure(text="⏸ TẠM DỪNG", fg_color="#d97706")
                self.lbl_status.configure(text="🔊 Đang phát âm thanh...", text_color="#2da44e")
            return

        # 2. Bắt đầu phát mới
        content = self.txt_content.get("1.0", "end-1c").strip()
        if not content:
            messagebox.showwarning("Văn bản trống", "Vui lòng nhập hoặc dán nội dung văn bản để nghe!")
            return

        voice_id = "vi-VN-NamMinhNeural"
        rate_str = self.lbl_rate_val.cget("text")
        pitch_str = self.lbl_pitch_val.cget("text")

        self.btn_play.configure(text="⏸ TẠM DỪNG", fg_color="#d97706")
        self.btn_stop.configure(state="normal")
        self.lbl_status.configure(text="⏳ Đang chuẩn bị âm thanh...", text_color="#1f6aa5")

        try:
            self.stream_player = StreamingAudioPlayer(
                text=content,
                voice=voice_id,
                rate=rate_str,
                pitch=pitch_str,
                on_status=lambda msg: self.after(0, lambda: self._update_player_status(msg)),
                on_completed=lambda: self.after(0, self._on_stream_completed)
            )
            self.stream_player.start()
        except Exception as e:
            messagebox.showerror("Lỗi", str(e))
            self._stop_playback()

    def _update_player_status(self, msg: str):
        color = "#2da44e" if "Đang phát" in msg else ("#1f6aa5" if "chuẩn bị" in msg else ("gray40", "gray70"))
        self.lbl_status.configure(text=msg, text_color=color)

    def _on_stream_completed(self):
        self.btn_play.configure(text="▶ ĐỌC VĂN BẢN (NGHE NGAY)", fg_color="#1f6aa5")
        self.btn_stop.configure(state="disabled")
        self.lbl_status.configure(text="● Đã đọc xong toàn bộ văn bản", text_color="#2da44e")

    def _stop_playback(self):
        """Dừng hẳn phát âm thanh."""
        if self.stream_player:
            self.stream_player.stop()
            self.stream_player = None

        self.btn_play.configure(state="normal", text="▶ ĐỌC VĂN BẢN (NGHE NGAY)", fg_color="#1f6aa5")
        self.btn_stop.configure(state="disabled")
        self.lbl_status.configure(text="● Đã dừng", text_color=("gray40", "gray70"))

    def _on_close(self):
        """Dừng âm thanh và đóng app."""
        if self.stream_player:
            self.stream_player.stop()
        self.destroy()


def main():
    app = VoiceReaderApp()
    app.mainloop()


if __name__ == "__main__":
    main()
