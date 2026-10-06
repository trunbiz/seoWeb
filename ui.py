import customtkinter as ctk
import threading
import asyncio
import sys
import random
import time
import uuid
import itertools
import traceback
import requests
from tkinter import END
from tkinter import messagebox
from pathlib import Path
from utils.ui_layout import ZizaLayout, BG, ACCENT, MUTED
from utils.user_settings import load_settings, save_settings
from utils.targets import current_target, parse_targets

from core.browser_manager import BrowserManager
from tests.test_direct_access import run_deep_session
import config.settings as cfg

_real_stderr = sys.stderr  # preserve before any redirect

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class RedirectText:
    def __init__(self, text_ctrl, app):
        self.output = text_ctrl
        self.app = app

    def write(self, string):
        if string:
            try:
                self.app.after(0, self._insert_text, string)
            except Exception:
                _real_stderr.write(string)

    def _insert_text(self, string):
        try:
            self.output.configure(state="normal")
            self.output.insert(END, string)
            # Keep long-running sessions responsive instead of growing forever.
            line_count = int(self.output.index("end-1c").split(".")[0])
            if line_count > 3000:
                self.output.delete("1.0", f"{line_count - 3000}.0")
            if self.app.chk_follow_log.get():
                self.output.see(END)
            self.output.configure(state="disabled")
        except Exception:
            _real_stderr.write(string)

    def flush(self): pass


class ZizaSeoUI(ZizaLayout, ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{cfg.APP_NAME} · Không gian SEO")
        self.geometry("1280x860")
        self.minsize(1100, 720)
        self.configure(fg_color=BG)
        icon_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        icon_path = icon_root / "assets" / "zizaseo.ico"
        if icon_path.exists():
            self.after(250, lambda: self.iconbitmap(str(icon_path)))
        self.is_running = False
        self.stop_event = threading.Event()
        self._session_ok = 0
        self._session_err = 0

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_area()

        sys.stdout = RedirectText(self.txt_log, self)
        sys.stderr = RedirectText(self.txt_log, self)
        self._saved_values = None
        self._settings_error_shown = False
        if "--smoke-test" not in sys.argv:
            self._restore_settings()
        self.protocol("WM_DELETE_WINDOW", self._close_window)
        self._autosave_id = self.after(1000, self._autosave_settings)
        self.bind("<Control-Return>", lambda event: self.start_thread())
        self.bind("<Escape>", lambda event: self.stop_process())
        self.bind("<Control-s>", lambda event: self._save_settings())

    def _settings_widgets(self):
        types = (ctk.CTkEntry, ctk.CTkComboBox, ctk.CTkCheckBox,
                 ctk.CTkSwitch, ctk.CTkSlider, ctk.CTkTextbox)
        return {name: widget for name, widget in vars(self).items()
                if isinstance(widget, types) and name != "txt_log"}

    def _collect_settings(self):
        values = {"radio_var": self.radio_var.get()}
        for name, widget in self._settings_widgets().items():
            values[name] = (widget.get("1.0", "end-1c")
                            if isinstance(widget, ctk.CTkTextbox) else widget.get())
        return values

    def _restore_settings(self):
        try:
            values = load_settings()
            for name, widget in self._settings_widgets().items():
                if name not in values:
                    continue
                value = values[name]
                if isinstance(widget, (ctk.CTkCheckBox, ctk.CTkSwitch)):
                    if value in (0, 1):
                        widget.select() if value else widget.deselect()
                elif isinstance(widget, ctk.CTkSlider):
                    if type(value) in (int, float):
                        widget.set(value)
                        command = widget.cget("command")
                        if command:
                            command(widget.get())
                elif isinstance(value, str):
                    if isinstance(widget, ctk.CTkComboBox):
                        if name != "combo_ai_provider" or value in ("gemini", "aibox", "maxmorus", "local"):
                            widget.set(value)
                    elif isinstance(widget, ctk.CTkTextbox):
                        widget.delete("1.0", "end")
                        widget.insert("1.0", value)
                    else:
                        previous_state = widget.cget("state")
                        widget.configure(state="normal")
                        widget.delete(0, "end")
                        widget.insert(0, value)
                        widget.configure(state=previous_state)
            if values.get("radio_var") in ("direct", "search", "aio", "mix"):
                self.radio_var.set(values["radio_var"])
            self._select_ai_provider(self.combo_ai_provider.get())
            self._continuous_changed()
            self._saved_values = self._collect_settings()
        except (OSError, ValueError) as exc:
            messagebox.showwarning("Cấu hình", f"Không đọc được cấu hình đã lưu. Dùng mặc định.\n{exc}", parent=self)

    def _save_settings(self):
        values = self._collect_settings()
        if values == self._saved_values:
            return True
        try:
            save_settings(values)
            self._saved_values = values
            self._settings_error_shown = False
            self.lbl_save_status.configure(text="Đã lưu trên máy", text_color=MUTED)
            return True
        except (OSError, ValueError) as exc:
            if not self._settings_error_shown:
                self._settings_error_shown = True
                self.lbl_save_status.configure(text="Không lưu được cấu hình", text_color="#F9A58B")
                messagebox.showerror("Cấu hình", f"Không lưu được cấu hình.\n{exc}", parent=self)
            return False

    def _autosave_settings(self):
        self._save_settings()
        self._autosave_id = self.after(1000, self._autosave_settings)

    def _close_window(self):
        if not self._save_settings():
            return
        self.stop_event.set()
        self.after_cancel(self._autosave_id)
        sys.stdout = sys.__stdout__
        sys.stderr = _real_stderr
        self.destroy()

    # ═══════════════════════════════════════════════════════════════
    # SIDEBAR
    # ═══════════════════════════════════════════════════════════════

    def _setup_tab_loop(self):
        t = self.tab_loop

        self.chk_loop = ctk.CTkCheckBox(
            t, text="Tự động chạy phiên tiếp theo (AUTO LOOP)",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.chk_loop.grid(row=0, column=0, sticky="w", padx=20, pady=(20, 8))
        if cfg.LOOP_ENABLE:
            self.chk_loop.select()

        ctk.CTkLabel(t, text="Thời lượng chạy có giới hạn · phút").grid(row=1, column=0, sticky="w", padx=40)
        self.entry_loop_time = ctk.CTkEntry(t, width=140, placeholder_text="VD: 120")
        self.entry_loop_time.insert(0, str(getattr(cfg, "LOOP_DURATION_MINUTES", 120)))
        self.entry_loop_time.grid(row=2, column=0, sticky="w", padx=40, pady=6)

        self.chk_new_user = ctk.CTkCheckBox(t, text="Luôn dùng User mới (xóa cookie sau mỗi phiên)")
        if cfg.ALWAYS_NEW_USER:
            self.chk_new_user.select()
        self.chk_new_user.grid(row=3, column=0, sticky="w", padx=20, pady=(20, 8))

        ctk.CTkLabel(
            t, text="Mỗi luồng chạy độc lập. Tắt AUTO LOOP để mỗi luồng chỉ chạy một phiên.",
            text_color="gray", font=ctk.CTkFont(size=11),
        ).grid(row=4, column=0, sticky="w", padx=20, pady=8)
        self.chk_continuous = ctk.CTkCheckBox(
            t, text="Chạy liên tục đến khi nhấn Dừng (không nghỉ / không giới hạn phiên)",
            command=self._continuous_changed,
        )
        self.chk_continuous.grid(row=5, column=0, sticky="w", padx=20, pady=8)
        if cfg.LOOP_CONTINUOUS:
            self.chk_continuous.select()
        self._continuous_changed()

    def _continuous_changed(self):
        continuous = bool(self.chk_continuous.get())
        if continuous:
            self.chk_loop.select()
        self.entry_loop_time.configure(state="disabled" if continuous else "normal")

    # ═══════════════════════════════════════════════════════════════
    # TAB: THIẾT BỊ
    # ═══════════════════════════════════════════════════════════════

    def _setup_tab_browser(self):
        t = self.tab_browser

        ctk.CTkLabel(t, text="Thiết bị giả lập:").grid(row=0, column=0, sticky="w", padx=20, pady=(20, 4))
        self.combo_device = ctk.CTkComboBox(t, values=cfg.SUPPORTED_DEVICES, width=260)
        # Dùng giá trị từ cfg.DEVICE_NAME, fallback về item đầu tiên trong list
        default_device = cfg.DEVICE_NAME if cfg.DEVICE_NAME in cfg.SUPPORTED_DEVICES else cfg.SUPPORTED_DEVICES[0]
        self.combo_device.set(default_device)
        self.combo_device.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 20))

        self.sw_headless = ctk.CTkSwitch(t, text="Chạy Ngầm (Headless Mode)")
        if cfg.HEADLESS_MODE:
            self.sw_headless.select()
        self.sw_headless.grid(row=2, column=0, sticky="w", padx=20, pady=10)

        self.sw_images = ctk.CTkSwitch(t, text="Tải Hình Ảnh (tắt để nhanh hơn)")
        if cfg.LOAD_IMAGES:
            self.sw_images.select()
        self.sw_images.grid(row=3, column=0, sticky="w", padx=20, pady=10)

    # ═══════════════════════════════════════════════════════════════
    # TAB: HÀNH VI SEO
    # ═══════════════════════════════════════════════════════════════

    def _setup_tab_behavior(self):
        t = self.tab_behavior

        # Thời gian trên site
        ctk.CTkLabel(t, text="⏱  Thời gian xem trang (giây):",
                     font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=4, sticky="w", padx=14, pady=(14, 6))
        dur_f = ctk.CTkFrame(t, fg_color="transparent")
        dur_f.grid(row=1, column=0, columnspan=4, sticky="w", padx=20)
        ctk.CTkLabel(dur_f, text="Min:").pack(side="left")
        self.entry_min_time = ctk.CTkEntry(dur_f, width=70)
        self.entry_min_time.insert(0, str(cfg.DURATION_MIN))
        self.entry_min_time.pack(side="left", padx=(4, 14))
        ctk.CTkLabel(dur_f, text="Max:").pack(side="left")
        self.entry_max_time = ctk.CTkEntry(dur_f, width=70)
        self.entry_max_time.insert(0, str(cfg.DURATION_MAX))
        self.entry_max_time.pack(side="left", padx=4)

        ctk.CTkFrame(t, height=1, fg_color="#333").grid(row=2, column=0, columnspan=4, sticky="ew", padx=14, pady=12)

        # Hành vi SERP
        ctk.CTkLabel(t, text="🔍  Hành vi tìm kiếm Google:",
                     font=ctk.CTkFont(weight="bold")).grid(row=3, column=0, columnspan=4, sticky="w", padx=14, pady=(0, 8))

        self.chk_pogo = ctk.CTkCheckBox(
            t, text="Pogo-stick đối thủ  (click đối thủ → back → mới vào site mình)")
        if cfg.POGO_STICK_ENABLE:
            self.chk_pogo.select()
        self.chk_pogo.grid(row=4, column=0, columnspan=4, sticky="w", padx=28, pady=4)

        pf = ctk.CTkFrame(t, fg_color="transparent")
        pf.grid(row=5, column=0, columnspan=4, sticky="w", padx=48, pady=(0, 6))
        ctk.CTkLabel(pf, text="Số lần tối đa:").pack(side="left")
        self.slider_pogo = ctk.CTkSlider(
            pf, from_=0, to=2, number_of_steps=2, width=110,
            command=lambda v: self.lbl_pogo_val.configure(text=f"{int(v)}"),
        )
        self.slider_pogo.set(cfg.POGO_STICK_MAX)
        self.slider_pogo.pack(side="left", padx=8)
        self.lbl_pogo_val = ctk.CTkLabel(pf, text=str(cfg.POGO_STICK_MAX), width=16)
        self.lbl_pogo_val.pack(side="left")
        ctk.CTkLabel(pf, text="lần", text_color="gray").pack(side="left", padx=4)

        self.chk_warmup_search = ctk.CTkCheckBox(
            t, text="Warm-up trước Google  (ghé trang VN phù hợp persona vài chục giây)")
        if cfg.WARMUP_SEARCH_ENABLE:
            self.chk_warmup_search.select()
        self.chk_warmup_search.grid(row=6, column=0, columnspan=4, sticky="w", padx=28, pady=4)

        self.chk_kw_variation = ctk.CTkCheckBox(
            t, text="Thử từ khóa biến thể trước  (25% — mô phỏng gõ sai rồi sửa lại)")
        if cfg.KEYWORD_VARIATION_ENABLE:
            self.chk_kw_variation.select()
        self.chk_kw_variation.grid(row=7, column=0, columnspan=4, sticky="w", padx=28, pady=4)

        ctk.CTkFrame(t, height=1, fg_color="#333").grid(row=8, column=0, columnspan=4, sticky="ew", padx=14, pady=12)

        # Hành vi trên site
        ctk.CTkLabel(t, text="🌐  Hành vi trên site đích:",
                     font=ctk.CTkFont(weight="bold")).grid(row=9, column=0, columnspan=4, sticky="w", padx=14, pady=(0, 8))

        self.chk_third_page = ctk.CTkCheckBox(t, text="Ghé thêm trang thứ 3  (tăng pages/session)")
        if cfg.THIRD_PAGE_ENABLE:
            self.chk_third_page.select()
        self.chk_third_page.grid(row=10, column=0, columnspan=4, sticky="w", padx=28, pady=4)

        tf = ctk.CTkFrame(t, fg_color="transparent")
        tf.grid(row=11, column=0, columnspan=4, sticky="w", padx=48, pady=(0, 8))
        ctk.CTkLabel(tf, text="Xác suất:").pack(side="left")
        self.slider_third_page = ctk.CTkSlider(
            tf, from_=10, to=70, number_of_steps=12, width=140,
            command=lambda v: self.lbl_third_val.configure(text=f"{int(v)}%"),
        )
        self.slider_third_page.set(cfg.THIRD_PAGE_CHANCE)
        self.slider_third_page.pack(side="left", padx=8)
        self.lbl_third_val = ctk.CTkLabel(tf, text=f"{cfg.THIRD_PAGE_CHANCE}%", width=38)
        self.lbl_third_val.pack(side="left")

    # ═══════════════════════════════════════════════════════════════
    # TAB: AI ENGINE
    # ═══════════════════════════════════════════════════════════════

    def _setup_tab_ai(self):
        t = self.tab_ai

        ctk.CTkLabel(t, text="Kết nối nhà cung cấp AI",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, columnspan=3, sticky="w", padx=14, pady=(16, 10))

        ctk.CTkLabel(t, text="Nhà cung cấp:").grid(row=1, column=0, sticky="w", padx=14, pady=(0, 4))
        self.combo_ai_provider = ctk.CTkComboBox(
            t, values=["gemini", "aibox", "maxmorus", "local"], width=180,
            state="readonly", command=self._select_ai_provider,
        )
        self.combo_ai_provider.set(cfg.AI_PROVIDER)
        self.combo_ai_provider.grid(row=2, column=0, sticky="w", padx=14)
        common_widgets = set(t.winfo_children())

        ctk.CTkLabel(t, text="Gemini model:").grid(row=1, column=1, sticky="w", padx=14, pady=(0, 4))
        self.entry_gemini_model = ctk.CTkEntry(t, width=220)
        self.entry_gemini_model.insert(0, cfg.GEMINI_MODEL)
        self.entry_gemini_model.grid(row=2, column=1, sticky="w", padx=14)

        ctk.CTkLabel(t, text="Gemini API key (lưu mã hóa trên máy):").grid(row=3, column=0, columnspan=2, sticky="w", padx=14, pady=(12, 4))
        self.entry_gemini_key = ctk.CTkEntry(t, width=470, show="•")
        self.entry_gemini_key.insert(0, cfg.GEMINI_API_KEY)
        self.entry_gemini_key.grid(row=4, column=0, columnspan=2, sticky="w", padx=14)

        gf = ctk.CTkFrame(t, fg_color="transparent")
        gf.grid(row=5, column=0, columnspan=3, sticky="w", padx=14, pady=10)
        self.btn_test_gemini = ctk.CTkButton(
            gf, text="🔌 Kiểm tra Gemini", width=170,
            command=self.test_gemini_connection,
        )
        self.btn_test_gemini.pack(side="left")
        self.lbl_gemini_status = ctk.CTkLabel(gf, text="● Chưa kiểm tra", text_color="gray")
        self.lbl_gemini_status.pack(side="left", padx=14)
        gemini_widgets = set(t.winfo_children()) - common_widgets

        ctk.CTkLabel(t, text="Model AI Box").grid(row=6, column=0, sticky="w", padx=14, pady=(12, 4))
        ctk.CTkLabel(t, text="API key · lưu mã hóa trên máy").grid(row=6, column=1, sticky="w", padx=14, pady=(12, 4))
        self.entry_aibox_model = ctk.CTkEntry(t, width=220)
        self.entry_aibox_model.insert(0, cfg.AIBOX_MODEL)
        self.entry_aibox_model.grid(row=7, column=0, padx=14, sticky="w")
        self.entry_aibox_key = ctk.CTkEntry(t, width=300, show="•", placeholder_text="Nhập API key của bạn")
        self.entry_aibox_key.insert(0, cfg.AIBOX_API_KEY)
        self.entry_aibox_key.grid(row=7, column=1, padx=14, sticky="w")
        ctk.CTkLabel(t, text="AI Box chat completions URL:").grid(row=8, column=0, columnspan=2, sticky="w", padx=14)
        self.entry_aibox_url = ctk.CTkEntry(t, width=470)
        self.entry_aibox_url.insert(0, cfg.AIBOX_API_URL)
        self.entry_aibox_url.grid(row=9, column=0, columnspan=2, padx=14, sticky="w")
        self.btn_test_aibox = ctk.CTkButton(t, text="Kiểm tra AI Box", command=self.test_aibox_connection)
        self.btn_test_aibox.grid(row=10, column=0, padx=14, pady=6, sticky="w")
        self.lbl_aibox_status = ctk.CTkLabel(t, text="Chưa kiểm tra", text_color="gray")
        self.lbl_aibox_status.grid(row=10, column=1, padx=14, sticky="w")
        aibox_widgets = set(t.winfo_children()) - common_widgets - gemini_widgets

        ctk.CTkLabel(t, text="Model MaxMorus").grid(row=6, column=0, sticky="w", padx=14, pady=(12, 4))
        ctk.CTkLabel(t, text="API key · lưu mã hóa trên máy").grid(row=6, column=1, sticky="w", padx=14, pady=(12, 4))
        self.entry_maxmorus_model = ctk.CTkEntry(t, width=220)
        self.entry_maxmorus_model.insert(0, cfg.MAXMORUS_MODEL)
        self.entry_maxmorus_model.grid(row=7, column=0, padx=14, sticky="w")
        self.entry_maxmorus_key = ctk.CTkEntry(t, width=300, show="•", placeholder_text="Nhập API key của bạn")
        self.entry_maxmorus_key.insert(0, cfg.MAXMORUS_API_KEY)
        self.entry_maxmorus_key.grid(row=7, column=1, padx=14, sticky="w")
        ctk.CTkLabel(t, text="MaxMorus chat completions URL:").grid(row=8, column=0, columnspan=2, sticky="w", padx=14)
        self.entry_maxmorus_url = ctk.CTkEntry(t, width=470)
        self.entry_maxmorus_url.insert(0, cfg.MAXMORUS_API_URL)
        self.entry_maxmorus_url.grid(row=9, column=0, columnspan=2, padx=14, sticky="w")
        self.btn_test_maxmorus = ctk.CTkButton(t, text="Kiểm tra MaxMorus", command=self.test_maxmorus_connection)
        self.btn_test_maxmorus.grid(row=10, column=0, padx=14, pady=6, sticky="w")
        self.lbl_maxmorus_status = ctk.CTkLabel(t, text="Chưa kiểm tra", text_color="gray")
        self.lbl_maxmorus_status.grid(row=10, column=1, padx=14, sticky="w")
        maxmorus_widgets = set(t.winfo_children()) - common_widgets - gemini_widgets - aibox_widgets

        ctk.CTkFrame(t, height=1, fg_color="#333").grid(row=12, column=0, columnspan=3, sticky="ew", padx=14, pady=6)
        ctk.CTkLabel(t, text="Local dùng bộ sinh Python. Ollama bên dưới chỉ để kiểm tra kết nối.",
                     font=ctk.CTkFont(size=12, weight="bold")).grid(row=13, column=0, columnspan=2, sticky="w", padx=14, pady=(4, 8))

        ctk.CTkLabel(t, text="Ollama URL:").grid(row=14, column=0, sticky="w", padx=14, pady=(0, 4))
        self.entry_ollama_url = ctk.CTkEntry(t, width=380)
        self.entry_ollama_url.insert(0, cfg.OLLAMA_URL)
        self.entry_ollama_url.grid(row=15, column=0, sticky="w", padx=14)

        ctk.CTkLabel(t, text="Model:").grid(row=14, column=1, sticky="w", padx=14, pady=(0, 4))
        self.combo_model = ctk.CTkComboBox(t, values=[
            "qwen3:30b-a3b",
            "qwen3:8b",
            "gemma3:12b",
            "qwen2.5:7b",
            "qwen2.5-coder:7b",
            "qwen2.5-coder:14b",
            "llama3.1:8b",
            "mistral:7b",
        ], width=260)
        self.combo_model.set(cfg.OLLAMA_MODEL)
        self.combo_model.grid(row=15, column=1, sticky="w", padx=14)

        bf = ctk.CTkFrame(t, fg_color="transparent")
        bf.grid(row=16, column=0, columnspan=3, sticky="w", padx=14, pady=10)
        self.btn_test_ollama = ctk.CTkButton(
            bf, text="🔌  Kiểm tra kết nối Ollama", width=220,
            command=self.test_ollama_connection,
        )
        self.btn_test_ollama.pack(side="left")
        self.btn_refresh_models = ctk.CTkButton(
            bf, text="Refresh model list", width=130,
            command=self.refresh_ollama_models,
        )
        self.btn_refresh_models.pack(side="left", padx=6)
        self.lbl_ollama_status = ctk.CTkLabel(bf, text="● Chưa kiểm tra", text_color="gray")
        self.lbl_ollama_status.pack(side="left", padx=14)
        local_widgets = set(t.winfo_children()) - common_widgets - gemini_widgets - aibox_widgets - maxmorus_widgets
        self._ai_provider_widgets = {
            "gemini": gemini_widgets, "aibox": aibox_widgets, "maxmorus": maxmorus_widgets, "local": local_widgets,
        }
        self._select_ai_provider(self.combo_ai_provider.get())

        info = (
            "Chỉ provider được chọn được dùng khi bắt đầu chạy.\n"
            "Nếu API key thiếu hoặc request lỗi, ứng dụng tự dùng local fallback."
        )
        ctk.CTkLabel(t, text=info, justify="left", text_color="gray",
                     font=ctk.CTkFont(size=11)).grid(row=17, column=0, columnspan=3, sticky="w", padx=14, pady=4)

    def _select_ai_provider(self, provider):
        for name, widgets in self._ai_provider_widgets.items():
            for widget in widgets:
                if name == provider:
                    widget.grid()
                else:
                    widget.grid_remove()

    # ═══════════════════════════════════════════════════════════════
    # TAB: NUÔI NICK
    # ═══════════════════════════════════════════════════════════════

    def _setup_tab_warmup(self):
        t = self.tab_warmup

        self.chk_warmup = ctk.CTkCheckBox(
            t, text="Duyệt các trang khởi động trước mỗi phiên",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        if cfg.WARMUP_ENABLE:
            self.chk_warmup.select()
        self.chk_warmup.grid(row=0, column=0, sticky="w", padx=20, pady=(20, 12))

        ctk.CTkLabel(t, text="Loại trang warm-up:", text_color="gray").grid(row=1, column=0, sticky="w", padx=20, pady=(0, 8))

        self.chk_ytb = ctk.CTkCheckBox(t, text="YouTube  (xem video ngắn)")
        if cfg.WARMUP_YOUTUBE:
            self.chk_ytb.select()
        self.chk_ytb.grid(row=2, column=0, sticky="w", padx=44, pady=4)

        self.chk_news = ctk.CTkCheckBox(t, text="Đọc Báo  (vnexpress, dantri...)")
        if cfg.WARMUP_NEWS:
            self.chk_news.select()
        self.chk_news.grid(row=3, column=0, sticky="w", padx=44, pady=4)

        self.chk_wiki = ctk.CTkCheckBox(t, text="Wikipedia")
        if cfg.WARMUP_WIKIPEDIA:
            self.chk_wiki.select()
        self.chk_wiki.grid(row=4, column=0, sticky="w", padx=44, pady=4)

        self.chk_shop = ctk.CTkCheckBox(t, text="Shopping  (shopee, lazada...)")
        if cfg.WARMUP_SHOPPING:
            self.chk_shop.select()
        self.chk_shop.grid(row=5, column=0, sticky="w", padx=44, pady=4)

        self.chk_fb = ctk.CTkCheckBox(t, text="Facebook")
        if cfg.WARMUP_FACEBOOK:
            self.chk_fb.select()
        self.chk_fb.grid(row=6, column=0, sticky="w", padx=44, pady=4)

        self.chk_ig = ctk.CTkCheckBox(t, text="Instagram")
        if cfg.WARMUP_INSTAGRAM:
            self.chk_ig.select()
        self.chk_ig.grid(row=7, column=0, sticky="w", padx=44, pady=4)

        ctk.CTkLabel(
            t,
            text=(
                "ℹ️  Nuôi Nick khác với Warm-up trước Google (tab Hành Vi SEO).\n"
                "    Nuôi Nick chạy trước toàn bộ task — xây dựng lịch sử duyệt web dài hạn.\n"
                "    Warm-up trước Google chỉ ghé 1 trang VN ngắn ngay trước khi search."
            ),
            text_color="gray", font=ctk.CTkFont(size=11), justify="left",
        ).grid(row=8, column=0, sticky="w", padx=20, pady=20)

    # ═══════════════════════════════════════════════════════════════
    # GEMINI / OLLAMA TEST CONNECTION
    # ═══════════════════════════════════════════════════════════════

    def _apply_aibox_config(self):
        cfg.AIBOX_API_KEY = self.entry_aibox_key.get().strip()
        cfg.AIBOX_MODEL = self.entry_aibox_model.get().strip() or "deepseek-v4.1-flash"
        cfg.AIBOX_API_URL = self.entry_aibox_url.get().strip() or "https://api.ai-box.vn/v1/chat/completions"

    def test_aibox_connection(self):
        self._apply_aibox_config()
        self.btn_test_aibox.configure(state="disabled")
        self.lbl_aibox_status.configure(text="Đang kết nối...", text_color="yellow")
        threading.Thread(target=self._do_test_aibox, daemon=True).start()

    def _do_test_aibox(self):
        from utils.ai_engine import test_aibox_connection
        ok, detail = asyncio.run(test_aibox_connection())
        msg = "AI Box online" if ok else f"Lỗi: {detail[:70]}"
        color = "#00cc44" if ok else "#cc2222"
        def finish():
            self.lbl_aibox_status.configure(text=msg, text_color=color)
            self.lbl_ollama_sidebar.configure(text=msg, text_color=color)
            self.btn_test_aibox.configure(state="normal")
        self.after(0, finish)

    def _apply_maxmorus_config(self):
        cfg.MAXMORUS_API_KEY = self.entry_maxmorus_key.get().strip()
        cfg.MAXMORUS_MODEL = self.entry_maxmorus_model.get().strip() or "cl/deepseek/deepseek-v4.1-flash"
        cfg.MAXMORUS_API_URL = self.entry_maxmorus_url.get().strip() or "https://ai.maxmorus.com/v1/chat/completions"

    def test_maxmorus_connection(self):
        self._apply_maxmorus_config()
        self.btn_test_maxmorus.configure(state="disabled")
        self.lbl_maxmorus_status.configure(text="Đang kết nối...", text_color="yellow")
        threading.Thread(target=self._do_test_maxmorus, daemon=True).start()

    def _do_test_maxmorus(self):
        from utils.ai_engine import test_maxmorus_connection
        ok, detail = asyncio.run(test_maxmorus_connection())
        msg = "MaxMorus online" if ok else f"Lỗi: {detail[:70]}"
        color = "#00cc44" if ok else "#cc2222"
        def finish():
            self.lbl_maxmorus_status.configure(text=msg, text_color=color)
            self.lbl_ollama_sidebar.configure(text=msg, text_color=color)
            self.btn_test_maxmorus.configure(state="normal")
        self.after(0, finish)

    def test_gemini_connection(self):
        cfg.GEMINI_API_KEY = self.entry_gemini_key.get().strip()
        cfg.GEMINI_MODEL = self.entry_gemini_model.get().strip() or "gemini-3.5-flash"
        self.btn_test_gemini.configure(state="disabled", text="Đang kiểm tra...")
        self.lbl_gemini_status.configure(text="● Đang kết nối...", text_color="yellow")
        threading.Thread(target=self._do_test_gemini, daemon=True).start()

    def _do_test_gemini(self):
        from utils.ai_engine import test_gemini_connection

        try:
            ok, detail = asyncio.run(test_gemini_connection())
            if ok:
                msg = f"● Gemini online ({cfg.GEMINI_MODEL})"
                color = "#00cc44"
            else:
                msg = f"● Lỗi: {detail[:55]}"
                color = "#cc2222"
            self.after(0, lambda: self.lbl_gemini_status.configure(text=msg, text_color=color))
            self.after(0, lambda: self.lbl_ollama_sidebar.configure(text=msg, text_color=color))
        finally:
            self.after(0, lambda: self.btn_test_gemini.configure(state="normal", text="🔌 Kiểm tra Gemini"))

    def test_ollama_connection(self):
        self.btn_test_ollama.configure(state="disabled", text="Đang kiểm tra...")
        self.lbl_ollama_status.configure(text="● Đang kết nối...", text_color="yellow")
        threading.Thread(target=self._do_test_ollama, daemon=True).start()

    def _do_test_ollama(self):
        base = self.entry_ollama_url.get().replace("/api/generate", "").rstrip("/")
        try:
            resp = requests.get(f"{base}/api/tags", timeout=5)
            if resp.status_code == 200:
                n = len(resp.json().get("models", []))
                msg_ok = f"● Kết nối thành công  ({n} model)"
                self.after(0, lambda: self.lbl_ollama_status.configure(text=msg_ok, text_color="#00cc44"))
                self.after(0, lambda: self.lbl_ollama_sidebar.configure(text=f"● Online ({n} model)", text_color="#00cc44"))
            else:
                raise ConnectionError(f"HTTP {resp.status_code}")
        except Exception as e:
            msg_err = f"● Lỗi: {str(e)[:38]}"
            self.after(0, lambda: self.lbl_ollama_status.configure(text=msg_err, text_color="#cc2222"))
            self.after(0, lambda: self.lbl_ollama_sidebar.configure(text="● Offline", text_color="#cc2222"))
        finally:
            self.after(0, lambda: self.btn_test_ollama.configure(state="normal", text="🔌  Kiểm tra kết nối Ollama"))

    # ═══════════════════════════════════════════════════════════════
    # SESSION COUNTER
    # ═══════════════════════════════════════════════════════════════

    
    def refresh_ollama_models(self):
        """L?y danh s�ch model t? Ollama server v� c?p nh?t dropdown."""
        base = self.entry_ollama_url.get().replace("/api/generate", "").rstrip("/")
        try:
            resp = requests.get(f"{base}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                if models:
                    self.combo_model.configure(values=models)
                    self.combo_model.set(models[0])
                    self.after(0, lambda: self.lbl_ollama_status.configure(
                        text=f"? {len(models)} models loaded", text_color="#00cc44"))
                else:
                    self.after(0, lambda: self.lbl_ollama_status.configure(
                        text="? Kh�ng c� model n�o", text_color="#cc2222"))
        except Exception as e:
            self.after(0, lambda e=e: self.lbl_ollama_status.configure(
                text=f"? L?i: {str(e)[:38]}", text_color="#cc2222"))
    def _inc_ok(self):
        self._session_ok += 1
        self.lbl_ok.configure(text=str(self._session_ok))

    def _inc_err(self):
        self._session_err += 1
        self.lbl_err.configure(text=str(self._session_err))

    def _reset_counters(self):
        self._session_ok = 0
        self._session_err = 0
        self.lbl_ok.configure(text="0")
        self.lbl_err.configure(text="0")

    # ═══════════════════════════════════════════════════════════════
    # LOGIC CHẠY
    # ═══════════════════════════════════════════════════════════════

    def start_thread(self):
        if self.is_running:
            return
        try:
            targets = parse_targets(
                self.entry_url.get().strip() + "\n" + self.txt_targets.get("1.0", "end-1c")
            )
            # The main URL is required independently of additional websites.
            parse_targets(self.entry_url.get().strip())
        except ValueError as exc:
            self.tabs.set("Website")
            self.entry_url.focus_set()
            messagebox.showerror(cfg.APP_NAME, str(exc), parent=self)
            return
        try:
            minimum, maximum = int(self.entry_min_time.get()), int(self.entry_max_time.get())
            if minimum <= 0 or maximum < minimum:
                raise ValueError()
        except ValueError:
            self.tabs.set("Tương tác")
            messagebox.showerror(cfg.APP_NAME, "Thời gian xem trang phải lớn hơn 0; tối đa không nhỏ hơn tối thiểu.", parent=self)
            return
        if self.chk_loop.get() and not self.chk_continuous.get():
            try:
                if int(self.entry_loop_time.get()) <= 0:
                    raise ValueError()
            except ValueError:
                self.tabs.set("Lịch chạy")
                messagebox.showerror(cfg.APP_NAME, "Nhập số phút lớn hơn 0 hoặc chọn chạy liên tục.", parent=self)
                return
        if not self._save_settings():
            return
        self.is_running = True
        self.stop_event.clear()
        self._reset_counters()
        self.update_ui_state(running=True)

        cfg.TARGET_URL   = targets[0]
        cfg.TARGET_URLS  = targets
        cfg.TRAFFIC_MODE = self.radio_var.get()

        kws = self.txt_keywords.get("0.0", "end").strip().split("\n")
        cfg.SEO_KEYWORDS = [k.strip() for k in kws if k.strip()]

        proxies = self.txt_proxy.get("0.0", "end").strip().split("\n")
        cfg.PROXY_LIST = [p.strip() for p in proxies if p.strip()]

        cfg.HEADLESS_MODE = bool(self.sw_headless.get())
        cfg.LOAD_IMAGES   = bool(self.sw_images.get())

        dev = self.combo_device.get()
        cfg.DEVICE_NAME   = dev
        cfg.VIEWPORT_SIZE = {"width": 1920, "height": 1080} if "Desktop" in dev else {"width": 390, "height": 844}

        try:
            min_val = int(self.entry_min_time.get())
            max_val = int(self.entry_max_time.get())
            cfg.DURATION_MIN = min(min_val, max_val)
            cfg.DURATION_MAX = max(min_val, max_val)
        except ValueError:
            cfg.DURATION_MIN, cfg.DURATION_MAX = 60, 120

        cfg.LOOP_ENABLE = bool(self.chk_loop.get())
        cfg.LOOP_CONTINUOUS = bool(self.chk_continuous.get())
        try:
            cfg.LOOP_DURATION_MINUTES = int(self.entry_loop_time.get())
        except ValueError:
            cfg.LOOP_DURATION_MINUTES = 60
        cfg.ALWAYS_NEW_USER = bool(self.chk_new_user.get())

        cfg.WARMUP_ENABLE    = bool(self.chk_warmup.get())
        cfg.WARMUP_YOUTUBE   = bool(self.chk_ytb.get())
        cfg.WARMUP_NEWS      = bool(self.chk_news.get())
        cfg.WARMUP_WIKIPEDIA = bool(self.chk_wiki.get())
        cfg.WARMUP_SHOPPING  = bool(self.chk_shop.get())
        cfg.WARMUP_FACEBOOK  = bool(self.chk_fb.get())
        cfg.WARMUP_INSTAGRAM = bool(self.chk_ig.get())

        # AI Engine
        cfg.AI_PROVIDER  = self.combo_ai_provider.get().strip().lower()
        if cfg.AI_PROVIDER == "aibox":
            self._apply_aibox_config()
        elif cfg.AI_PROVIDER == "maxmorus":
            self._apply_maxmorus_config()
        elif cfg.AI_PROVIDER == "gemini":
            cfg.GEMINI_API_KEY = self.entry_gemini_key.get().strip()
            cfg.GEMINI_MODEL = self.entry_gemini_model.get().strip() or "gemini-3.5-flash"

        # Hành Vi SEO
        cfg.POGO_STICK_ENABLE        = bool(self.chk_pogo.get())
        cfg.POGO_STICK_MAX           = int(self.slider_pogo.get())
        cfg.WARMUP_SEARCH_ENABLE     = bool(self.chk_warmup_search.get())
        cfg.KEYWORD_VARIATION_ENABLE = bool(self.chk_kw_variation.get())
        cfg.THIRD_PAGE_ENABLE        = bool(self.chk_third_page.get())
        cfg.THIRD_PAGE_CHANCE        = int(self.slider_third_page.get())

        threads = int(self.slider_threads.get())
        threading.Thread(target=self.run_async_loop, args=(threads,), daemon=True).start()

    def stop_process(self):
        if not self.is_running:
            return
        print("\n[🛑] ĐANG DỪNG... (Chờ các luồng hiện tại chạy xong)")
        self.stop_event.set()
        self.btn_stop.configure(state="disabled", text="Đang dừng…")
        self.lbl_status.configure(text="●  Đang kết thúc phiên", text_color="#F9C97B")

    def update_ui_state(self, running: bool):
        if running:
            self.btn_start.configure(state="disabled", text="Đang chạy", fg_color="#245448")
            self.btn_stop.configure(state="normal", text="Dừng sau thao tác hiện tại", fg_color="#613A40")
            self.lbl_status.configure(text="●  Đang hoạt động", text_color=ACCENT)
        else:
            self.btn_start.configure(state="normal", text="Bắt đầu chạy", fg_color=ACCENT)
            self.btn_stop.configure(state="disabled", text="Dừng sau thao tác hiện tại", fg_color="#121D30")
            self.lbl_status.configure(text="●  Đã dừng", text_color=MUTED)
            self.lbl_timer.configure(text="Sẵn sàng cho lần chạy mới")

    def run_async_loop(self, max_tabs: int):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.main_logic(max_tabs))
        loop.close()
        self.is_running = False
        self.after(0, lambda: self.update_ui_state(running=False))

    async def process_single_session(self, manager, browser, proxy, worker_id: int):
        # Rate limiter - toi da 25 session/ngay
        if self.stop_event.is_set():
            return
        from utils.rate_limiter import acquire_session
        continuous = cfg.LOOP_ENABLE and cfg.LOOP_CONTINUOUS
        limits = {"max_per_day": 0, "min_interval": 0} if continuous else {}
        allowed, reason = acquire_session(scope=f"worker-{worker_id}", **limits)
        if not allowed:
            print(f"[W{worker_id}] [RATE] {reason}")
            return
        page = None
        succeeded = False
        try:
            if cfg.ALWAYS_NEW_USER:
                p_id   = f"{proxy or 'Local'}_{uuid.uuid4().hex[:8]}"
                label  = "🆕 New"
            else:
                p_id   = proxy or f"Local_W{worker_id}"
                label  = "♻️ Returning"

            print(f"[W{worker_id}] 🚀 Mở Tab ({label}) | Proxy: {proxy or 'None'}")
            page = await manager.create_context(browser, proxy_info=proxy, profile_id=p_id)

            if cfg.WARMUP_ENABLE:
                modes = [m for m, flag in [
                    ("youtube",  cfg.WARMUP_YOUTUBE),
                    ("news",     cfg.WARMUP_NEWS),
                    ("wiki",     cfg.WARMUP_WIKIPEDIA),
                    ("shopping", cfg.WARMUP_SHOPPING),
                    ("facebook", cfg.WARMUP_FACEBOOK),
                    ("instagram", cfg.WARMUP_INSTAGRAM),
                ] if flag]
                if modes:
                    from scenarios.warmup import run_warmup
                    await run_warmup(page, modes)

            if not self.stop_event.is_set():
                mode = getattr(cfg, "TRAFFIC_MODE", "direct")
                targets = list(getattr(cfg, "TARGET_URLS", None) or [cfg.TARGET_URL])
                succeeded = True
                for index, target in enumerate(targets, 1):
                    if self.stop_event.is_set():
                        succeeded = False
                        break
                    session_duration = random.randint(cfg.DURATION_MIN, cfg.DURATION_MAX)
                    print(f"[W{worker_id}] 🌐 Website {index}/{len(targets)}: {target}")
                    token = current_target.set(target)
                    try:
                        target_mode = mode
                        if mode == "mix":
                            r = random.random()
                            target_mode = "search" if r < 0.4 else "aio" if r < 0.7 else "direct"
                        if target_mode == "search":
                            from tests.test_search_flow import run_search_flow
                            target_ok = await run_search_flow(page, session_duration, stop_event=self.stop_event)
                        elif target_mode == "aio":
                            from scenarios.aio_traffic import run_aio_session
                            target_ok = await run_aio_session(page, stop_event=self.stop_event)
                        else:
                            target_ok = await run_deep_session(page, session_duration)
                        succeeded = bool(target_ok) and succeeded
                        print(f"[W{worker_id}] {'✅' if target_ok else '❌'} Website {index}/{len(targets)}: {target}")
                    except Exception as exc:
                        succeeded = False
                        print(f"[W{worker_id}] ❌ Website {target}: {exc}")
                    finally:
                        current_target.reset(token)

            if succeeded:
                print(f"[W{worker_id}] ✅ Hoàn thành phiên.")
                self.after(0, self._inc_ok)
            else:
                print(f"[W{worker_id}] ❌ Phiên không đạt mục tiêu.")
                self.after(0, self._inc_err)

        except Exception as e:
            print(f"[W{worker_id}] ❌ Lỗi: {e}")
            self.after(0, self._inc_err)
        finally:
            if page:
                try:
                    context = page.context
                    state_file = getattr(context, "_seo_state_file", None)
                    if state_file and not cfg.ALWAYS_NEW_USER:
                        await context.storage_state(path=state_file)
                    await context.close()
                except Exception:
                    pass
    async def continuous_worker(self, manager, browser, proxy_iter, worker_id: int, end_time: float):
        # Stagger: moi luong cach nhau 10-30s
        stagger = 0 if cfg.LOOP_CONTINUOUS else random.randint(cfg.THREAD_STAGGER_MIN, cfg.THREAD_STAGGER_MAX)
        print(f"[W{worker_id}] Cho {stagger}s de tranh phat hien...")
        await asyncio.sleep(stagger)

        while time.time() < end_time and not self.stop_event.is_set():
            proxy = next(proxy_iter)
            await self.process_single_session(manager, browser, proxy, worker_id)
            if self.stop_event.is_set():
                break
            rest = 0 if cfg.LOOP_CONTINUOUS else random.randint(cfg.REST_BETWEEN_SESSIONS_MIN, cfg.REST_BETWEEN_SESSIONS_MAX)
            if rest:
                print(f"[W{worker_id}] 💤 Nghỉ {rest}s...")
            await asyncio.sleep(rest)

    async def main_logic(self, max_tabs: int):
        manager = BrowserManager()
        try:
            browser    = await manager.launch_browser()
            proxies    = cfg.PROXY_LIST or [None]
            proxy_iter = itertools.cycle(proxies)

            loop_minutes = cfg.LOOP_DURATION_MINUTES if cfg.LOOP_ENABLE and not cfg.LOOP_CONTINUOUS else None
            end_time = time.time() + loop_minutes * 60 if loop_minutes else float("inf")
            duration_label = ("liên tục đến khi nhấn Dừng" if cfg.LOOP_ENABLE and cfg.LOOP_CONTINUOUS
                              else f"{loop_minutes} phút" if loop_minutes else "mỗi worker 1 phiên")
            print(f"\n--- 🕒 BẮT ĐẦU: {duration_label} | {max_tabs} luồng | Mode: {cfg.TRAFFIC_MODE.upper()} ---")

            workers = []
            for i in range(max_tabs):
                await asyncio.sleep(random.uniform(0.5, 2.0))
                if cfg.LOOP_ENABLE:
                    task = self.continuous_worker(manager, browser, proxy_iter, i + 1, end_time)
                else:
                    task = self.process_single_session(manager, browser, next(proxy_iter), i + 1)
                workers.append(asyncio.create_task(task))

            while cfg.LOOP_ENABLE and time.time() < end_time and not self.stop_event.is_set():
                if end_time == float("inf"):
                    self.after(0, lambda: self.lbl_timer.configure(text="Chạy liên tục"))
                else:
                    remaining = max(0, int(end_time - time.time()))
                    m, s = divmod(remaining, 60)
                    self.after(0, lambda t=f"{m:02d}:{s:02d}": self.lbl_timer.configure(text=f"⏳ {t}"))
                await asyncio.sleep(1)

            if not cfg.LOOP_ENABLE:
                await asyncio.gather(*workers, return_exceptions=True)
                self.after(0, lambda: self.lbl_timer.configure(text="✅ HOÀN THÀNH"))
            elif self.stop_event.is_set():
                print("\n[🛑] Đã nhận lệnh dừng. Chờ các luồng đang chạy...")
            else:
                print("\n[🏁] Hết thời gian treo máy!")
                self.after(0, lambda: self.lbl_timer.configure(text="✅ HOÀN THÀNH"))

            if cfg.LOOP_ENABLE:
                await asyncio.gather(*workers, return_exceptions=True)

        except Exception as e:
            print(f"[CRITICAL] {e}")
        finally:
            await manager.close()


# Backward-compatible import for integrations and tests.
TrafficBotUI = ZizaSeoUI


if __name__ == "__main__":
    try:
        app = ZizaSeoUI()
        if "--smoke-test" in sys.argv:
            app.withdraw()
            app.update_idletasks()
            async def check_browser():
                from playwright.async_api import async_playwright
                async with async_playwright() as playwright:
                    browser = await playwright.chromium.launch(headless=True)
                    page = await browser.new_page()
                    await page.set_content("<title>ZizaSeo package check</title>")
                    assert await page.title() == "ZizaSeo package check"
                    await browser.close()
            asyncio.run(check_browser())
            app.after_cancel(app._autosave_id)
            app.destroy()
            _real_stderr.write("Packaged ZizaSeo UI and Chromium smoke test passed\n")
        else:
            app.mainloop()
    except Exception:
        msg = traceback.format_exc()
        _real_stderr.write(msg)
        with open("ui_error.log", "w", encoding="utf-8") as _f:
            _f.write(msg)
        sys.exit(1)
