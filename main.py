"""
Audiobook Studio - Main Application Launcher
Khởi động ứng dụng tạo sách nói và chuyển đổi tài liệu sang âm thanh.
"""

import sys
import os
from pathlib import Path

# Đảm bảo mã hóa UTF-8 trên Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    # Sửa lỗi Tcl/Tk trên môi trường ảo venv Windows
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

# Đảm bảo đường dẫn gốc của dự án được thêm vào sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Tạo các thư mục cần thiết nếu chưa có
(BASE_DIR / "output").mkdir(exist_ok=True)
(BASE_DIR / "temp_chunks").mkdir(exist_ok=True)

from ui.app import main

if __name__ == "__main__":
    main()
