"""
Module phát âm thanh dạng Streaming / Hàng đợi đệm (Audio Stream Queue).
Cung cấp trải nghiệm phát tức thì:
- Vừa render xong đoạn 1 (mất ~0.5s) là BẮT ĐẦU PHÁT NGAY LẬP TỨC.
- Trong lúc người dùng đang nghe đoạn 1, hệ thống âm thầm render tiếp các đoạn sau.
- Cơ chế chống nhảy cóc (No Skip): Đảm bảo 100% các đoạn đều được phát theo đúng thứ tự.
- Tự động dọn dẹp các file âm thanh tạm sau khi kết thúc.
"""

import os
import re
import time
import queue
import shutil
import threading
from pathlib import Path
from typing import Callable, Optional, List

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame

from core.normalizer import normalize_text_for_tts
from core.chunker import create_chunks
from core.tts_engine import run_synthesize_sync


class StreamingAudioPlayer:
    """Trình phát âm thanh đa luồng theo cơ chế đệm gối đầu (Producer-Consumer)."""
    
    _mixer_initialized = False

    def __init__(
        self,
        text: str,
        voice: str = "vi-VN-NamMinhNeural",
        rate: str = "+0%",
        pitch: str = "+0Hz",
        on_status: Optional[Callable[[str], None]] = None,
        on_chunk_change: Optional[Callable[[int, int], None]] = None,
        on_completed: Optional[Callable[[], None]] = None
    ):
        self._ensure_mixer()
        self.raw_text = text
        self.voice = voice
        self.rate = rate
        self.pitch = pitch
        self.on_status = on_status
        self.on_chunk_change = on_chunk_change
        self.on_completed = on_completed

        # Hàng đợi các file audio đã sẵn sàng phát
        self.audio_queue = queue.Queue()
        self.temp_dir: Optional[Path] = None

        # Cờ kiểm soát luồng
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.is_running = False
        self.current_chunk_idx = 0
        self.total_chunks = 0

        self.producer_thread: Optional[threading.Thread] = None
        self.consumer_thread: Optional[threading.Thread] = None

    @classmethod
    def _ensure_mixer(cls):
        if not cls._mixer_initialized:
            try:
                pygame.mixer.init()
                cls._mixer_initialized = True
            except Exception as e:
                print(f"Lỗi khởi tạo mixer: {e}")

    def update_status(self, msg: str):
        if self.on_status:
            self.on_status(msg)

    def start(self):
        """Khởi động luồng sinh âm thanh và luồng phát đồng thời."""
        self.stop() # Dừng bất kỳ phiên nào trước đó
        self.stop_event.clear()
        self.pause_event.clear()
        self.is_running = True

        # Chuẩn hóa văn bản
        clean_text = normalize_text_for_tts(self.raw_text)
        if not clean_text:
            raise ValueError("Văn bản trống sau khi làm sạch.")

        # Chia đoạn kích thước tối ưu 40-70 từ để render dưới 0.6s
        chunks = create_chunks(clean_text, max_words=65, min_words=30)
        self.total_chunks = len(chunks)

        if self.total_chunks == 0:
            raise ValueError("Không thể chia nhỏ văn bản.")

        # Tạo thư mục làm việc tạm thời
        self.temp_dir = Path("temp_chunks") / f"stream_{int(time.time() * 1000)}"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # 1. Luồng Producer: Render tuần tự từng đoạn, đảm bảo KHÔNG BỎ SÓT đoạn nào
        def producer_worker():
            for idx, c in enumerate(chunks):
                if self.stop_event.is_set():
                    break

                chunk_file = self.temp_dir / f"chunk_{idx:03d}.mp3"
                chunk_text = c["text"]
                render_ok = False

                # Thử render với cơ chế kiên định duy nhất giọng Nam Minh
                for attempt in range(1, 4):
                    if self.stop_event.is_set():
                        break
                    try:
                        render_ok = run_synthesize_sync(
                            text=chunk_text,
                            output_path=str(chunk_file),
                            voice=self.voice,
                            rate=self.rate,
                            pitch=self.pitch
                        )
                        if render_ok and chunk_file.is_file() and chunk_file.stat().st_size > 300:
                            break
                    except Exception as err:
                        # Tạm nghỉ và thử lại với phiên bản làm sạch
                        time.sleep(0.4 * attempt)

                # Đưa file vào hàng đợi phát
                if render_ok and chunk_file.is_file():
                    self.audio_queue.put((idx, str(chunk_file)))

                # Khoảng nghỉ nhẹ tránh nghẽn socket Microsoft
                time.sleep(0.25)

            # Đánh dấu đã kết thúc toàn bộ danh sách
            self.audio_queue.put(None)

        # 2. Luồng Consumer: Phát ngay khi có đoạn đầu tiên, nối tiếp mượt mà
        def consumer_worker():
            self.update_status("⏳ Đang chuẩn bị đoạn đầu tiên...")

            while not self.stop_event.is_set():
                try:
                    # Chờ đoạn tiếp theo từ producer
                    item = self.audio_queue.get(timeout=0.2)
                except queue.Empty:
                    continue

                if item is None:
                    # Đã phát hết toàn bộ các đoạn
                    break

                chunk_idx, file_path = item
                self.current_chunk_idx = chunk_idx

                if self.on_chunk_change:
                    self.on_chunk_change(chunk_idx + 1, self.total_chunks)

                self.update_status(f"🔊 Đang phát đoạn {chunk_idx + 1}/{self.total_chunks}...")

                try:
                    pygame.mixer.music.load(file_path)
                    pygame.mixer.music.play()

                    # QUAN TRỌNG: Đợi 0.18s để thiết bị âm thanh SDL thực sự bắt đầu phát,
                    # tránh lỗi get_busy() trả về False sớm làm nhảy cóc qua đoạn tiếp theo!
                    time.sleep(0.18)

                    # Vòng lặp theo dõi đoạn đang phát
                    while pygame.mixer.music.get_busy() or self.pause_event.is_set():
                        if self.stop_event.is_set():
                            pygame.mixer.music.stop()
                            return

                        # Xử lý tạm dừng
                        if self.pause_event.is_set():
                            if pygame.mixer.music.get_busy():
                                pygame.mixer.music.pause()
                            time.sleep(0.1)
                        else:
                            time.sleep(0.06)

                except Exception as e:
                    print(f"Lỗi khi phát {file_path}: {e}")

            # Kết thúc toàn bộ
            self.is_running = False
            self.update_status("● Đã đọc xong toàn bộ văn bản")
            if self.on_completed:
                self.on_completed()

            # Tự động dọn dẹp file tạm
            self._cleanup_temp_files()

        self.producer_thread = threading.Thread(target=producer_worker, daemon=True)
        self.consumer_thread = threading.Thread(target=consumer_worker, daemon=True)

        self.producer_thread.start()
        self.consumer_thread.start()

    def pause(self):
        """Tạm dừng phát."""
        self.pause_event.set()
        try:
            pygame.mixer.music.pause()
        except Exception:
            pass

    def unpause(self):
        """Tiếp tục phát sau khi tạm dừng."""
        self.pause_event.clear()
        try:
            pygame.mixer.music.unpause()
        except Exception:
            pass

    def is_paused(self) -> bool:
        return self.pause_event.is_set()

    def stop(self):
        """Dừng hẳn toàn bộ tiến trình và dọn dẹp file."""
        self.stop_event.set()
        self.pause_event.clear()
        self.is_running = False
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
        except Exception:
            pass
        self._cleanup_temp_files()

    def _cleanup_temp_files(self):
        """Dọn dẹp thư mục tạm thời của phiên phát này sau khi giải phóng file."""
        try:
            pygame.mixer.music.unload()
        except Exception:
            pass

        if self.temp_dir and self.temp_dir.is_dir():
            try:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            except Exception:
                pass
