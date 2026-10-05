# Đóng gói Windows

Ứng dụng và bộ cài có tên **ZizaSeo**. AppId và thư mục dữ liệu cũ `SeoWeb` được giữ để tương thích nâng cấp và cấu hình người dùng.

Máy build cần Windows x64, Python 3.11+ bản 64-bit có Tkinter, Internet và vài GB dung lượng trống. Người dùng cuối không cần Python, pip hay cài Playwright/Chromium riêng.

## Tạo bộ cài một file EXE

Mở PowerShell tại thư mục dự án. Cài Inno Setup 6 một lần:

```powershell
winget install --id JRSoftware.InnoSetup -e
```

Build ứng dụng và bộ cài:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1 -Installer
```

Gửi người dùng file **`dist\installer\ZizaSeo-Setup.exe`**. Họ cài đặt rồi mở shortcut ZizaSeo. Bộ cài bao gồm Python runtime, thư viện, giao diện và Chromium. Không cần quyền admin khi cài cho tài khoản hiện tại.

Nếu đã có `dist\ZizaSeo\ZizaSeo.exe` và chỉ cần tạo lại bộ cài (ví dụ vừa cài bổ sung Inno Setup), chạy:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1 -InstallerOnly
```

Lệnh này vẫn kiểm tra bản EXE trước khi đóng gói nhưng không build lại source. Nếu đã sửa code, dùng `-Installer` để tạo bản mới đầy đủ. Script kiểm tra Inno Setup ngay từ đầu để tránh chờ build xong mới phát hiện thiếu công cụ.

Script tạo `.venv-build`, cài dependencies, xác định đường dẫn Tcl/Tk của Python gốc, tải Chromium vào package Playwright rồi đóng gói bằng PyInstaller. Script dừng ngay nếu Tkinter/Tcl/Tk không hoạt động. Trước khi tạo bộ cài, script khởi tạo giao diện ZizaSeo trong bản EXE và kiểm tra Chromium bằng trang HTML nội bộ; không chạy traffic, gọi API AI hoặc lưu đè cấu hình người dùng.

## Tạo bản portable

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1
```

Kết quả: `dist\ZizaSeo\ZizaSeo.exe`. Phải gửi **toàn bộ thư mục `dist\ZizaSeo`**, gồm `_internal`; chỉ gửi EXE này sẽ thiếu thư viện/trình duyệt. Có thể nén cả thư mục thành ZIP. Chỉ file **Setup.exe** ở trên là bộ cài một file để phân phối.

## Dữ liệu và cấu hình

- EXE lưu cấu hình, profile, bộ đếm và log dưới `%LOCALAPPDATA%\SeoWeb`, không ghi vào thư mục cài đặt.
- Không đóng gói profile, bộ đếm hoặc API key đã nhập trong UI trên máy phát triển. Không ghi key thật trực tiếp trong source trước khi build.
- Người dùng cần Internet để truy cập website/API. Nếu chọn AI Box/Gemini, họ nhập API key riêng; `local` không cần API key. Ollama là dịch vụ tùy chọn bên ngoài, không được đóng gói.
- Cấu hình mặc định trong `config/settings.py` được đóng gói cùng ứng dụng. Thay đổi source cần build lại. Cấu hình người dùng đã lưu vẫn ưu tiên khi mở bản mới.
- Gỡ cài đặt giữ dữ liệu người dùng; muốn xóa hoàn toàn, đóng ứng dụng rồi xóa `%LOCALAPPDATA%\SeoWeb`.

## Kiểm tra trước khi phát hành

Sau build, cài và mở trên máy Windows sạch hoặc VM không có Python. Kiểm tra UI, mở browser, lưu cấu hình rồi mở lại. Kiểm tra tự động xác nhận giao diện và Chromium đóng gói khởi chạy được trên máy build, chưa thay thế kiểm thử trên máy sạch. Bản chưa ký số có thể hiển thị cảnh báo SmartScreen; ký số EXE/bộ cài nếu phát hành chính thức.

## Lỗi `No module named 'tkinter'`

PyInstaller có thể loại Tkinter khi Python build không tìm thấy Tcl/Tk, ngay cả khi `import tkinter` vẫn chạy được. Script đã tự tìm `tcl/tcl8.x` và `tcl/tk8.x` trong Python gốc, đặt `TCL_LIBRARY`/`TK_LIBRARY` cho bước build, và kiểm tra mở GUI thật trước khi đóng gói.

Chạy lại lệnh build để tạo bản mới. Nếu kiểm tra đầu vào vẫn báo thiếu Tcl/Tk, mở trình cài Python → **Modify/Repair** → bật **tcl/tk and IDLE**, rồi build lại. Tkinter không được khắc phục bằng `pip install tkinter`. Xem [tùy chọn Tcl/Tk của Python](https://docs.python.org/3.11/using/windows.html#installing-without-ui).

Nếu build báo lỗi kiểm tra EXE, xem `%LOCALAPPDATA%\SeoWeb\startup.log` và `ui_error.log`; không phát hành bộ cài từ lần build lỗi.

Tài liệu tham khảo: [Playwright/PyInstaller](https://playwright.dev/python/docs/library#pyinstaller), [CustomTkinter packaging](https://github.com/TomSchimansky/CustomTkinter/wiki/Packaging).
