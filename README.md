# ZizaSeo

## Đóng gói bộ cài

```powershell
winget install --id JRSoftware.InnoSetup -e
powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1 -Installer


```

File kết quả: `dist\installer\ZizaSeo-Setup.exe`.

Nếu ứng dụng đã build xong nhưng bước tạo bộ cài báo thiếu Inno Setup, cài công cụ rồi chỉ chạy lại bước tạo bộ cài:

```powershell
winget install --id JRSoftware.InnoSetup -e
powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1 -InstallerOnly
```

`-InstallerOnly` dùng bản có sẵn trong `dist\ZizaSeo`, không build lại mã nguồn. Sau khi sửa code, dùng `-Installer` như bình thường.

Nếu bản cũ báo `No module named 'tkinter'`, chạy lại script build đã cập nhật. Script tự thiết lập đường dẫn Tcl/Tk và kiểm tra cả giao diện lẫn Chromium trong EXE trước khi tạo bộ cài. Xem [hướng dẫn sửa lỗi Tkinter](docs/BUILD_WINDOWS.md#lỗi-no-module-named-tkinter).

Ứng dụng desktop Python dùng Playwright để mô phỏng các phiên truy cập website theo ba luồng: truy cập trực tiếp, tìm kiếm Google và AIO. Ứng dụng có giao diện CustomTkinter, hỗ trợ proxy, giả lập thiết bị, warm-up, giới hạn số phiên và lưu profile cho người dùng quay lại.

> Lưu ý: tự động hóa traffic không bảo đảm cải thiện thứ hạng SEO. Hãy dùng với tải thấp, trên website bạn có quyền kiểm thử, và tuân thủ điều khoản của các website/dịch vụ được truy cập.

## Yêu cầu

- Windows 10/11
- Python 3.11 trở lên
- Kết nối Internet
- Khoảng 1 GB dung lượng trống để cài Chromium
- Gemini API key nếu muốn dùng `gemini-3.5-flash`; ứng dụng vẫn chạy bằng local fallback khi không có key

## Cài đặt

Để tạo bộ cài Windows `ZizaSeo-Setup.exe` kèm Chromium, xem [hướng dẫn đóng gói EXE](docs/BUILD_WINDOWS.md).

Mở PowerShell tại thư mục dự án:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m playwright install chromium
```

Để dùng Gemini 3.5 Flash, tạo API key trong Google AI Studio rồi đặt biến môi trường trước khi mở ứng dụng:

```powershell
$env:GEMINI_API_KEY="dán-api-key-vào-đây"
$env:AI_PROVIDER="gemini"
python ui.py
```

Không ghi API key thật vào `settings.py` và không commit key lên Git. Key nhập trong tab **Kết nối AI** được tự lưu mã hóa trên máy và khôi phục khi mở lại ứng dụng.

Nếu PowerShell chặn script kích hoạt môi trường ảo:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
```

## Chạy giao diện

```powershell
python ui.py
```

Thiết lập chính trên giao diện:

Giao diện ZizaSeo gồm 6 tab: **Website**, **Lịch chạy**, **Trình duyệt**, **Tương tác**, **Kết nối AI**, **Khởi động**. Thanh điều khiển bên trái luôn hiển thị nút chạy/dừng, trạng thái và kết quả lần chạy. Các thiết lập được tự lưu. Mỗi tab có thể cuộn để dùng trên cửa sổ nhỏ.

- `Ctrl + Enter`: bắt đầu chạy; `Esc`: yêu cầu dừng; `Ctrl + S`: lưu thiết lập.
- Nhật ký có thể thu gọn, sao chép hoặc xóa; bỏ chọn **Cuộn tự động** để đọc dòng cũ. UI giữ khoảng 3.000 dòng gần nhất để tránh tăng bộ nhớ khi chạy lâu.
- Khi URL hoặc thời gian nhập không hợp lệ, ứng dụng chỉ rõ tab cần sửa trước khi chạy.
- Thư mục dữ liệu `%LOCALAPPDATA%\SeoWeb` được giữ nguyên để tương thích cấu hình/profile cũ; tên ứng dụng và bộ cài đã đổi thành ZizaSeo.

1. Nhập URL đầy đủ, ví dụ `https://example.com/`.
2. Chọn `Direct`, `Google Search`, `AIO` hoặc `Mix`.
3. Nhập mỗi từ khóa trên một dòng.
4. Nếu dùng proxy, nhập mỗi proxy trên một dòng. Các định dạng được hỗ trợ:
   - `http://host:port`
   - `host:port:user:password`
5. Chọn thiết bị và số worker.
6. Đặt thời gian xem trang tối thiểu/tối đa.
7. Bật `AUTO LOOP` và **Chạy liên tục đến khi nhấn Dừng** để chạy vô thời hạn, không nghỉ giữa phiên và không áp dụng hạn mức phiên/ngày. Tùy chọn này mặc định bật; ô số phút bị vô hiệu hóa. Bỏ chọn **Chạy liên tục** để dùng thời gian đã nhập và các giới hạn thông thường. Khi tắt `AUTO LOOP`, mỗi worker chỉ chạy một phiên.
8. Nhấn **Bắt đầu treo máy**.

### AI Engine

- MaxMorus: chọn `maxmorus` trong tab **Kết nối AI**, nhập API key rồi nhấn **Kiểm tra MaxMorus**. Model mặc định `cl/deepseek/deepseek-v4.1-flash`, endpoint `https://ai.maxmorus.com/v1/chat/completions`. CLI dùng `MAXMORUS_API_KEY`, `MAXMORUS_MODEL`, `MAXMORUS_API_URL`.

- AI Box: chọn `aibox`, cấu hình `AIBOX_API_KEY` và model `deepseek-v4.1-flash`. Xem [hướng dẫn cấu hình AI đầy đủ](docs/AI_CONFIGURATION.md).

- Chọn `gemini` để dùng model `gemini-3.5-flash` tạo persona, hành vi tìm kiếm và từ khóa biến thể.
- Nhập API key hoặc khởi động ứng dụng với biến môi trường `GEMINI_API_KEY`.
- Nhấn **Kiểm tra Gemini** trước khi chạy.
- Chọn `local` nếu không muốn gọi API hoặc phát sinh chi phí.
- Nếu Gemini timeout, hết quota hoặc trả lỗi và `AI_FALLBACK_LOCAL=True`, ứng dụng tự chuyển sang bộ sinh local.

Nút dừng yêu cầu các thao tác Playwright hiện tại kết thúc hoặc timeout; nó không đóng cưỡng bức browser giữa một lệnh đang chạy.

## Chạy bằng dòng lệnh

Xem tổng quan chiến lược:

```powershell
python main.py
```

Chạy một phiên tìm kiếm hoặc trực tiếp:

```powershell
python main.py --search
python main.py --direct
```

Các báo cáo tĩnh:

```powershell
python main.py --plan
python main.py --keywords
python main.py --backlinks
```

Nếu terminal cũ hiển thị tiếng Việt sai, chạy trước:

```powershell
chcp 65001
$env:PYTHONUTF8="1"
```

## Cấu hình

Cấu hình mặc định nằm trong `config/settings.py`:

- `TARGET_URL`: website đích.
- `SEO_KEYWORDS`: danh sách từ khóa.
- `MAX_SESSIONS_PER_DAY`: số phiên tối đa mỗi ngày.
- `MIN_INTERVAL_BETWEEN_SESSIONS`: khoảng cách tối thiểu giữa hai phiên của cùng một worker, tính bằng giây.
- `DURATION_MIN`, `DURATION_MAX`: khoảng thời gian tương tác trên site đích.
- `HEADLESS_MODE`: chạy ẩn cửa sổ Chromium.
- `LOAD_IMAGES`: cho phép/chặn tải ảnh.
- `ALWAYS_NEW_USER`: tạo profile mới hoặc tái sử dụng profile theo worker/proxy.
- `AI_PROVIDER`: `gemini`, `aibox`, `maxmorus` hoặc `local`.
- `GEMINI_MODEL`: mặc định `gemini-3.5-flash`.
- `GEMINI_API_KEY`: đọc từ biến môi trường hoặc cấu hình đã lưu trên UI.
- `AI_FALLBACK_LOCAL`: tiếp tục chạy bằng logic local khi Gemini lỗi.

Giao diện tự lưu cấu hình tại `%LOCALAPPDATA%\SeoWeb\settings.dat`, mã hóa bằng Windows DPAPI, và khôi phục khi mở lại. Không sửa trực tiếp `settings.py`. Xem [chi tiết lưu cấu hình](docs/AI_CONFIGURATION.md).

## Profile và giới hạn phiên

Chế độ **Chạy liên tục** chỉ có hiệu lực cùng **AUTO LOOP** (`LOOP_ENABLE=True`, `LOOP_CONTINUOUS=True`). Trong chế độ này, mỗi worker bắt đầu phiên tiếp theo ngay khi phiên trước kết thúc; không áp dụng `LOOP_DURATION_MINUTES`, `MIN_INTERVAL_BETWEEN_SESSIONS`, `REST_BETWEEN_SESSIONS_MIN/MAX` và `MAX_SESSIONS_PER_DAY`. Bộ đếm phiên vẫn được ghi lại. Thời gian tải trang, tương tác và warm-up bên trong phiên vẫn giữ nguyên. Nhấn **Dừng** để kết thúc; ứng dụng không tự chạy lại sau khi bị đóng/crash.

Các giới hạn dưới đây áp dụng khi **không bật Chạy liên tục**:

- Trạng thái giới hạn được lưu tại `session_state.json`.
- Profile quay lại được lưu trong `profiles/state_<id>.json`.
- Khi bật `ALWAYS_NEW_USER`, state của profile ngẫu nhiên không được lưu lại.
- Một suất chạy được tính ngay khi phiên bắt đầu, kể cả phiên sau đó thất bại.
- Cooldown được theo dõi riêng cho từng worker, vì vậy slider số luồng có thể chạy đồng thời. `MAX_SESSIONS_PER_DAY` vẫn áp dụng chung cho toàn ứng dụng.

Muốn reset bộ đếm trong môi trường phát triển, hãy đóng ứng dụng rồi xóa `session_state.json`. Không nên reset để vượt giới hạn khi đang chạy thật.

## Chạy kiểm thử

Không cần cài thêm framework test:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
python -m compileall -q .
```

Các test hồi quy hiện kiểm tra nhận diện CAPTCHA async và việc nhiều thread không thể vượt rate limit.

## Cấu trúc dự án

```text
core/           Quản lý Playwright browser, context và device
scenarios/      Warm-up và AIO flow
utils/          Tương tác trang, mouse, persona và rate limiter
tests/          Search/direct flow cũ và kiểm thử hồi quy
content/        Kế hoạch nội dung, nghiên cứu từ khóa mẫu
backlinks/      Kế hoạch backlink mẫu
config/         Cấu hình mặc định
ui.py           Giao diện desktop
main.py         Điểm chạy dòng lệnh
```

## Xử lý lỗi thường gặp

### `Executable doesn't exist` hoặc không mở được Chromium

```powershell
python -m playwright install chromium
```

### Google timeout hoặc tìm kiếm thất bại

Nếu Google không tải được (ví dụ `Page.goto: Timeout 60000ms exceeded`), lỗi thao tác tìm kiếm, thiếu từ khóa hoặc không tìm thấy kết quả, Search và bước tìm kiếm Google của AIO sẽ chuyển sang truy cập trực tiếp `TARGET_URL`. Log ghi rõ `SEARCH FAILED -> DIRECT` hoặc lý do tương ứng. Lỗi tương tác sau khi đã vào website đích không tự khởi động lại lượt truy cập.

Trong `config/settings.py`:

- `TARGET_NAVIGATION_ATTEMPTS = 3`: số lần tối đa thử tải website đích khi gặp lỗi mạng/timeout.
- `TARGET_NAVIGATION_TIMEOUT_MS = 60000`: timeout mỗi lần tải đích; nghỉ 1 giây giữa các lần thử lỗi.

Nếu tất cả lần thử đều thất bại, website trả HTTP lỗi, điều hướng sai hoặc yêu cầu CAPTCHA, phiên vẫn báo thất bại đúng thực tế. Không thể bảo đảm truy cập thành công khi website/mạng không hoạt động. AUTO LOOP tiếp tục phiên sau; nhấn Dừng sẽ ngăn lần thử tiếp theo.

### Xử lý CAPTCHA

Mặc định `CAPTCHA_ACTION = "direct"` trong `config/settings.py`: khi Search hoặc bước Google của AIO gặp CAPTCHA, ứng dụng **bỏ Google và truy cập trực tiếp `TARGET_URL`**, không chờ bạn thao tác. Hoạt động cả khi bật Headless. Ứng dụng không tự giải CAPTCHA.

- Phiên chuyển sang Direct vẫn thực hiện tương tác trên website đích. Log ghi `[CAPTCHA -> DIRECT]`, không gán nguồn Google giả cho lượt truy cập này.
- Nếu website đích lỗi, điều hướng sai hoặc cũng có CAPTCHA, phiên được tính thất bại; không lặp lại fallback vô hạn.
- Bật **AUTO LOOP** để tiếp tục các phiên sau. Khi tắt, mỗi worker chỉ chạy một phiên. Giới hạn ngày và khoảng cách giữa các phiên vẫn áp dụng.
- Nếu muốn bỏ Google hoàn toàn cho mọi phiên, chọn chế độ **Direct** trên UI.
- Tùy chọn cũ: đặt `CAPTCHA_ACTION = "manual"` để chờ xác minh; `CAPTCHA_WAIT_SECONDS = 180` và `CAPTCHA_COOLDOWN_SECONDS = 60` chỉ áp dụng cho chế độ này. Cần tắt Headless để xác minh thủ công.

Nếu gặp CAPTCHA liên tục, giảm số worker và tăng `MIN_INTERVAL_BETWEEN_SESSIONS`. Chuyển sang Direct không tạo lượt truy cập từ kết quả tìm kiếm Google.

### Proxy không kết nối

Kiểm tra đúng giao thức và thông tin xác thực. Với proxy IPv6 hoặc mật khẩu chứa dấu `:`, định dạng bốn phần hiện không phù hợp; hãy dùng URL proxy đầy đủ.

### UI dừng chậm

Nút dừng là cooperative stop. Một thao tác đang chờ navigation có thể mất đến timeout đã cấu hình trước khi context đóng.

### File profile tăng nhiều

Profile chỉ được lưu khi tắt “Luôn dùng User mới”. Có thể xóa các file cũ trong `profiles/` sau khi đã đóng ứng dụng.

### Nhiều website trong một phiên

Trong tab **Website**, nhập URL chính và danh sách **Website đích bổ sung**, mỗi dòng một URL đầy đủ. Mỗi phiên ghé lần lượt tất cả URL trong cùng browser context; URL trùng được bỏ qua. Website lỗi không ngăn các website sau; phiên chỉ thành công khi tất cả website thành công.

Tab **Tương tác**: đặt Min/Max giây onsite cho mỗi website (ví dụ 30–90). Thời gian được chọn ngẫu nhiên riêng cho từng website, áp dụng cho Direct, Google, AIO và Mix. Khoảng này tính phần tương tác onsite, không bao gồm warm-up, tìm kiếm hay tải trang ban đầu. Danh sách và thời gian được tự lưu. Từ khóa hiện dùng chung cho các website.

### Browser identity for automated testing

Device presets now change viewport dimensions only. Sessions keep native Chromium user agent, platform, GPU, CPU and memory values. iPhone/iPad presets do not represent real iOS/Safari devices. Fingerprint override scripts, stealth injection and automation-hiding launch flags have been removed. Browser detection is an expected outcome of automated testing. Existing cookies remain subject to the profile settings.
