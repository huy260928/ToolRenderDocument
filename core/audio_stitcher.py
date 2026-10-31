"""
Module ghép nối âm thanh sử dụng FFmpeg binary (qua imageio-ffmpeg)
và quản lý checkpoint lưu tiến độ render sách nói.
"""

import os
import json
import subprocess
from pathlib import Path
from typing import List, Optional
import imageio_ffmpeg


def get_ffmpeg_binary() -> str:
    """Lấy đường dẫn file thực thi ffmpeg đã nhúng kèm."""
    try:
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:
        # Thử tìm trong PATH hệ thống
        import shutil
        which_ffmpeg = shutil.which("ffmpeg")
        if which_ffmpeg:
            return which_ffmpeg
        raise RuntimeError(f"Không tìm thấy FFmpeg binary: {e}")


def concatenate_audio_files(
    audio_files: List[str],
    output_path: str,
    cleanup_temp_list: bool = True
) -> bool:
    """
    Ghép danh sách các file MP3 thành một file duy nhất sử dụng FFmpeg concat demuxer.
    Tốc độ cực nhanh vì sử dụng stream copy (-c copy), không làm giảm chất lượng âm thanh.
    """
    if not audio_files:
        raise ValueError("Danh sách file âm thanh trống.")

    if len(audio_files) == 1:
        # Nếu chỉ có 1 file, chỉ cần copy hoặc đổi tên
        import shutil
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(audio_files[0], output_path)
        return True

    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    list_file_path = output_dir / f"concat_list_{os.getpid()}.txt"

    try:
        # Tạo file danh sách cho ffmpeg concat demuxer
        with open(list_file_path, "w", encoding="utf-8") as f:
            for file_p in audio_files:
                # Chuẩn hóa đường dẫn tương thích FFmpeg
                abs_path = Path(file_p).resolve().as_posix()
                f.write(f"file '{abs_path}'\n")

        ffmpeg_exe = get_ffmpeg_binary()

        # Lệnh FFmpeg ghép nối
        cmd = [
            ffmpeg_exe,
            "-y",                   # Tự động ghi đè nếu file đích đã tồn tại
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file_path),
            "-c", "copy",           # Stream copy siêu tốc
            output_path
        ]

        # Chạy lệnh FFmpeg ẩn cửa sổ đen trên Windows
        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # SW_HIDE

        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=startupinfo,
            check=True
        )

        return Path(output_path).is_file() and Path(output_path).stat().st_size > 0

    except subprocess.CalledProcessError as e:
        stderr_msg = e.stderr.decode("utf-8", errors="ignore") if e.stderr else str(e)
        # Fallback ghép nối binary trực tiếp (cho MP3 frames) nếu FFmpeg gặp lỗi
        return _fallback_concat_mp3(audio_files, output_path)

    finally:
        if cleanup_temp_list and list_file_path.is_file():
            try:
                list_file_path.unlink()
            except Exception:
                pass


def _fallback_concat_mp3(audio_files: List[str], output_path: str) -> bool:
    """Phương án dự phòng ghép thô binary MP3 nếu ffmpeg gặp lỗi."""
    try:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as outfile:
            for f in audio_files:
                with open(f, "rb") as infile:
                    outfile.write(infile.read())
        return True
    except Exception as e:
        raise RuntimeError(f"Lỗi khi ghép audio bằng phương án dự phòng: {e}")


def save_checkpoint(job_dir: str, data: dict):
    """Lưu tiến độ render vào file manifest.json để hỗ trợ resume."""
    Path(job_dir).mkdir(parents=True, exist_ok=True)
    manifest_path = Path(job_dir) / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_checkpoint(job_dir: str) -> Optional[dict]:
    """Tải tiến độ đã lưu từ file manifest.json nếu có."""
    manifest_path = Path(job_dir) / "manifest.json"
    if manifest_path.is_file():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None
