import sys
import asyncio
import edge_tts

sys.stdout.reconfigure(encoding="utf-8")

async def test_phrase(phrase, label):
    c = edge_tts.Communicate(phrase, "vi-VN-NamMinhNeural")
    try:
        await c.save(f"test_{label}.mp3")
        print(f"[{label}] 100% PASS: {phrase}")
        return True
    except Exception as e:
        print(f"[{label}] FAIL: {phrase} -> {e}")
        return False

async def main():
    # Thử nghiệm các phiên âm tiếng Việt tự nhiên của Nam Minh
    await test_phrase("Ngôn ngữ lập trình Pai thơn rất phổ biến.", "python")
    await asyncio.sleep(0.5)
    await test_phrase("Hệ điều hành Uyn đâu phổ biến trên toàn cầu.", "windows")
    await asyncio.sleep(0.5)
    await test_phrase("Tập đoàn Mai cờ rô xốp phát triển công nghệ.", "microsoft")
    await asyncio.sleep(0.5)
    await test_phrase("Công cụ Chát G-P-T vô cùng thông minh.", "chatgpt")
    await asyncio.sleep(0.5)
    await test_phrase("Mạng In tơ nét kết nối toàn cầu.", "internet")
    await asyncio.sleep(0.5)
    await test_phrase("Mạng xã hội Phây búc và ứng dụng Tíc tóc.", "fb_tiktok")
    await asyncio.sleep(0.5)
    await test_phrase("Xem video trên kênh Diu túp.", "youtube")
    await asyncio.sleep(0.5)
    await test_phrase("Truy cập trang oép trực tuyến.", "website")

if __name__ == "__main__":
    asyncio.run(main())
