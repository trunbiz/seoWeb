"""
utils/fix_encoding.py — Công cụ sửa lỗi encoding tiếng Việt.

Vấn đề: Nhiều file trong project đã bị hỏng ký tự tiếng Việt (hiển thị "?" thay vì
chữ có dấu) do lưu sai encoding (ANSI thay vì UTF-8).

Cách dùng:
    python fix_encoding.py

Script này sẽ:
1. Đọc các file .py quan trọng
2. Áp dụng bảng mapping từ ký tự hỏng → ký tự đúng
3. Ghi lại file với encoding UTF-8
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Mapping ký tự bị hỏng -> ký tự đúng
# Dùng cho trường hợp file bị lưu sai encoding (thường do PowerShell/CMD)
# Các ký tự bị mất dấu và hiển thị thành "?" hoặc ký tự thay thế
REPLACEMENTS = {
    # === config/settings.py ===
    "Desktop (Mặc định)": "Desktop (Mặc định)",
    "Random (Ngẫu nhiên mọi loại)": "Random (Ngẫu nhiên mọi loại)",
    "Random Mobile (Chỉ điện thoại)": "Random Mobile (Chỉ điện thoại)",
    # SEO keywords
    "nối mi thủ đức": "nối mi thủ đức",
    "uốn mi thủ đức": "uốn mi thủ đức",
    "chuyên bán dụng cụ nối mi ở tphcm": "chuyên bán dụng cụ nối mi ở tphcm",
    "dụng cụ nối mi giá rẻ tphcm": "dụng cụ nối mi giá rẻ tphcm",
    "nối mi quận 2": "nối mi quận 2",
    "nối mi thảo điền": "nối mi thảo điền",
    "uốn mi quận 2": "uốn mi quận 2",
    "nối mi gần đây": "nối mi gần đây",
    "nối mi trần não": "nối mi trần não",
    "uốn mi gần đây": "uốn mi gần đây",
    "nối mi tại Sài Gòn": "nối mi tại Sài Gòn",
    "nối mi tự nhiên": "nối mi tự nhiên",
    "dịch vụ làm đẹp mắt": "dịch vụ làm đẹp mắt",
    "uốn mi ở đâu đẹp": "uốn mi ở đâu đẹp",
    "nối mi giá rẻ quận 1": "nối mi giá rẻ quận 1",

    # === scenarios/warmup.py ===
    "nhạc lofi chill": "nhạc lofi chill",
    "nhạc tiktok remix 2024": "nhạc tiktok remix 2024",
    "highlight bóng đá ngoại hạng anh": "highlight bóng đá ngoại hạng anh",
    "hướng dẫn tập gym": "hướng dẫn tập gym",
    "công nghệ thông tin việc làm": "công nghệ thông tin việc làm",
    "học tiếng anh online": "học tiếng anh online",
    "cách nối mi tại nhà": "cách nối mi tại nhà",
    "các bước trang điểm cơ bản": "các bước trang điểm cơ bản",
    "mẫu móng tay đẹp 2024": "mẫu móng tay đẹp 2024",
    "review son môi 2024": "review son môi 2024",

    # === aio_traffic.py ===
    "nối mi tự nhiên ? Sài Gòn ? ?âu t?t": "nối mi tự nhiên ở Sài Gòn ở đâu tốt",
    "dịch vụ làm đẹp mắt chuyên nghi?p": "dịch vụ làm đẹp mắt chuyên nghiệp",
    "nối mi Hàn Quốc giá bao nhiêu": "nối mi Hàn Quốc giá bao nhiêu",
    "cách chăm sóc mi nối đúng cách": "cách chăm sóc mi nối đúng cách",
    "review tiệm nối mi ở quận 1": "review tiệm nối mi ở quận 1",
    "uốn mi cho mắt một mí": "uốn mi cho mắt một mí",
    "làm đẹp gần Q1": "làm đẹp gần Q1",
    "nối mi ở tphcm ở đâu tin cậy": "nối mi ở tphcm ở đâu tin cậy",

    # === utils/onsite_interactions.py ===
    "Xem thêm": "Xem thêm",
    "Mua ngay": "Mua ngay",
    "Đăng ký": "Đăng ký",
    "Chi tiết": "Chi tiết",
    "Tìm hiểu thêm": "Tìm hiểu thêm",

    # === backlinks/tracker.py ===
    "nối mi ở đâu tốt tphcm": "nối mi ở đâu tốt tphcm",
    "eyelash extension bình thạnh": "eyelash extension bình thạnh",
    "uốn mi ở thủ đức": "uốn mi ở thủ đức",


    # === scenarios/aio_traffic.py - site list ===
    "nankybeauty.com": "nankybeauty.com",
    "topdev.vn/nhan-noi-mi/": "topdev.vn/nhan-noi-mi/",
}

# Các ký tự tìm và thay thế dạng character-level
CHAR_FIXES = {
    # Các ký tự bị hỏng phổ biến
    '?': '',  # ký tự "?" là wildcard, xử lý cẩn thận
}


def fix_text(text: str) -> str:
    """Áp dụng tất cả các bảng mapping để sửa text."""
    for corrupted, correct in REPLACEMENTS.items():
        if corrupted != correct:
            text = text.replace(corrupted, correct)
    return text


def fix_file(filepath: str) -> bool:
    """Sửa encoding cho một file. Return True nếu có thay đổi."""
    if not os.path.exists(filepath):
        print(f"   [SKIP] Không tìm thấy: {filepath}")
        return False

    # Thử đọc file
    original_content = None
    for enc in ['utf-8', 'latin-1', 'cp1252', 'cp1258']:
        try:
            with open(filepath, 'r', encoding=enc, errors='replace') as f:
                original_content = f.read()
            break
        except:
            continue

    if original_content is None:
        print(f"   [FAIL] Không thể đọc: {filepath}")
        return False

    # Sửa text
    fixed_content = fix_text(original_content)

    if fixed_content == original_content:
        # Thử dùng character-level fix
        # Thay thế các ký tự lẻ bị hỏng (thường là ký tự Latin thay vì Unicode)
        fixed_content = original_content

    if fixed_content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        print(f"   [FIXED] {os.path.basename(filepath)}")
        return True
    else:
        print(f"   [OK] {os.path.basename(filepath)} — không cần sửa")
        return False


def main():
    """Chạy fix encoding cho tất cả file Python trong project."""
    print("🔧 Bắt đầu fix encoding tiếng Việt...")
    print()

    # Các thư mục cần quét
    scan_dirs = [
        BASE_DIR,
        os.path.join(BASE_DIR, "config"),
        os.path.join(BASE_DIR, "core"),
        os.path.join(BASE_DIR, "tests"),
        os.path.join(BASE_DIR, "scenarios"),
        os.path.join(BASE_DIR, "utils"),
        os.path.join(BASE_DIR, "content"),
        os.path.join(BASE_DIR, "backlinks"),
    ]

    fixed_count = 0
    total_count = 0

    for scan_dir in scan_dirs:
        if not os.path.exists(scan_dir):
            continue
        for fname in sorted(os.listdir(scan_dir)):
            if fname.endswith('.py'):
                total_count += 1
                filepath = os.path.join(scan_dir, fname)
                if fix_file(filepath):
                    fixed_count += 1

    print()
    print(f"✅ Hoàn thành: {fixed_count}/{total_count} file đã được sửa.")

    if fixed_count > 0:
        print("\n⚠️  Lưu ý: Nếu file vẫn hiển thị sai, nguyên nhân có thể là")
        print("   ký tự gốc đã bị hỏng không thể khôi phục (mất thông tin).")
        print("   Cần gõ lại các từ tiếng Việt trong file đó.")


if __name__ == "__main__":
    main()
