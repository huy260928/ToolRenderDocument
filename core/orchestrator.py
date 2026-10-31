"""
Bộ điều phối tiến trình render sách nói (Orchestrator).
Chạy ngầm (background thread), quản lý hàng đợi chunk, cập nhật tiến độ UI,
hỗ trợ Resume khi gián đoạn và ghép nối thành phẩm.
"""

import os
import time
import threading
from pathlib import Path
from typing import Callable, Optional, List, Dict, Any

from core.normalizer import normalize_text_for_tts
from core.chunker import create_chunks
from core.tts_engine import run_synthesize_sync
from core.audio_stitcher import concatenate_audio_files, save_checkpoint, load_checkpoint


class AudiobookOrchestrator:
    def __init__(
        self,
        text: str,
        output_filepath: str,
        voice_id: str = "vi-VN-NamMinhNeural",
        rate: str = "+0%",
        pitch: str = "+0Hz",
        on_progress: Optional[Callable[[float, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None,
        on_finished: Optional[Callable[[bool, str], None]] = None
    ):
        self.raw_text = text
        self.output_filepath = Path(output_filepath).resolve()
        self.voice_id = voice_id
        self.rate = rate
        self.pitch = pitch
        self.on_progress = on_progress
        self.on_log = on_log
        self.on_finished = on_finished

        self.cancel_event = threading.Event()
        self.is_running = False

    def log(self, message: str):
        if self.on_log:
            self.on_log(message)

    def progress(self, val: float, msg: str):
        if self.on_progress:
            self.on_progress(val, msg)

    def stop(self):
        """Yêu cầu dừng tiến trình đang chạy."""
        self.cancel_event.set()

    def run(self):
        """Hàm thực thi chính chạy trong thread."""
        self.is_running = True
        self.cancel_event.clear()

        try:
            self.log("🚀 Bắt đầu quá trình tạo sách nói...")
            self.progress(0.02, "Đang chuẩn hóa văn bản...")

            # 1. Chuẩn hóa ngôn ngữ
            clean_text = normalize_text_for_tts(self.raw_text)
            if not clean_text:
                raise ValueError("Nội dung văn bản trống sau khi chuẩn hóa.")

            # 2. Chia đoạn thông minh
            self.progress(0.05, "Đang phân tích cấu trúc câu và chia đoạn...")
            chunks = create_chunks(clean_text, max_words=200, min_words=60)
            total_chunks = len(chunks)

            total_words = sum(c["word_count"] for c in chunks)
            est_total_min = round(total_words / 150, 1)
            self.log(f"📊 Thống kê: {total_words:,} từ | {total_chunks} đoạn | Thời lượng ước tính: ~{est_total_min} phút.")

            # 3. Tạo thư mục làm việc tạm thời
            job_slug = self.output_filepath.stem
            temp_dir = self.output_filepath.parent / "temp_chunks" / job_slug
            temp_dir.mkdir(parents=True, exist_ok=True)

            # 4. Kiểm tra Checkpoint (Resume)
            manifest = load_checkpoint(str(temp_dir))
            completed_indices = set(manifest.get("completed", [])) if manifest else set()
            if completed_indices:
                self.log(f"🔄 Tìm thấy tiến độ đã lưu trước đó: Đã hoàn thành {len(completed_indices)}/{total_chunks} đoạn. Tiếp tục render...")

            chunk_files = []

            # 5. Vòng lặp render từng chunk
            for idx, chunk in enumerate(chunks):
                if self.cancel_event.is_set():
                    self.log("⏹ Người dùng đã hủy hoặc tạm dừng tiến trình.")
                    save_checkpoint(str(temp_dir), {
                        "total": total_chunks,
                        "completed": list(completed_indices),
                        "voice": self.voice_id
                    })
                    if self.on_finished:
                        self.on_finished(False, "Tiến trình đã bị dừng.")
                    return

                chunk_filename = temp_dir / f"chunk_{idx:04d}.mp3"
                chunk_files.append(str(chunk_filename))

                # Nếu chunk đã được render trước đó và tồn tại file hợp lệ -> bỏ qua
                if idx in completed_indices and chunk_filename.is_file() and chunk_filename.stat().st_size > 0:
                    curr_prog = 0.05 + 0.85 * ((idx + 1) / total_chunks)
                    self.progress(curr_prog, f"Đoạn {idx + 1}/{total_chunks} đã có sẵn (khôi phục từ cache).")
                    continue

                # Cập nhật thông tin đoạn đang render
                curr_prog = 0.05 + 0.85 * (idx / total_chunks)
                self.progress(curr_prog, f"Đang render đoạn {idx + 1}/{total_chunks} ({chunk['word_count']} từ)...")

                # Gọi Edge-TTS
                success = run_synthesize_sync(
                    text=chunk["text"],
                    output_path=str(chunk_filename),
                    voice=self.voice_id,
                    rate=self.rate,
                    pitch=self.pitch
                )

                if not success:
                    raise RuntimeError(f"Không thể render đoạn {idx + 1}")

                completed_indices.add(idx)
                save_checkpoint(str(temp_dir), {
                    "total": total_chunks,
                    "completed": list(completed_indices),
                    "voice": self.voice_id
                })

                # Khoảng nghỉ ổn định giữa các chunk để tránh bị Edge-TTS rate limit
                time.sleep(2.0)

            # 6. Ghép nối âm thanh
            self.progress(0.92, "Đang ghép nối các đoạn âm thanh thành file hoàn chỉnh...")
            self.log("🎵 Đang ghép nối âm thanh siêu tốc bằng FFmpeg...")

            concat_ok = concatenate_audio_files(chunk_files, str(self.output_filepath))
            if not concat_ok:
                raise RuntimeError("Lỗi trong quá trình ghép nối file âm thanh cuối cùng.")

            # 7. Hoàn tất
            self.progress(1.0, "Tạo sách nói thành công 100%!")
            file_size_mb = round(self.output_filepath.stat().st_size / (1024 * 1024), 2)
            self.log(f"🎉 THÀNH CÔNG! File hoàn tất: {self.output_filepath.name} ({file_size_mb} MB)")
            self.log(f"📁 Vị trí lưu: {self.output_filepath}")

            if self.on_finished:
                self.on_finished(True, str(self.output_filepath))

        except Exception as e:
            err_msg = f"Lỗi xảy ra trong quá trình xử lý: {e}"
            self.log(f"❌ {err_msg}")
            self.progress(0.0, "Đã xảy ra lỗi.")
            if self.on_finished:
                self.on_finished(False, err_msg)
        finally:
            self.is_running = False
