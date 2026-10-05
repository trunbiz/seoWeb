# Hướng dẫn cấu hình AI Engine

## MaxMorus

Chọn `maxmorus` trong tab **Kết nối AI**, nhập API key rồi nhấn **Kiểm tra MaxMorus**. Model, URL và key được lưu mã hóa trên máy. Kiểm tra kết nối gửi request thật, có thể tính phí.

```powershell
$env:AI_PROVIDER="maxmorus"
$env:MAXMORUS_API_KEY="YOUR_API_KEY"
$env:MAXMORUS_MODEL="cl/deepseek/deepseek-v4.1-flash"
$env:MAXMORUS_API_URL="https://ai.maxmorus.com/v1/chat/completions"
python ui.py
```

MaxMorus gửi `stream: false`, dùng Bearer token và đọc `choices[0].message.content`, bỏ qua reasoning và provider_metadata. Khi API lỗi, `AI_FALLBACK_LOCAL` quyết định có dùng bộ sinh local hay không. Không ghi key thật vào source.

AI Engine hỗ trợ `gemini`, `aibox`, `maxmorus` và `local` cho ba chức năng: tạo persona, tạo hành vi tìm kiếm và biến thể từ khóa. Các báo cáo trong `content/` vẫn dùng dữ liệu/logic hiện có; tích hợp này không chuyển chúng thành công cụ viết bài bằng AI.

Mỗi thời điểm chỉ chọn **một** provider qua `AI_PROVIDER` hoặc dropdown trên UI. UI chỉ hiện cấu hình tương ứng và áp dụng lựa chọn khi bắt đầu chạy. Các key của provider khác không được dùng. Fallback local (nếu bật) chỉ xử lý khi provider đã chọn lỗi, không gọi đồng thời hay chuyển sang nhà cung cấp API khác.

## Chạy với AI Box

Tại thư mục dự án, mở PowerShell và chạy:

```powershell
python -m pip install -r requirements.txt
$env:AI_PROVIDER="aibox"
$env:AIBOX_API_KEY="YOUR_API_KEY"
$env:AIBOX_MODEL="deepseek-v4.1-flash"
$env:AIBOX_API_URL="https://api.ai-box.vn/v1/chat/completions"
$env:AI_FALLBACK_LOCAL="true"
python ui.py
```

Thay `YOUR_API_KEY` bằng khóa của bạn. Các biến `$env:` chỉ áp dụng cho PowerShell hiện tại và chương trình khởi chạy từ đó. Dự án không tự đọc file `.env`. Không đưa khóa thật vào source hay tài liệu.

Trong tab **Kết nối AI**, chọn `aibox`, nhập model, API key và URL đầy đủ rồi nhấn **Kiểm tra AI Box**. Nút kiểm tra gửi request thật, có thể tính phí.

UI tự lưu mỗi giây khi có thay đổi, khi bắt đầu chạy và khi đóng cửa sổ. Khi mở lại, giá trị đã lưu được ưu tiên hơn `settings.py` và biến môi trường. Bao gồm URL, proxy, từ khóa, số luồng, tùy chọn trình duyệt/warm-up/hành vi và cấu hình từng provider AI. Log không được lưu trong cấu hình.

File nằm tại `%LOCALAPPDATA%\SeoWeb\settings.dat`, được mã hóa bằng Windows DPAPI cho tài khoản Windows hiện tại, bao gồm API key và proxy. Không sửa file bằng tay hoặc chép sang máy/tài khoản khác. Muốn về mặc định: đóng ứng dụng rồi xóa file này. CLI vẫn dùng `settings.py` và biến môi trường. Nếu tắt cưỡng bức trước lần tự lưu tiếp theo, thay đổi trong giây cuối có thể chưa được ghi.

## Các vị trí cấu hình

| Biến trong `config/settings.py` | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `AI_PROVIDER` | `gemini` | Chọn `gemini`, `aibox`, `maxmorus`, `local`; có thể đặt qua biến môi trường cùng tên |
| `AIBOX_API_KEY` | rỗng | Bearer token, đọc từ môi trường hoặc nhập UI |
| `AIBOX_API_URL` | `https://api.ai-box.vn/v1/chat/completions` | Endpoint đầy đủ, đọc từ môi trường hoặc UI |
| `AIBOX_MODEL` | `deepseek-v4.1-flash` | Model AI Box, đọc từ môi trường hoặc UI |
| `AI_FALLBACK_LOCAL` | `true` | Môi trường: `true`, `1`, `yes` bật; giá trị khác tắt |
| `GEMINI_API_KEY` | rỗng | Khóa Gemini từ môi trường hoặc UI |
| `GEMINI_MODEL` | giá trị hiện có trong settings | Model Gemini từ môi trường hoặc UI |
| `GEMINI_API_URL` | Google API v1beta | Sửa trong settings nếu cần |
| `OLLAMA_URL`, `OLLAMA_MODEL` | giá trị trong settings | Chỉ dùng phần kiểm tra Ollama hiện có trên UI |

`local` và local fallback là bộ sinh bằng Python, không gọi Ollama và không cần API key. `CONTENT_MODEL` không chọn model cho ba chức năng AI Engine; dùng `AIBOX_MODEL` hoặc `GEMINI_MODEL` tương ứng.

Các cấu hình ứng dụng khác nằm trong `config/settings.py`: `TARGET_URL` (website), `SEO_KEYWORDS` (từ khóa), `PROXY_LIST`, `HEADLESS_MODE`, `DEVICE_NAME`, `DURATION_MIN/MAX`, `MAX_SESSIONS_PER_DAY` và `MIN_INTERVAL_BETWEEN_SESSIONS`. UI lưu lựa chọn vào file riêng trên máy, không sửa `settings.py`.

## Request và xử lý response

Backend tại `utils/ai_engine.py` gửi POST với `Authorization: Bearer ...`, `Content-Type: application/json`, `model` và `messages`. System message yêu cầu JSON theo schema của chức năng đang dùng; không yêu cầu thêm tham số API ngoài hợp đồng mẫu đã cung cấp.

Backend lấy `choices[0].message.content`, bỏ qua `reasoning_content`, chấp nhận JSON thuần hoặc JSON trong code fence. Response phải kết thúc bằng `finish_reason="stop"`. Dữ liệu thiếu trường, sai kiểu hoặc JSON lỗi sẽ bị từ chối. Request có timeout 30 giây; không tự retry.

Nếu thiếu key, lỗi HTTP, timeout hoặc dữ liệu không hợp lệ: bật fallback thì sinh bằng local; tắt fallback thì phát sinh lỗi cho bên gọi. Provider không hợp lệ luôn báo lỗi. Nút kiểm tra kết nối luôn báo kết quả API thật, không dùng fallback để báo thành công giả.

## Chẩn đoán và kiểm thử

- HTTP 401/403: kiểm tra key và quyền truy cập.
- HTTP 404: kiểm tra URL đầy đủ và model.
- HTTP 429: kiểm tra quota và tần suất gọi.
- JSON lỗi hoặc response bị cắt: kiểm tra khả năng trả JSON của model; thử lại bằng nút kiểm tra.
- UI ưu tiên cấu hình đã lưu; sửa trên UI hoặc xóa file cấu hình để nạp lại mặc định/biến môi trường.

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
python -m compileall -q config utils ui.py tests
```

Các unit test giả lập HTTP, không dùng khóa thật và không tốn phí. Việc test tự động thành công không xác nhận key, quota hoặc tình trạng dịch vụ AI Box thực tế.
