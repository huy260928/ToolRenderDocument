"""
Module phát âm thanh tích hợp sử dụng pygame.mixer.
Hỗ trợ phát, tạm dừng, tiếp tục và dừng âm thanh trực tiếp trên giao diện ứng dụng.
"""

import os
from pathlib import Path

# Tắt thông báo chào mừng của pygame
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame


class SimpleAudioPlayer:
    """Trình phát âm thanh độc lập, nhẹ và an toàn đa luồng."""
    _initialized = False
    _is_paused = False

    @classmethod
    def _ensure_init(cls):
        if not cls._initialized:
            try:
                pygame.mixer.init()
                cls._initialized = True
            except Exception as e:
                print(f"Lỗi khởi tạo pygame mixer: {e}")

    @classmethod
    def play(cls, file_path: str):
        """Dừng âm thanh hiện tại và phát file âm thanh mới."""
        cls._ensure_init()
        if not Path(file_path).is_file():
            raise FileNotFoundError(f"Không tìm thấy file: {file_path}")

        try:
            cls.stop()
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            cls._is_paused = False
        except Exception as e:
            raise RuntimeError(f"Lỗi khi phát âm thanh: {e}")

    @classmethod
    def pause(cls):
        """Tạm dừng phát âm thanh."""
        cls._ensure_init()
        try:
            if pygame.mixer.music.get_busy() and not cls._is_paused:
                pygame.mixer.music.pause()
                cls._is_paused = True
        except Exception:
            pass

    @classmethod
    def unpause(cls):
        """Tiếp tục phát âm thanh sau khi tạm dừng."""
        cls._ensure_init()
        try:
            if cls._is_paused:
                pygame.mixer.music.unpause()
                cls._is_paused = False
        except Exception:
            pass

    @classmethod
    def stop(cls):
        """Dừng phát âm thanh và giải phóng file."""
        cls._ensure_init()
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
            cls._is_paused = False
        except Exception:
            pass

    @classmethod
    def is_playing(cls) -> bool:
        """Đang phát âm thanh và không ở trạng thái tạm dừng."""
        cls._ensure_init()
        try:
            return pygame.mixer.music.get_busy() and not cls._is_paused
        except Exception:
            return False

    @classmethod
    def is_paused(cls) -> bool:
        return cls._is_paused
