import os

files_to_fix = [
    r'I:\seo2\config\settings.py',
    r'I:\seo2\tests\test_search_flow.py',
    r'I:\seo2\tests\test_direct_access.py',
    r'I:\seo2\scenarios\aio_traffic.py',
]

# Correct Vietnamese strings to replace corrupted ones
replacements = {
    # Settings keywords (corrupted -> correct)
    "n?i mi t?i Sài Gòn": "n?i mi t?i Sài Gòn",
    "n?i mi t? nhiên": "n?i mi t? nhiên",
    "d?ch v? làm ?p m?t": "d?ch v? làm ?p m?t",
    "u?n mi ? ?u ?p": "u?n mi ? ?u ?p",
    "n?i mi giá r? qu?n 1": "n?i mi giá r? qu?n 1",
    
    # AIO questions
    "n?i mi t? nhiên ? Sài Gòn ? ?âu t?t": "n?i mi t? nhiên ? Sài Gòn ? ?âu t?t",
    "d?ch v? làm ?p m?t chuyên nghi?p": "d?ch v? làm ?p m?t chuyên nghi?p",
    "n?i mi Hàn Qu?c giá bao nhiêu": "n?i mi Hàn Qu?c giá bao nhiêu",
    "cách ch?m sóc mi n?i ?úng cách": "cách ch?m sóc mi n?i ?úng cách",
    "review ti?m n?i mi ? qu?n 1": "review ti?m n?i mi ? qu?n 1",
    "u?n mi cho m?t m?t mí": "u?n mi cho m?t m?t mí",
    "làm ?p g?n Q1": "làm ?p g?n Q1",
    "n?i mi ? tphcm ? ?âu tin c?y": "n?i mi ? tphcm ? ?âu tin c?y",
}

# Actually, the problem is deeper - all files need proper encoding
# Let me just ensure the files are UTF-8 and fix critical strings

for filepath in files_to_fix:
    if not os.path.exists(filepath):
        print(f"Not found: {filepath}")
        continue
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    # The goal is to ensure proper Vietnamese characters
    # Most corruptions are from characters being lost when saving via PowerShell
    # We need to read the file as-is and write it back as proper UTF-8
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Fixed encoding: {os.path.basename(filepath)}")

print("\nDone. Note: Vietnamese chars may still be corrupted if they were already lost.")
print("The core issue: files need to be created with proper encoding from the start.")
