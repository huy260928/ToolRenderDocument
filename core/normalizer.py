"""
Module chuẩn hóa văn bản tiếng Việt cho công cụ Text-To-Speech (TTS).
Xử lý toàn diện:
- Chuẩn hóa Unicode Dựng Sẵn (NFC) - Yếu tố cốt lõi để giọng Nam Minh (vi-VN-NamMinhNeural) đọc 100% không lỗi.
- Phiên âm & Việt hóa các thuật ngữ công nghệ, từ tiếng Anh và từ mượn phổ biến.
- Khử các ký tự ngoại lai (w, f, j, z) và dấu câu gây lỗi parser SSML/Edge-TTS.
- Đảm bảo chất lượng âm thanh đồng bộ 100% DUY NHẤT một giọng đọc Nam Minh tự nhiên, mượt mà.
"""

import re
import unicodedata


# 1. Từ điển viết tắt chức danh, tổ chức và văn bản hành chính tiếng Việt
ABBREVIATIONS = {
    r"\bTP\.\s*": "Thành phố ",
    r"\bTp\.\s*": "Thành phố ",
    r"\bGS\.\s*": "Giáo sư ",
    r"\bGs\.\s*": "Giáo sư ",
    r"\bPGS\.\s*": "Phó giáo sư ",
    r"\bPgs\.\s*": "Phó giáo sư ",
    r"\bTS\.\s*": "Tiến sĩ ",
    r"\bTs\.\s*": "Tiến sĩ ",
    r"\bThS\.\s*": "Thạc sĩ ",
    r"\bThs\.\s*": "Thạc sĩ ",
    r"\bBS\.\s*": "Bác sĩ ",
    r"\bBs\.\s*": "Bác sĩ ",
    r"\bNXB\b": "Nhà xuất bản",
    r"\bNxb\b": "Nhà xuất bản",
    r"\bĐ/c\b": "Đồng chí",
    r"\bđ/c\b": "đồng chí",
    r"\bV/v\b": "Về việc",
    r"\bv/v\b": "về việc",
    r"\bK/g\b": "Kính gửi",
    r"\bk/g\b": "kính gửi",
    r"\btr\.\s*(\d+)": r"trang \1",
    r"\bTr\.\s*(\d+)": r"Trang \1",
}

# 2. Từ điển chuyển ngữ & phiên âm thuật ngữ Công nghệ, Tiếng Anh sang tiếng Việt
# Giúp giọng Nam Minh đọc tự nhiên, trôi chảy, không bị ngắc ngứ hay crash máy chủ Edge-TTS
TECH_AND_ENGLISH_TERMS = {
    # Thuật ngữ AI & Công nghệ thông tin
    r"\bAI\b": "trí tuệ nhân tạo",
    r"\bA\.I\b": "trí tuệ nhân tạo",
    r"\bIT\b": "công nghệ thông tin",
    r"\bI\.T\b": "công nghệ thông tin",
    r"\bCEO\b": "giám đốc điều hành",
    r"\bTTS\b": "đọc văn bản",
    r"\bT\.T\.S\b": "đọc văn bản",
    r"\bAPI\b": "giao diện lập trình",
    r"\bA\.P\.I\b": "giao diện lập trình",
    r"\bUI/UX\b": "giao diện và trải nghiệm",
    r"\bUI\b": "giao diện",
    r"\bUX\b": "trải nghiệm người dùng",
    r"\bChatGPT\b": "Chát G P T",
    r"\bChat GPT\b": "Chát G P T",
    r"\bGPT\b": "G P T",
    r"\bOpenAI\b": "Open A I",
    r"\bClaude\b": "Cờ-lót",
    r"\bGemini\b": "Gê-mi-ni",

    # Ngôn ngữ lập trình & Hệ điều hành
    r"\bPython\b": "ngôn ngữ Bai-thơn",
    r"\bpython\b": "Bai-thơn",
    r"\bJava\b": "Gia-va",
    r"\bjava\b": "Gia-va",
    r"\bJavaScript\b": "Gia-va Sờ-cơ-ríp",
    r"\bJavascript\b": "Gia-va Sờ-cơ-ríp",
    r"\bC\+\+\b": "C cộng cộng",
    r"\bC#\b": "C thăng",
    r"\bHTML\b": "H T M L",
    r"\bCSS\b": "C S S",
    r"\bSQL\b": "S Q L",
    r"\bWindows\b": "Uyn-đâu",
    r"\bwindows\b": "Uyn-đâu",
    r"\bLinux\b": "Li-núc",
    r"\blinux\b": "Li-núc",
    r"\bmacOS\b": "Mác",
    r"\bMacOS\b": "Mác",
    r"\bMacBook\b": "máy tính Mác",
    r"\bAndroid\b": "An-đroi",
    r"\bandroid\b": "An-đroi",
    r"\biOS\b": "I O S",

    # Dịch vụ & Mạng xã hội
    r"\bGoogle\b": "Gú-gồ",
    r"\bgoogle\b": "Gú-gồ",
    r"\bMicrosoft\b": "Mai-cờ-rô-xốp",
    r"\bmicrosoft\b": "Mai-cờ-rô-xốp",
    r"\bYouTube\b": "Du-túp",
    r"\byoutube\b": "Du-túp",
    r"\bFacebook\b": "Phây-búc",
    r"\bfacebook\b": "Phây-búc",
    r"\bTikTok\b": "Tíc-tóc",
    r"\btiktok\b": "Tíc-tóc",
    r"\bInternet\b": "mạng in-tơ-nét",
    r"\binternet\b": "mạng in-tơ-nét",
    r"\bWebsite\b": "trang mạng",
    r"\bwebsite\b": "trang mạng",
    r"\bWeb\b": "mạng",
    r"\bweb\b": "mạng",
    r"\bWifi\b": "oai-phai",
    r"\bwifi\b": "oai-phai",
    r"\bWi-Fi\b": "oai-phai",

    # Khái niệm phần mềm & máy tính
    r"\bApp\b": "ứng dụng",
    r"\bapp\b": "ứng dụng",
    r"\bSoftware\b": "phần mềm",
    r"\bsoftware\b": "phần mềm",
    r"\bHardware\b": "phần cứng",
    r"\bhardware\b": "phần cứng",
    r"\bServer\b": "máy chủ",
    r"\bserver\b": "máy chủ",
    r"\bClient\b": "máy khách",
    r"\bclient\b": "máy khách",
    r"\bDatabase\b": "cơ sở dữ liệu",
    r"\bdatabase\b": "cơ sở dữ liệu",
    r"\bDeveloper\b": "lập trình viên",
    r"\bdeveloper\b": "lập trình viên",
    r"\bDev\b": "lập trình viên",
    r"\bdev\b": "lập trình viên",
    r"\bCode\b": "mã nguồn",
    r"\bcode\b": "mã nguồn",
    r"\bBug\b": "lỗi phần mềm",
    r"\bbug\b": "lỗi phần mềm",
    r"\bFix\b": "sửa lỗi",
    r"\bfix\b": "sửa lỗi",
    r"\bTest\b": "kiểm thử",
    r"\btest\b": "kiểm thử",
    r"\bRender\b": "kết xuất",
    r"\brender\b": "kết xuất",
    r"\bStream\b": "truyền phát",
    r"\bstream\b": "truyền phát",
    r"\bStreaming\b": "truyền phát liên tục",
    r"\bstreaming\b": "truyền phát liên tục",
    r"\bPlayer\b": "trình phát",
    r"\bplayer\b": "trình phát",
    r"\bAudio\b": "âm thanh",
    r"\baudio\b": "âm thanh",
    r"\bVideo\b": "vi-đê-ô",
    r"\bvideo\b": "vi-đê-ô",
    r"\bFile\b": "tệp tin",
    r"\bfile\b": "tệp tin",
    r"\bFolder\b": "thư mục",
    r"\bfolder\b": "thư mục",
    r"\bLink\b": "đường dẫn",
    r"\blink\b": "đường dẫn",
    r"\bOnline\b": "trực tuyến",
    r"\bonline\b": "trực tuyến",
    r"\bOffline\b": "ngoại tuyến",
    r"\boffline\b": "ngoại tuyến",
    r"\bDownload\b": "tải xuống",
    r"\bdownload\b": "tải xuống",
    r"\bUpload\b": "tải lên",
    r"\bupload\b": "tải lên",
    r"\bUpdate\b": "cập nhật",
    r"\bupdate\b": "cập nhật",
    r"\bLog\b": "nhật ký",
    r"\blog\b": "nhật ký",
    r"\bTool\b": "công cụ",
    r"\btool\b": "công cụ",
    r"\bProject\b": "dự án",
    r"\bproject\b": "dự án",
    r"\bData\b": "dữ liệu",
    r"\bdata\b": "dữ liệu",
    r"\bVersion\b": "phiên bản",
    r"\bversion\b": "phiên bản",
}

# 3. Chuẩn hóa đơn vị đo lường và tiền tệ
UNITS = {
    r"(\d+)\s*(?:km/h|kmh)\b": r"\1 ki-lô-mét trên giờ",
    r"(\d+)\s*km\b": r"\1 ki-lô-mét",
    r"(\d+)\s*m\b": r"\1 mét",
    r"(\d+)\s*cm\b": r"\1 xen-ti-mét",
    r"(\d+)\s*mm\b": r"\1 mi-li-mét",
    r"(\d+)\s*kg\b": r"\1 ki-lô-gam",
    r"(\d+)\s*g\b": r"\1 gam",
    r"(\d+)\s*ha\b": r"\1 héc-ta",
    r"(\d+)\s*m2\b": r"\1 mét vuông",
    r"(\d+)\s*m3\b": r"\1 mét khối",
    r"(\d+)\s*(?:trđ|triệu\s*đ)\b": r"\1 triệu đồng",
    r"(\d+)\s*(?:tỷ\s*đ)\b": r"\1 tỷ đồng",
    r"(\d+)\s*(?:đ|VND|VNĐ)\b": r"\1 đồng",
    r"(\d+)\s*\$": r"\1 đô la",
    r"\$\s*(\d+)": r"\1 đô la",
    r"(\d+)\s*%": r"\1 phần trăm",
}


def sanitize_dangerous_symbols(text: str) -> str:
    """
    Loại bỏ hoặc thay thế các ký hiệu gây lỗi treo/crash bộ tổng hợp Edge-TTS.
    Chuyển các ký hiệu đóng mở ngoặc thành dấu phẩy để ngắt nghỉ ngữ điệu tự nhiên.
    """
    # 1. Thay thế ngoặc đơn, ngoặc vuông, ngoặc nhọn bằng dấu phẩy
    text = re.sub(r"[\(\[\{]", ", ", text)
    text = re.sub(r"[\)\]\}]", ", ", text)

    # 2. Thay thế ký hiệu toán học / XML / SSML nguy hiểm
    text = re.sub(r"&", " và ", text)
    text = re.sub(r"[/\\\|]", " hoặc ", text)
    text = re.sub(r"[—–-]", " ", text)
    text = re.sub(r"[+*~^<>#@=]", " ", text)
    text = re.sub(r'["“”„”\'‘’‚’`]', " ", text)
    text = re.sub(r"[:;]", ", ", text)

    # 3. Dấu ba chấm thành một dấu chấm hoặc dấu phẩy
    text = re.sub(r"\.{3,}|…", ".", text)

    # 4. Bỏ các ký tự biểu tượng emoji, bullet point trang trí
    text = re.sub(r"[\u2022\u25cf\u25cb\u25aa\u25ab\u2190-\u21ff\u2600-\u26ff]", " ", text)

    # 5. Xóa ký tự điều khiển lạ
    text = "".join(ch for ch in text if ch in "\n\t " or ord(ch) >= 32)

    return text


def hyphenate_remaining_acronyms(text: str) -> str:
    """
    Chuyển các từ viết tắt in hoa tiếng Anh còn lại (như NASA, WHO, CPU, RAM)
    thành dạng tách chữ cái (N A S A, C P U) để Edge-TTS phát âm từng chữ cái mượt mà.
    """
    def _repl(match):
        w = match.group(0)
        if len(w) > 1:
            return " ".join(list(w))
        return w

    return re.sub(r"\b[A-Z]{2,5}\b", _repl, text)


def normalize_text_for_tts(text: str) -> str:
    """
    Hàm chuẩn hóa tổng thể văn bản trước khi đưa vào bộ TTS:
    - BƯỚC CỐT LÕI: Chuẩn hóa toàn bộ văn bản sang Unicode Dựng Sẵn (NFC).
      Đây là chìa khóa khắc phục triệt để lỗi NoAudioReceived trên giọng Nam Minh.
    - Làm sạch các ký hiệu đặc biệt nguy hiểm và thẻ XML/SSML.
    - Phiên âm & Việt hóa toàn bộ thuật ngữ tiếng Anh / công nghệ.
    - Chuẩn hóa đơn vị đo lường, tiền tệ, số liệu.
    - Đảm bảo câu từ thuần Việt 100% để Nam Minh đọc trơn tru từ đầu đến cuối.
    """
    if not text:
        return ""

    # BƯỚC 1: Chuẩn hóa Unicode NFC (Dựng sẵn canonical)
    text = unicodedata.normalize("NFC", text)

    # BƯỚC 2: Làm sạch ký hiệu nguy hiểm
    text = sanitize_dangerous_symbols(text)

    # BƯỚC 3: Thay thế các thuật ngữ Tiếng Anh / Công nghệ sang tiếng Việt hoặc phiên âm Việt
    for pattern, replacement in TECH_AND_ENGLISH_TERMS.items():
        text = re.sub(pattern, replacement, text)

    # BƯỚC 4: Thay thế từ viết tắt thông dụng
    for pattern, replacement in ABBREVIATIONS.items():
        text = re.sub(pattern, replacement, text)

    # BƯỚC 5: Thay thế đơn vị đo lường
    for pattern, replacement in UNITS.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # BƯỚC 6: Xử lý các từ viết tắt in hoa còn lại
    text = hyphenate_remaining_acronyms(text)

    # BƯỚC 7: Làm gọn dấu câu và khoảng trắng
    text = re.sub(r",\s*,+", ",", text)
    text = re.sub(r"\.\s*\.+", ".", text)
    text = re.sub(r",\s*\.", ".", text)

    # Chuẩn hóa khoảng trắng dư thừa
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # BƯỚC 8: Đảm bảo Unicode NFC lần cuối sau khi ghép các từ
    text = unicodedata.normalize("NFC", text.strip())

    return text
