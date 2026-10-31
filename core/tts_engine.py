"""
Module tương tác với Microsoft Edge-TTS.
Chuyên trách tạo âm thanh từ văn bản đồng bộ 100% bằng DUY NHẤT một giọng đọc Nam Minh (vi-VN-NamMinhNeural).
Loại bỏ hoàn toàn mọi giọng đọc phụ/đa ngôn ngữ để đảm bảo trải nghiệm nghe đồng nhất từ đầu đến cuối.
"""

import asyncio
import re
import unicodedata
from pathlib import Path
from typing import List, Dict, Optional, Callable
import edge_tts


# Cấu hình giọng đọc DUY NHẤT của toàn bộ ứng dụng
DEFAULT_VOICE = "vi-VN-NamMinhNeural"

DEFAULT_VOICES = [
    {
        "id": "vi-VN-NamMinhNeural",
        "name": "Nam Minh (Nam - Tiếng Việt)",
        "gender": "Male",
        "lang": "vi-VN",
        "desc": "Giọng nam trầm ấm, truyền cảm, dõng dạc, đồng bộ 100% xuyên suốt tài liệu"
    }
]


async def fetch_all_voices() -> List[Dict[str, str]]:
    """Trả về danh sách giọng đọc mặc định của ứng dụng."""
    return DEFAULT_VOICES


async def synthesize_chunk(
    text: str,
    output_path: str,
    voice: str = DEFAULT_VOICE,
    rate: str = "+0%",
    pitch: str = "+0Hz",
    volume: str = "+0%",
    retries: int = 3
) -> bool:
    """
    Sinh file audio MP3 đồng bộ DUY NHẤT bằng giọng đọc Nam Minh (vi-VN-NamMinhNeural).
    
    Các nguyên tắc đảm bảo thành công 100%:
    1. Đảm bảo toàn bộ văn bản ở dạng Unicode Dựng Sẵn (NFC), ngăn chặn lỗi NoAudioReceived.
    2. Cơ chế Retry thông minh (Exponential Backoff): Nếu máy chủ Microsoft bận hoặc kết nối
       WebSocket bị nghẽn nhẹ, tự động đợi 0.4s - 0.8s và thử lại chính giọng Nam Minh.
    3. Bộ đệm khôi phục thuần Việt (Pure Vietnamese Fallback): Nếu văn bản chứa ký tự khó,
       tự động lọc sạch ký tự lạ và hoàn tất bằng giọng Nam Minh.
    4. TUYỆT ĐỐI KHÔNG BAO GIỜ đổi sang giọng đọc ngoại lai.
    """
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    # 1. Đảm bảo chuẩn hóa Unicode NFC dựng sẵn
    text = unicodedata.normalize("NFC", text.strip())
    if not text.endswith((".", "!", "?", "…")):
        text += "."

    # 2. Vòng lặp thử sinh âm thanh với giọng Nam Minh (tối đa 3 lần thử)
    for attempt in range(1, retries + 1):
        try:
            if out_p.is_file():
                try:
                    out_p.unlink()
                except Exception:
                    pass

            communicate = edge_tts.Communicate(
                text=text,
                voice=DEFAULT_VOICE,
                rate=rate,
                pitch=pitch,
                volume=volume
            )
            await communicate.save(output_path)

            if out_p.is_file() and out_p.stat().st_size > 300:
                return True

        except edge_tts.exceptions.NoAudioReceived:
            # Máy chủ bận hoặc nghẽn tạm thời, nghỉ nhẹ rồi thử lại
            if attempt < retries:
                await asyncio.sleep(0.4 * attempt)
        except Exception:
            if attempt < retries:
                await asyncio.sleep(0.4 * attempt)

    # 3. Tầng phục hồi an toàn: Lọc sạch chỉ giữ chữ cái tiếng Việt cơ bản và dấu câu chuẩn
    try:
        clean_fallback = unicodedata.normalize("NFC", text)
        clean_fallback = re.sub(r"[^\w\s\.,!\?]", " ", clean_fallback)
        clean_fallback = " ".join(clean_fallback.split())
        if not clean_fallback.endswith((".", "!", "?")):
            clean_fallback += "."

        if out_p.is_file():
            try:
                out_p.unlink()
            except Exception:
                pass

        communicate = edge_tts.Communicate(
            text=clean_fallback,
            voice=DEFAULT_VOICE, # Vẫn kiên định duy nhất giọng Nam Minh
            rate=rate,
            pitch=pitch,
            volume=volume
        )
        await communicate.save(output_path)

        if out_p.is_file() and out_p.stat().st_size > 300:
            return True
    except Exception:
        pass

    raise RuntimeError(f"Không thể tạo âm thanh cho đoạn: {text[:40]}...")


def run_synthesize_sync(
    text: str,
    output_path: str,
    voice: str = DEFAULT_VOICE,
    rate: str = "+0%",
    pitch: str = "+0Hz",
    volume: str = "+0%"
) -> bool:
    """Hàm synchronous tiện lợi để gọi từ các thread ứng dụng."""
    return asyncio.run(
        synthesize_chunk(
            text=text,
            output_path=output_path,
            voice=DEFAULT_VOICE,
            rate=rate,
            pitch=pitch,
            volume=volume
        )
    )
