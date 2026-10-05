"""ZizaSeo desktop layout and reusable visual styles."""
import customtkinter as ctk
import config.settings as cfg

BG = "#0B1120"
PANEL = "#121D30"
FIELD = "#0D1728"
BORDER = "#28364C"
TEXT = "#E6EDF7"
MUTED = "#9AAEC8"
ACCENT = "#27C9AE"


class ZizaLayout:
    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=244, corner_radius=0, fg_color=FIELD)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_columnconfigure(0, weight=1)
        sidebar.grid_rowconfigure(9, weight=1)
        brand = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand.grid(row=0, column=0, padx=22, pady=(28, 6), sticky="w")
        ctk.CTkLabel(brand, text="Z", width=40, height=40, corner_radius=12,
                     fg_color=ACCENT, text_color=BG, font=("Segoe UI", 25, "bold")).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(brand, text="ZizaSeo", text_color=TEXT, font=("Segoe UI", 25, "bold")).pack(side="left")
        ctk.CTkLabel(sidebar, text="SEO WORKSPACE", text_color=MUTED,
                     font=("Segoe UI", 11)).grid(row=1, column=0, sticky="w", padx=24, pady=(0, 26))
        self.lbl_status = ctk.CTkLabel(sidebar, text="●  Sẵn sàng", text_color=ACCENT,
                                      fg_color=PANEL, corner_radius=10, height=38)
        self.lbl_status.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 12))
        self.btn_start = ctk.CTkButton(sidebar, text="Bắt đầu chạy", height=46,
                                       fg_color=ACCENT, hover_color="#1EAC96", text_color=BG,
                                       font=("Segoe UI", 14, "bold"), command=self.start_thread)
        self.btn_start.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 8))
        self.btn_stop = ctk.CTkButton(sidebar, text="Dừng sau thao tác hiện tại", height=40,
                                      fg_color=PANEL, hover_color="#3A2534", border_width=1,
                                      border_color=BORDER, state="disabled", command=self.stop_process)
        self.btn_stop.grid(row=4, column=0, sticky="ew", padx=20)
        self.lbl_timer = ctk.CTkLabel(sidebar, text="Chưa bắt đầu", text_color=MUTED,
                                     font=("Segoe UI", 13))
        self.lbl_timer.grid(row=5, column=0, padx=12, pady=(12, 24))
        stats = ctk.CTkFrame(sidebar, fg_color=PANEL, corner_radius=14)
        stats.grid(row=6, column=0, sticky="ew", padx=20)
        stats.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(stats, text="KẾT QUẢ LẦN CHẠY", text_color=MUTED, font=("Segoe UI", 10, "bold")).grid(row=0, column=0, columnspan=2, pady=(12, 8))
        self.lbl_ok = ctk.CTkLabel(stats, text="0", text_color=ACCENT, font=("Segoe UI", 28, "bold"))
        self.lbl_ok.grid(row=1, column=0)
        self.lbl_err = ctk.CTkLabel(stats, text="0", text_color="#F9A58B", font=("Segoe UI", 28, "bold"))
        self.lbl_err.grid(row=1, column=1)
        ctk.CTkLabel(stats, text="Hoàn thành", text_color=MUTED, font=("Segoe UI", 11)).grid(row=2, column=0, pady=(0, 14))
        ctk.CTkLabel(stats, text="Chưa đạt", text_color=MUTED, font=("Segoe UI", 11)).grid(row=2, column=1, pady=(0, 14))
        self.lbl_ollama_sidebar = ctk.CTkLabel(sidebar, text="AI · Chưa kiểm tra", text_color=MUTED,
                                              wraplength=195, font=("Segoe UI", 12))
        self.lbl_ollama_sidebar.grid(row=7, column=0, padx=20, pady=18)
        self.lbl_save_status = ctk.CTkLabel(sidebar, text="Tự động lưu trên máy", text_color=MUTED,
                                           font=("Segoe UI", 11), wraplength=200)
        self.lbl_save_status.grid(row=10, column=0, padx=20, pady=(8, 4))
        ctk.CTkLabel(sidebar, text="Ctrl + Enter  Bắt đầu\nEsc  Dừng  ·  Ctrl + S  Lưu", justify="left",
                     text_color=MUTED, font=("Segoe UI", 11)).grid(row=11, column=0, padx=20, pady=(4, 22))

    def _build_main_area(self):
        self.main_panel = main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew", padx=24, pady=18)
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=3, minsize=340)
        main.grid_rowconfigure(2, weight=1, minsize=170)
        header = ctk.CTkFrame(main, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        ctk.CTkLabel(header, text="Không gian làm việc", text_color=TEXT,
                     font=("Segoe UI", 26, "bold")).pack(anchor="w")
        ctk.CTkLabel(header, text="Thiết lập website, chọn cách chạy và theo dõi mọi phiên tại một nơi.",
                     text_color=MUTED, font=("Segoe UI", 12)).pack(anchor="w", pady=(2, 0))
        self.tabs = ctk.CTkTabview(main, fg_color=PANEL, corner_radius=16,
                                  segmented_button_fg_color=FIELD, segmented_button_selected_color="#245448",
                                  segmented_button_selected_hover_color="#2D6859",
                                  segmented_button_unselected_color=FIELD,
                                  segmented_button_unselected_hover_color=BORDER,
                                  text_color=TEXT, anchor="w", height=460)
        self.tabs.grid(row=1, column=0, sticky="nsew")
        sections = [
            ("tab_general", "Website", self._setup_tab_general),
            ("tab_loop", "Lịch chạy", self._setup_tab_loop),
            ("tab_browser", "Trình duyệt", self._setup_tab_browser),
            ("tab_behavior", "Tương tác", self._setup_tab_behavior),
            ("tab_ai", "Kết nối AI", self._setup_tab_ai),
            ("tab_warmup", "Khởi động", self._setup_tab_warmup),
        ]
        for attribute, title, setup in sections:
            tab = self.tabs.add(title)
            content = ctk.CTkScrollableFrame(tab, fg_color="transparent", corner_radius=0)
            content.pack(fill="both", expand=True)
            setattr(self, attribute, content)
            setup()
            self._style_fields(content)
        self.log_frame = log = ctk.CTkFrame(main, fg_color=PANEL, corner_radius=14)
        log.grid(row=2, column=0, sticky="nsew", pady=(16, 0))
        log.grid_columnconfigure(0, weight=1)
        log.grid_rowconfigure(1, weight=1)
        header = ctk.CTkFrame(log, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=10)
        ctk.CTkLabel(header, text="Nhật ký hoạt động", font=("Segoe UI", 13, "bold"), text_color=TEXT).pack(side="left")
        self.btn_log_toggle = ctk.CTkButton(header, text="Thu gọn", width=82, height=28,
                                           fg_color=BORDER, command=self._toggle_log)
        self.btn_log_toggle.pack(side="right", padx=(8, 0))
        for label, command in [("Xóa", self._clear_log), ("Sao chép", self._copy_log)]:
            ctk.CTkButton(header, text=label, width=74, height=28, fg_color=BORDER,
                          hover_color="#3D5069", command=command).pack(side="right", padx=(8, 0))
        self.chk_follow_log = ctk.CTkCheckBox(header, text="Cuộn tự động", width=115,
                                            checkbox_width=16, checkbox_height=16, font=("Segoe UI", 11),
                                            fg_color=ACCENT, text_color=MUTED)
        self.chk_follow_log.select()
        self.chk_follow_log.pack(side="right", padx=14)
        self.txt_log = ctk.CTkTextbox(log, height=150, font=("Consolas", 12), fg_color=FIELD,
                                     text_color="#BDCEE3", corner_radius=10, state="disabled", wrap="word")
        self.txt_log.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self._log_visible = True

    def _style_fields(self, parent):
        for widget in parent.winfo_children():
            if isinstance(widget, ctk.CTkEntry):
                widget.configure(height=38, corner_radius=8, fg_color=FIELD, border_color=BORDER, text_color=TEXT)
            elif isinstance(widget, ctk.CTkComboBox):
                widget.configure(height=38, corner_radius=8, fg_color=FIELD, border_color=BORDER,
                                 button_color=BORDER, dropdown_fg_color=PANEL, text_color=TEXT)
            elif isinstance(widget, ctk.CTkTextbox):
                widget.configure(fg_color=FIELD, text_color=TEXT, border_width=1, border_color=BORDER, corner_radius=10)
            elif isinstance(widget, (ctk.CTkCheckBox, ctk.CTkRadioButton)):
                widget.configure(fg_color=ACCENT, hover_color="#1EAC96", text_color=TEXT)
            elif isinstance(widget, (ctk.CTkSlider, ctk.CTkSwitch)):
                widget.configure(progress_color=ACCENT, button_color="#D1FAF2", button_hover_color=ACCENT)
            elif isinstance(widget, ctk.CTkButton):
                widget.configure(fg_color="#245448", hover_color="#2D6859", height=34)
            elif isinstance(widget, ctk.CTkLabel) and widget.cget("text_color") == "gray":
                widget.configure(text_color=MUTED)
            if isinstance(widget, ctk.CTkLabel) and len(widget.cget("text")) > 80:
                widget.configure(wraplength=620, justify="left")
            self._style_fields(widget)

    def _setup_tab_general(self):
        t = self.tab_general
        t.grid_columnconfigure((0, 1), weight=1, uniform="website")
        ctk.CTkLabel(t, text="Website đích", font=("Segoe UI", 16, "bold"), text_color=TEXT).grid(row=0, column=0, sticky="w", padx=14, pady=(14, 8))
        self.entry_url = ctk.CTkEntry(t, placeholder_text="https://example.com", width=320)
        self.entry_url.insert(0, cfg.TARGET_URL)
        self.entry_url.grid(row=1, column=0, columnspan=2, sticky="ew", padx=14)
        ctk.CTkLabel(t, text="Website đích bổ sung · mỗi dòng một URL; mỗi phiên ghé tất cả", text_color=MUTED).grid(row=8, column=0, columnspan=2, sticky="w", padx=14, pady=(8, 6))
        self.txt_targets = ctk.CTkTextbox(t, height=120)
        self.txt_targets.grid(row=9, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 16))
        self.txt_targets.insert("1.0", "\n".join(getattr(cfg, "TARGET_URLS", [])[1:]))
        ctk.CTkLabel(t, text="Cách truy cập", text_color=MUTED).grid(row=2, column=0, sticky="w", padx=14, pady=(16, 6))
        self.radio_var = ctk.StringVar(value=cfg.TRAFFIC_MODE)
        modes = ctk.CTkFrame(t, fg_color=FIELD, corner_radius=10)
        modes.grid(row=3, column=0, sticky="ew", padx=14)
        for i, (label, value) in enumerate([("Trực tiếp", "direct"), ("Google", "search"), ("Qua AI", "aio"), ("Kết hợp", "mix")]):
            ctk.CTkRadioButton(modes, text=label, variable=self.radio_var, value=value,
                               width=130).grid(row=i // 2, column=i % 2, sticky="w", padx=12, pady=10)
        ctk.CTkLabel(t, text="Số phiên đồng thời", text_color=MUTED).grid(row=4, column=0, sticky="w", padx=14, pady=(12, 4))
        workers = ctk.CTkFrame(t, fg_color="transparent")
        workers.grid(row=5, column=0, sticky="ew", padx=14)
        workers.grid_columnconfigure(0, weight=1)
        self.lbl_threads = ctk.CTkLabel(workers, text="5 luồng", width=65, text_color=ACCENT)
        self.slider_threads = ctk.CTkSlider(workers, from_=1, to=20, number_of_steps=19, width=190,
                                          command=lambda v: self.lbl_threads.configure(text=f"{int(v)} luồng"))
        self.slider_threads.set(5)
        self.slider_threads.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        self.lbl_threads.grid(row=0, column=1)
        ctk.CTkLabel(t, text="Proxy · tùy chọn, mỗi dòng một proxy", text_color=MUTED).grid(row=6, column=0, sticky="w", padx=14, pady=(12, 6))
        self.txt_proxy = ctk.CTkTextbox(t, height=100, width=290)
        self.txt_proxy.grid(row=7, column=0, sticky="ew", padx=14, pady=(0, 16))
        self.txt_proxy.insert("1.0", "\n".join(cfg.PROXY_LIST))
        ctk.CTkLabel(t, text="Từ khóa · mỗi dòng một từ khóa", text_color=MUTED).grid(row=2, column=1, sticky="w", padx=14, pady=(16, 6))
        self.txt_keywords = ctk.CTkTextbox(t, height=220, width=290)
        self.txt_keywords.grid(row=3, column=1, rowspan=5, sticky="nsew", padx=14, pady=(0, 16))
        self.txt_keywords.insert("1.0", "\n".join(cfg.SEO_KEYWORDS))

    def _clear_log(self):
        self.txt_log.configure(state="normal")
        self.txt_log.delete("1.0", "end")
        self.txt_log.configure(state="disabled")

    def _copy_log(self):
        self.clipboard_clear()
        self.clipboard_append(self.txt_log.get("1.0", "end-1c"))
        self.lbl_save_status.configure(text="Đã sao chép nhật ký")

    def _toggle_log(self):
        self._log_visible = not self._log_visible
        if self._log_visible:
            self.txt_log.grid()
        else:
            self.txt_log.grid_remove()
        self.main_panel.grid_rowconfigure(2, weight=1 if self._log_visible else 0,
                                         minsize=170 if self._log_visible else 48)
        self.btn_log_toggle.configure(text="Thu gọn" if self._log_visible else "Mở nhật ký")
