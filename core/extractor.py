"""
Module trích xuất văn bản từ các định dạng file khác nhau:
Hỗ trợ .txt, .md, .pdf, .docx, .epub
"""

import os
from pathlib import Path
from typing import Optional


def extract_from_txt(file_path: str) -> str:
    """Đọc file text thuần hoặc markdown với tự động phát hiện encoding."""
    encodings = ["utf-8", "utf-8-sig", "utf-16", "cp1258", "windows-1252"]
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    # Fallback with ignore errors
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def extract_from_docx(file_path: str) -> str:
    """Trích xuất toàn bộ văn bản từ file Word .docx."""
    import docx

    doc = docx.Document(file_path)
    paragraphs = []
    for p in doc.paragraphs:
        text = p.text.strip()
        if text:
            paragraphs.append(text)
    return "\n\n".join(paragraphs)


def extract_from_pdf(file_path: str) -> str:
    """Trích xuất văn bản từ file PDF."""
    from pypdf import PdfReader

    reader = PdfReader(file_path)
    pages_text = []
    for idx, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            pages_text.append(text)
    return "\n\n".join(pages_text)


def extract_from_epub(file_path: str) -> str:
    """Trích xuất văn bản từ sách điện tử .epub."""
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup
    import warnings

    # Ẩn warning của ebooklib liên quan tới XML namespaces
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        book = epub.read_epub(file_path)

    chapters_text = []
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            soup = BeautifulSoup(item.get_content(), "html.parser")
            # Xóa các thẻ script và style nếu có
            for tag in soup(["script", "style"]):
                tag.decompose()
            text = soup.get_text(separator="\n").strip()
            if text:
                chapters_text.append(text)
    return "\n\n".join(chapters_text)


def extract_text(file_path: str) -> str:
    """
    Hàm tổng quát nhận diện đuôi file và gọi parser tương ứng.
    Trả về nội dung văn bản dưới dạng chuỗi đã dọn dẹp sơ bộ.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Không tìm thấy file: {file_path}")

    ext = path.suffix.lower()
    if ext in [".txt", ".md", ".text"]:
        content = extract_from_txt(file_path)
    elif ext == ".docx":
        content = extract_from_docx(file_path)
    elif ext == ".pdf":
        content = extract_from_pdf(file_path)
    elif ext == ".epub":
        content = extract_from_epub(file_path)
    else:
        # Thử đọc như file text mặc định
        content = extract_from_txt(file_path)

    # Chuẩn hóa khoảng trắng và dòng trống
    lines = [line.strip() for line in content.splitlines()]
    # Ghép lại với tối đa 2 dòng trống liên tiếp
    cleaned_paragraphs = []
    buffer = []
    for line in lines:
        if line:
            buffer.append(line)
        else:
            if buffer:
                cleaned_paragraphs.append(" ".join(buffer))
                buffer = []
    if buffer:
        cleaned_paragraphs.append(" ".join(buffer))

    return "\n\n".join(cleaned_paragraphs)
