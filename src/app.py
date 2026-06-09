import os
import sys
import time
import threading
import subprocess
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image

from .downloader import is_realesrgan_installed, download_realesrgan, get_realesrgan_dir
from .utils import check_ffmpeg_ffprobe, get_video_info, get_vram_presets, get_gpu_devices
from .checker_app import PrerequisiteCheckerWindow
from .engine import UpscaleEngine

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

COLOR_BG = ("#EBEFF2", "#0B0E14")
COLOR_CARD = ("#FFFFFF", "#141923")
COLOR_BORDER = ("#D4DCE2", "#222D3F")
COLOR_TEXT_PRIMARY = ("#0F172A", "#F8FAFC")
COLOR_TEXT_MUTED = ("#475569", "#94A3B8")
COLOR_INPUT_BG = ("#F1F5F9", "#1E293B")

COLOR_ACCENT_BLUE = ("#0066FF", "#3385FF")
COLOR_ACCENT_BLUE_HOVER = ("#0052CC", "#1A75FF")

class MuseUpscaleApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("MuseUpscale - Premium AI Video Upscaler")
        self.geometry("1000x835")
        self.minsize(980, 835)
        self.configure(fg_color=COLOR_BG)

        try:
            if getattr(sys, 'frozen', False):
                base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            icon_path = os.path.join(base_dir, "assets", "app.ico")
            if os.path.isfile(icon_path):
                self.iconbitmap(icon_path)
                self.after(200, lambda: self.iconbitmap(icon_path))
        except Exception:
            pass

        self.selected_video = ""
        self.selected_folder = ""
        self.video_info = None
        self.is_processing = False

        self.engine = UpscaleEngine()
        self.vram_presets = get_vram_presets()

        self.ffmpeg_ok, self.ffprobe_ok = check_ffmpeg_ffprobe()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.build_ui()
        self.check_system_dependencies()

    def create_setting_field(self, parent, label_text, values, row, col, default_val=None, command=None):
        lbl = ctk.CTkLabel(
            parent,
            text=label_text,
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            text_color=COLOR_TEXT_MUTED
        )
        lbl.grid(row=row, column=col, sticky="w", padx=5, pady=(5, 2))

        combo = ctk.CTkComboBox(
            parent,
            values=values,
            height=30,
            fg_color=COLOR_INPUT_BG,
            text_color=COLOR_TEXT_PRIMARY,
            border_color=COLOR_BORDER,
            button_color=COLOR_BORDER,
            button_hover_color=COLOR_ACCENT_BLUE,
            dropdown_fg_color=COLOR_CARD,
            dropdown_text_color=COLOR_TEXT_PRIMARY,
            dropdown_hover_color=COLOR_ACCENT_BLUE,
            corner_radius=6,
            command=command,
            state="readonly"
        )
        if default_val is not None:
            combo.set(default_val)
        combo.grid(row=row+1, column=col, padx=5, pady=(0, 10), sticky="ew")
        return combo

    def build_ui(self):

        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(1, weight=1)

        self.header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(5, 15))
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="MUSE UPSCALE",
            font=ctk.CTkFont(family="Outfit", size=24, weight="bold"),
            text_color=COLOR_ACCENT_BLUE
        )
        self.title_label.grid(row=0, column=0, sticky="w")

        self.subtitle_label = ctk.CTkLabel(
            self.header_frame,
            text="Ultra-Performance AI Video Upscaling for AMD & NVIDIA GPUs (Vulkan Powered)",
            font=ctk.CTkFont(family="Inter", size=12),
            text_color=COLOR_TEXT_MUTED
        )
        self.subtitle_label.grid(row=1, column=0, sticky="w", pady=(2, 0))

        self.btn_prerequisites = ctk.CTkButton(
            self.header_frame,
            text="⚙ Prerequisites",
            width=130,
            height=28,
            fg_color=("#E5E7EB", "#1C2028"),
            hover_color=("#D1D5DB", "#2E3545"),
            text_color=("#374151", "#E5E7EB"),
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            command=self.open_prerequisites_window,
            corner_radius=6
        )
        self.btn_prerequisites.grid(row=0, column=1, rowspan=2, sticky="e", padx=(10, 5))

        self.download_overlay = ctk.CTkFrame(
            self.main_container,
            fg_color=COLOR_CARD,
            border_width=1,
            border_color=COLOR_BORDER,
            corner_radius=10
        )

        self.split_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.split_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 15))
        self.split_frame.grid_columnconfigure(0, weight=3)
        self.split_frame.grid_columnconfigure(1, weight=2)
        self.split_frame.grid_rowconfigure(0, weight=1)

        self.steps_container = ctk.CTkFrame(self.split_frame, fg_color="transparent")
        self.steps_container.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.steps_container.grid_columnconfigure(0, weight=1)

        self.step1_card_outer = ctk.CTkFrame(self.steps_container, fg_color=COLOR_BORDER, corner_radius=10)
        self.step1_card_outer.grid(row=0, column=0, sticky="ew", pady=(10, 10))

        self.step1_card = ctk.CTkFrame(self.step1_card_outer, fg_color=COLOR_CARD, corner_radius=9)
        self.step1_card.pack(expand=True, fill="both", padx=1, pady=1)
        self.step1_card.grid_columnconfigure(1, weight=1)

        self.lbl_step1_check = ctk.CTkLabel(
            self.step1_card,
            text="□",
            font=ctk.CTkFont(family="Inter", size=16, weight="bold"),
            text_color=COLOR_ACCENT_BLUE
        )
        self.lbl_step1_check.grid(row=0, column=0, padx=(15, 5), pady=(10, 2), sticky="w")

        self.lbl_step1_title = ctk.CTkLabel(
            self.step1_card,
            text="01 SOURCE",
            font=ctk.CTkFont(family="Outfit", size=13, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        self.lbl_step1_title.grid(row=0, column=1, pady=(10, 2), sticky="w")

        self.lbl_step1_desc = ctk.CTkLabel(
            self.step1_card,
            text="[ VIDEO SOURCE FILE ]",
            font=ctk.CTkFont(family="Inter", size=10),
            text_color=COLOR_TEXT_MUTED
        )
        self.lbl_step1_desc.grid(row=0, column=2, padx=(0, 15), pady=(10, 2), sticky="e")

        self.step1_body = ctk.CTkFrame(self.step1_card, fg_color="transparent")
        self.step1_body.grid(row=1, column=0, columnspan=3, sticky="ew", padx=15, pady=(5, 15))
        self.step1_body.grid_columnconfigure(0, weight=1)

        self.entry_video = ctk.CTkEntry(
            self.step1_body,
            placeholder_text="No video file selected...",
            height=30,
            state="disabled",
            fg_color=COLOR_INPUT_BG,
            text_color=COLOR_TEXT_PRIMARY,
            placeholder_text_color=COLOR_TEXT_MUTED,
            border_color=COLOR_BORDER,
            border_width=1,
            corner_radius=6
        )
        self.entry_video.grid(row=0, column=0, padx=(0, 10), sticky="ew")

        self.btn_select_video = ctk.CTkButton(
            self.step1_body,
            text="Select Video",
            width=110,
            height=30,
            fg_color=COLOR_ACCENT_BLUE,
            hover_color=COLOR_ACCENT_BLUE_HOVER,
            text_color="#FFFFFF",
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            command=self.select_video,
            corner_radius=6
        )
        self.btn_select_video.grid(row=0, column=1, sticky="e")

        self.step2_card_outer = ctk.CTkFrame(self.steps_container, fg_color=COLOR_BORDER, corner_radius=10)
        self.step2_card_outer.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        self.step2_card = ctk.CTkFrame(self.step2_card_outer, fg_color=COLOR_CARD, corner_radius=9)
        self.step2_card.pack(expand=True, fill="both", padx=1, pady=1)
        self.step2_card.grid_columnconfigure(1, weight=1)

        self.lbl_step2_check = ctk.CTkLabel(
            self.step2_card,
            text="□",
            font=ctk.CTkFont(family="Inter", size=16, weight="bold"),
            text_color=COLOR_ACCENT_BLUE
        )
        self.lbl_step2_check.grid(row=0, column=0, padx=(15, 5), pady=(10, 2), sticky="w")

        self.lbl_step2_title = ctk.CTkLabel(
            self.step2_card,
            text="02 TARGET",
            font=ctk.CTkFont(family="Outfit", size=13, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        self.lbl_step2_title.grid(row=0, column=1, pady=(10, 2), sticky="w")

        self.lbl_step2_desc = ctk.CTkLabel(
            self.step2_card,
            text="[ PROCESS & OUTPUT DIRECTORY ]",
            font=ctk.CTkFont(family="Inter", size=10),
            text_color=COLOR_TEXT_MUTED
        )
        self.lbl_step2_desc.grid(row=0, column=2, padx=(0, 15), pady=(10, 2), sticky="e")

        self.step2_body = ctk.CTkFrame(self.step2_card, fg_color="transparent")
        self.step2_body.grid(row=1, column=0, columnspan=3, sticky="ew", padx=15, pady=(5, 15))
        self.step2_body.grid_columnconfigure(0, weight=1)

        self.entry_folder = ctk.CTkEntry(
            self.step2_body,
            placeholder_text="No processing folder selected...",
            height=30,
            state="disabled",
            fg_color=COLOR_INPUT_BG,
            text_color=COLOR_TEXT_PRIMARY,
            placeholder_text_color=COLOR_TEXT_MUTED,
            border_color=COLOR_BORDER,
            border_width=1,
            corner_radius=6
        )
        self.entry_folder.grid(row=0, column=0, padx=(0, 10), sticky="ew")

        self.btn_select_folder = ctk.CTkButton(
            self.step2_body,
            text="Select Folder",
            width=110,
            height=30,
            fg_color=COLOR_ACCENT_BLUE,
            hover_color=COLOR_ACCENT_BLUE_HOVER,
            text_color="#FFFFFF",
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            state="disabled",
            command=self.select_folder,
            corner_radius=6
        )
        self.btn_select_folder.grid(row=0, column=1, sticky="e")

        self.step3_card_outer = ctk.CTkFrame(self.steps_container, fg_color=COLOR_BORDER, corner_radius=10)
        self.step3_card_outer.grid(row=2, column=0, sticky="ew", pady=(0, 10))

        self.step3_card = ctk.CTkFrame(self.step3_card_outer, fg_color=COLOR_CARD, corner_radius=9)
        self.step3_card.pack(expand=True, fill="both", padx=1, pady=1)
        self.step3_card.grid_columnconfigure(1, weight=1)

        self.lbl_step3_check = ctk.CTkLabel(
            self.step3_card,
            text="□",
            font=ctk.CTkFont(family="Inter", size=16, weight="bold"),
            text_color=COLOR_ACCENT_BLUE
        )
        self.lbl_step3_check.grid(row=0, column=0, padx=(15, 5), pady=(10, 2), sticky="w")

        self.lbl_step3_title = ctk.CTkLabel(
            self.step3_card,
            text="03 CONFIG",
            font=ctk.CTkFont(family="Outfit", size=13, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        self.lbl_step3_title.grid(row=0, column=1, pady=(10, 2), sticky="w")

        self.lbl_step3_desc = ctk.CTkLabel(
            self.step3_card,
            text="[ ADVANCED AI PARAMETERS ]",
            font=ctk.CTkFont(family="Inter", size=10),
            text_color=COLOR_TEXT_MUTED
        )
        self.lbl_step3_desc.grid(row=0, column=2, padx=(0, 15), pady=(10, 2), sticky="e")

        self.settings_frame = ctk.CTkFrame(self.step3_card, fg_color="transparent")
        self.settings_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=15, pady=(5, 15))
        self.settings_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.combo_model = self.create_setting_field(
            self.settings_frame, "AI Model",
            ["realesr-animevideov3", "realesrgan-x4plus-anime", "realesrgan-x4plus"],
            row=0, col=0,
            default_val="",
            command=self.on_model_changed
        )
        self.combo_vram = self.create_setting_field(
            self.settings_frame, "VRAM Configuration",
            list(self.vram_presets.keys()),
            row=0, col=1,
            default_val="16GB VRAM (Extreme Performance)",
            command=self.on_vram_preset_changed
        )

        gpu_devices = get_gpu_devices()
        gpu_options = ["Auto-detect"]
        if gpu_devices:
            for gpu_name in gpu_devices:
                gpu_options.append(gpu_name)
        else:
            gpu_options.extend(["Device 0", "Device 1"])

        self.combo_gpu = self.create_setting_field(
            self.settings_frame, "Target GPU",
            gpu_options,
            row=0, col=2,
            default_val="Auto-detect"
        )
        self.combo_scale = self.create_setting_field(
            self.settings_frame, "Scaling Factor",
            ["4x", "3x", "2x"],
            row=2, col=0,
            default_val="2x"
        )
        self.combo_format = self.create_setting_field(
            self.settings_frame, "Frame Format",
            ["JPG (Fast & Compressed)", "WebP (Balanced)", "PNG (Lossless - Heavy)"],
            row=2, col=1,
            default_val="JPG (Fast & Compressed)"
        )
        self.combo_pre_resize = self.create_setting_field(
            self.settings_frame, "Pre-Resize (Input)",
            ["100% (No Resize)", "75%", "50%", "25%"],
            row=2, col=2,
            default_val="100% (No Resize)"
        )
        self.combo_post_resize = self.create_setting_field(
            self.settings_frame, "Post-Resize (Output)",
            ["100% (No Resize)", "75%", "50%", "25%"],
            row=4, col=0,
            default_val="100% (No Resize)"
        )

        self.step4_card_outer = ctk.CTkFrame(self.steps_container, fg_color=COLOR_BORDER, corner_radius=10)
        self.step4_card_outer.grid(row=3, column=0, sticky="ew", pady=(0, 0))

        self.step4_card = ctk.CTkFrame(self.step4_card_outer, fg_color=COLOR_CARD, corner_radius=9)
        self.step4_card.pack(expand=True, fill="both", padx=1, pady=1)
        self.step4_card.grid_columnconfigure(1, weight=1)

        self.lbl_step4_check = ctk.CTkLabel(
            self.step4_card,
            text="□",
            font=ctk.CTkFont(family="Inter", size=16, weight="bold"),
            text_color=COLOR_ACCENT_BLUE
        )
        self.lbl_step4_check.grid(row=0, column=0, padx=(15, 5), pady=(10, 2), sticky="w")

        self.lbl_step4_title = ctk.CTkLabel(
            self.step4_card,
            text="04 UPSCALE",
            font=ctk.CTkFont(family="Outfit", size=13, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        self.lbl_step4_title.grid(row=0, column=1, pady=(10, 2), sticky="w")

        self.lbl_step4_desc = ctk.CTkLabel(
            self.step4_card,
            text="[ PIPELINE CONTROL ]",
            font=ctk.CTkFont(family="Inter", size=10),
            text_color=COLOR_TEXT_MUTED
        )
        self.lbl_step4_desc.grid(row=0, column=2, padx=(0, 15), pady=(10, 2), sticky="e")

        self.controls_frame = ctk.CTkFrame(self.step4_card, fg_color="transparent")
        self.controls_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=15, pady=(5, 15))
        self.controls_frame.grid_columnconfigure(0, weight=2)
        self.controls_frame.grid_columnconfigure(1, weight=1)

        self.btn_action = ctk.CTkButton(
            self.controls_frame,
            text="Start AI Upscaling",
            height=36,
            fg_color=COLOR_ACCENT_BLUE,
            hover_color=COLOR_ACCENT_BLUE_HOVER,
            text_color="#FFFFFF",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            state="disabled",
            command=self.toggle_upscale,
            corner_radius=6
        )
        self.btn_action.grid(row=0, column=0, padx=(0, 10), sticky="ew")

        self.btn_open_output = ctk.CTkButton(
            self.controls_frame,
            text="Open Output Folder",
            height=36,
            fg_color=("#E5E7EB", "#1C2028"),
            hover_color=("#D1D5DB", "#2E3545"),
            text_color=("#374151", "#E5E7EB"),
            state="disabled",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            command=self.open_output_folder,
            corner_radius=6
        )
        self.btn_open_output.grid(row=0, column=1, sticky="ew")

        self.info_container = ctk.CTkFrame(self.split_frame, fg_color="transparent")
        self.info_container.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self.info_container.grid_columnconfigure(0, weight=1)
        self.info_container.grid_rowconfigure(0, weight=0)
        self.info_container.grid_rowconfigure(1, weight=1)

        self.decor_card_outer = ctk.CTkFrame(self.info_container, fg_color=COLOR_BORDER, corner_radius=10)
        self.decor_card_outer.grid(row=0, column=0, sticky="ew", pady=(10, 10))

        self.decor_card = ctk.CTkFrame(self.decor_card_outer, fg_color=COLOR_CARD, corner_radius=9)
        self.decor_card.pack(expand=True, fill="both", padx=1, pady=1)
        self.decor_card.grid_columnconfigure(0, weight=1)

        self.lbl_kanji_decor = ctk.CTkLabel(
            self.decor_card,
            text="超解像処理",
            font=ctk.CTkFont(family="MS Gothic", size=32, weight="bold"),
            text_color=COLOR_ACCENT_BLUE
        )
        self.lbl_kanji_decor.grid(row=0, column=0, padx=15, pady=(15, 2), sticky="w")

        self.lbl_tech_subtitle = ctk.CTkLabel(
            self.decor_card,
            text="MUSE ENGINE v2.0 // VULKAN ACCELERATED",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=COLOR_TEXT_MUTED
        )
        self.lbl_tech_subtitle.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="w")

        self.console_frame_outer = ctk.CTkFrame(self.info_container, fg_color=COLOR_BORDER, corner_radius=10)
        self.console_frame_outer.grid(row=1, column=0, sticky="nsew", pady=(0, 5))

        self.console_frame = ctk.CTkFrame(self.console_frame_outer, fg_color=COLOR_CARD, corner_radius=9)
        self.console_frame.pack(expand=True, fill="both", padx=1, pady=1)
        self.console_frame.grid_columnconfigure(0, weight=1)
        self.console_frame.grid_rowconfigure(1, weight=1)

        self.terminal_header = ctk.CTkFrame(self.console_frame, fg_color="transparent")
        self.terminal_header.grid(row=0, column=0, sticky="ew", padx=15, pady=(10, 5))
        self.terminal_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.terminal_header,
            text="SYSTEM TERMINAL LOG",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=COLOR_TEXT_MUTED
        ).grid(row=0, column=0, sticky="w")

        self.txt_console = ctk.CTkTextbox(
            self.console_frame,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=COLOR_INPUT_BG,
            text_color=COLOR_TEXT_PRIMARY,
            border_width=0,
            corner_radius=6
        )
        self.txt_console.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))

        self.bottom_panel = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.bottom_panel.grid(row=2, column=0, sticky="ew", padx=10, pady=(5, 0))
        self.bottom_panel.grid_columnconfigure(0, weight=1)

        self.progress_header = ctk.CTkFrame(self.bottom_panel, fg_color="transparent")
        self.progress_header.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        self.progress_header.grid_columnconfigure(0, weight=1)

        self.lbl_status = ctk.CTkLabel(
            self.progress_header,
            text="Ready: Please select a video source to begin upscaling.",
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            text_color=COLOR_TEXT_MUTED
        )
        self.lbl_status.grid(row=0, column=0, sticky="w")

        self.lbl_pct = ctk.CTkLabel(
            self.progress_header,
            text="0%",
            font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
            text_color=COLOR_ACCENT_BLUE
        )
        self.lbl_pct.grid(row=0, column=1, sticky="e")

        self.progress_bar = ctk.CTkProgressBar(
            self.bottom_panel,
            height=6,
            progress_color=COLOR_ACCENT_BLUE,
            fg_color=COLOR_BORDER
        )
        self.progress_bar.set(0.0)
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        self.footer_steps_frame = ctk.CTkFrame(self.bottom_panel, fg_color="transparent")
        self.footer_steps_frame.grid(row=2, column=0, pady=(0, 5))

        self.step_labels = {}
        steps = ["EXTRACT", "UPSCALE", "STITCH", "FINISHED"]
        for idx, step_name in enumerate(steps):
            lbl = ctk.CTkLabel(
                self.footer_steps_frame,
                text=step_name,
                font=ctk.CTkFont(family="Consolas", size=9, weight="bold"),
                text_color=COLOR_TEXT_MUTED,
                fg_color=COLOR_INPUT_BG,
                corner_radius=4,
                padx=8,
                pady=2
            )
            lbl.grid(row=0, column=idx, padx=5, pady=2)
            self.step_labels[step_name] = lbl

        self.lbl_elapsed = ctk.CTkLabel(
            self.footer_steps_frame,
            text="ELAPSED: 00:00",
            font=ctk.CTkFont(family="Consolas", size=9, weight="bold"),
            text_color=COLOR_TEXT_MUTED,
            fg_color=COLOR_INPUT_BG,
            corner_radius=4,
            padx=8,
            pady=2
        )
        self.lbl_elapsed.grid(row=0, column=len(steps), padx=5, pady=2)

        self.write_log("MuseUpscale Engine Initialized.")
        self.write_log(f"System Check: python v{sys.version.split(' ')[0]}")

    def open_prerequisites_window(self):

        self.btn_prerequisites.configure(state="disabled")

        def on_prereq_close():

            self.btn_prerequisites.configure(state="normal")

            self.ffmpeg_ok, self.ffprobe_ok = check_ffmpeg_ffprobe()
            self.check_system_dependencies()

        PrerequisiteCheckerWindow(self, on_close_callback=on_prereq_close)

    def check_system_dependencies(self):

        if not self.ffmpeg_ok or not self.ffprobe_ok:
            self.write_log("[ERROR] FFmpeg or FFprobe was NOT found on your system PATH!")
            self.write_log("Please ensure FFmpeg is installed and added to your system Environment Variables.")
            messagebox.showerror(
                "FFmpeg Missing",
                "FFmpeg or FFprobe could not be found in your Windows PATH variable.\n\n"
                "Please download and install FFmpeg, then restart MuseUpscale."
            )
            self.btn_select_video.configure(state="disabled")
            return

        self.write_log("System Check: FFmpeg & FFprobe verified OK.")

        if not is_realesrgan_installed():
            self.show_downloader_overlay()
        else:
            self.write_log(f"System Check: Real-ESRGAN Vulkan binaries detected at '{get_realesrgan_dir()}'")

    def show_downloader_overlay(self):

        self.write_log("[SYSTEM] Real-ESRGAN Vulkan binaries are missing! Setup required.")

        self.btn_select_video.configure(state="disabled")

        self.download_overlay.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.75, relheight=0.45)
        self.download_overlay.grid_columnconfigure(0, weight=1)
        self.download_overlay.grid_rowconfigure((0, 1, 2, 3), weight=1)

        lbl_dl_title = ctk.CTkLabel(
            self.download_overlay,
            text="AI ENGINE SETUP",
            font=ctk.CTkFont(family="Outfit", size=18, weight="bold"),
            text_color=COLOR_ACCENT_BLUE
        )
        lbl_dl_title.grid(row=0, column=0, pady=(15, 2))

        lbl_dl_desc = ctk.CTkLabel(
            self.download_overlay,
            text="MuseUpscale requires the open-source Real-ESRGAN Vulkan binaries.\nWould you like to automatically download it now? (~15.2MB)",
            font=ctk.CTkFont(family="Inter", size=12),
            text_color=COLOR_TEXT_PRIMARY,
            justify="center"
        )
        lbl_dl_desc.grid(row=1, column=0, padx=20)

        self.dl_progress = ctk.CTkProgressBar(
            self.download_overlay,
            width=320,
            height=8,
            progress_color=COLOR_ACCENT_BLUE,
            fg_color=COLOR_BORDER
        )
        self.dl_progress.set(0.0)
        self.dl_progress.grid(row=2, column=0, pady=5)

        self.lbl_dl_status = ctk.CTkLabel(
            self.download_overlay,
            text="Status: Pending User Approval",
            font=ctk.CTkFont(family="Inter", size=11),
            text_color=COLOR_TEXT_MUTED
        )
        self.lbl_dl_status.grid(row=2, column=0, sticky="s", pady=(0, 5))

        self.btn_dl_start = ctk.CTkButton(
            self.download_overlay,
            text="Download & Install AI Engine",
            fg_color=COLOR_ACCENT_BLUE,
            hover_color=COLOR_ACCENT_BLUE_HOVER,
            text_color="#FFFFFF",
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            corner_radius=6,
            command=self.start_dependency_download
        )
        self.btn_dl_start.grid(row=3, column=0, pady=(5, 15))

    def start_dependency_download(self):

        self.btn_dl_start.configure(state="disabled", text="Downloading...")
        self.lbl_dl_status.configure(text="Status: Connecting...")

        threading.Thread(target=self.downloader_thread_proc, daemon=True).start()

    def downloader_thread_proc(self):

        def callback(progress, message):
            self.after(0, self.update_downloader_ui, progress, message)

        try:
            download_realesrgan(progress_callback=callback)
            self.after(0, self.finalize_dependency_install)
        except Exception as e:
            self.after(0, self.handle_downloader_error, str(e))

    def update_downloader_ui(self, progress, message):

        self.dl_progress.set(progress)
        self.lbl_dl_status.configure(text=f"Status: {message}")
        self.write_log(f"[Download Manager] {message}")

    def finalize_dependency_install(self):

        self.write_log("[SUCCESS] AI Engine installed and fully integrated!")
        self.download_overlay.place_forget()

        self.btn_select_video.configure(state="normal")
        messagebox.showinfo("Setup Complete", "The AI upscaling engine was downloaded and set up successfully!")

    def handle_downloader_error(self, err_msg):

        self.write_log(f"[ERROR] Failed to install AI Engine: {err_msg}")
        self.btn_dl_start.configure(state="normal", text="Retry Download & Install")
        self.lbl_dl_status.configure(text="Status: Download Failed.")
        messagebox.showerror("Download Error", f"Failed to download AI engine:\n{err_msg}\n\nPlease check your internet connection and try again.")

    def select_video(self):

        file_path = filedialog.askopenfilename(
            title="Select Video Source File",
            filetypes=[("Video Files", "*.mp4 *.mkv *.avi *.mov *.webm *.flv *.m4v")]
        )
        if not file_path:
            return

        self.selected_video = file_path
        self.entry_video.configure(state="normal")
        self.entry_video.delete(0, "end")
        self.entry_video.insert(0, self.selected_video)
        self.entry_video.configure(state="disabled")

        self.write_log(f"\nSource Video Selected: '{os.path.basename(self.selected_video)}'")
        self.lbl_step1_check.configure(text="☑")

        try:
            self.video_info = get_video_info(self.selected_video)
            self.write_log(f"Parsed Stream: {self.video_info['width']}x{self.video_info['height']} @ {self.video_info['fps']:.2f}fps, {self.video_info['frame_count']} frames")
        except Exception as e:
            self.write_log(f"[Warning] Failed to parse video metadata: {e}")

        self.btn_select_folder.configure(state="normal")
        self.lbl_status.configure(text="Step 2: Select a Process/Working Folder where frames will be upscaled.")

        self.validate_start_state()

    def select_folder(self):

        dir_path = filedialog.askdirectory(title="Select Process & Output Directory")
        if not dir_path:
            return

        self.selected_folder = dir_path
        self.entry_folder.configure(state="normal")
        self.entry_folder.delete(0, "end")
        self.entry_folder.insert(0, self.selected_folder)
        self.entry_folder.configure(state="disabled")

        self.write_log(f"Working Directory Selected: '{self.selected_folder}'")
        self.lbl_step2_check.configure(text="☑")

        self.btn_open_output.configure(state="normal")
        self.validate_start_state()

    def validate_start_state(self):

        model = self.combo_model.get()
        if self.selected_video and self.selected_folder and model and model != "":
            self.btn_action.configure(
                state="normal",
                fg_color=COLOR_ACCENT_BLUE,
                hover_color=COLOR_ACCENT_BLUE_HOVER,
                text_color="#FFFFFF",
                text="Start AI Upscaling"
            )
            self.lbl_status.configure(text="Ready to process! Adjust parameters and click Start AI Upscaling.")
            self.lbl_step4_check.configure(text="□")
        else:
            self.btn_action.configure(state="disabled")
            if not self.selected_video:
                self.lbl_status.configure(text="Step 1: Please select a video source to begin upscaling.")
            elif not self.selected_folder:
                self.lbl_status.configure(text="Step 2: Please select a process/working folder.")
            elif not model or model == "":
                self.lbl_status.configure(text="Step 3: Please select an AI Model to configure pipeline.")

    def open_output_folder(self):

        if self.selected_folder and os.path.exists(self.selected_folder):
            try:
                os.startfile(self.selected_folder)
                self.write_log(f"Opened Explorer directory: '{self.selected_folder}'")
            except Exception as e:
                self.write_log(f"Error opening folder: {e}")
        else:
            self.write_log("Error: Output folder is not selected or does not exist.")

    def on_vram_preset_changed(self, preset_name):

        preset = self.vram_presets.get(preset_name)
        if preset:
            self.write_log(f"[Preset Selected] {preset_name}: {preset['desc']}")

    def on_model_changed(self, model_name):

        self.update_config_checkmark()
        self.validate_start_state()

    def update_config_checkmark(self):

        model = self.combo_model.get()
        if model and model != "":
            self.lbl_step3_check.configure(text="☑")
        else:
            self.lbl_step3_check.configure(text="□")

    def toggle_upscale(self):

        if self.is_processing:

            reply = messagebox.askyesno("Confirm Cancellation", "Are you sure you want to abort the upscaling process?")
            if reply:
                self.write_log("\n[!] Cancellation requested by user... Terminating subprocesses.")
                self.engine.cancel()
                self.btn_action.configure(state="disabled", text="Cancelling...")
        else:
            try:

                self.is_processing = True
                self.lock_ui(True)
                self.set_active_footer_step("EXTRACT")
                self.upscale_start_time = time.time()
                self.update_elapsed_time()

                model = self.combo_model.get()
                scale_val = int(self.combo_scale.get().replace("x", ""))

                vram_preset = self.combo_vram.get()
                preset_config = self.vram_presets.get(vram_preset, self.vram_presets["8GB VRAM (Safe/Low VRAM)"])
                tile_size = preset_config["tile_size"]
                threads = preset_config["threads"]
                gpu_id = self.combo_gpu.get()
                if gpu_id != "Auto-detect":
                    gpu_devices = get_gpu_devices()
                    if gpu_id in gpu_devices:
                        gpu_id = f"Device {gpu_devices.index(gpu_id)}"

                selected_fmt = self.combo_format.get()
                if "JPG" in selected_fmt:
                    img_format = "jpg"
                elif "WebP" in selected_fmt:
                    img_format = "webp"
                else:
                    img_format = "png"

                pre_resize_val = self.combo_pre_resize.get()
                pre_resize = int(pre_resize_val.replace("% (No Resize)", "").replace("%", ""))

                post_resize_val = self.combo_post_resize.get()
                post_resize = int(post_resize_val.replace("% (No Resize)", "").replace("%", ""))

                self.btn_action.configure(
                    fg_color=("#EF4444", "#F87171"),
                    hover_color=("#DC2626", "#EF4444"),
                    text_color="#FFFFFF",
                    text="Cancel Process"
                )
                self.lbl_step4_check.configure(text="□")

                threading.Thread(
                    target=self.upscale_worker_proc,
                    args=(self.selected_video, self.selected_folder, model, scale_val, tile_size, threads, gpu_id, img_format, pre_resize, post_resize),
                    daemon=True
                ).start()
            except Exception as e:
                import traceback
                self.write_log(f"[CRITICAL ERROR] Failed to start upscale thread: {e}")
                self.write_log(traceback.format_exc())
                messagebox.showerror("Error", f"Failed to start upscaling:\n{e}\n\n{traceback.format_exc()}")
                self.is_processing = False
                self.lock_ui(False)

    def upscale_worker_proc(self, video, folder, model, scale, tile, threads, gpu, img_format, pre_resize, post_resize):

        def progress_cb(phase, value):
            self.after(0, self.update_engine_progress, phase, value)

        def log_cb(msg):
            self.after(0, self.write_log, msg)

        try:
            self.engine.run_upscale(video, folder, model, scale, tile, threads, gpu, img_format, pre_resize, post_resize, progress_cb, log_cb)
        except Exception as e:
            import traceback
            log_cb(f"\n[CRITICAL THREAD ERROR] Engine crashed: {e}")
            log_cb(traceback.format_exc())
        finally:
            self.after(0, self.finalize_upscale_run)

    def update_engine_progress(self, phase, progress):

        self.progress_bar.set(progress)
        self.lbl_pct.configure(text=f"{progress*100:.0f}%")

        if phase == "Extraction":
            status_text = f"Phase 1/3: Lossless Frame Extraction... ({progress*100:.1f}%)"
            self.progress_bar.configure(progress_color=("#D97706", "#F59E0B"))
            self.set_active_footer_step("EXTRACT")
        elif phase == "Upscaling":
            status_text = f"Phase 2/3: AI GPU Upscaling ({self.combo_model.get()})... {progress*100:.1f}%"
            self.progress_bar.configure(progress_color=COLOR_ACCENT_BLUE)
            self.lbl_step4_check.configure(text="□")
            self.set_active_footer_step("UPSCALE")
        elif phase == "Merging":
            status_text = f"Phase 3/3: Re-assembling Video & Audio... ({progress*100:.1f}%)"
            self.progress_bar.configure(progress_color=COLOR_ACCENT_BLUE)
            self.set_active_footer_step("STITCH")
        elif phase == "Completed":
            status_text = "Upscaling completed successfully!"
            self.progress_bar.configure(progress_color=COLOR_ACCENT_BLUE)
            self.lbl_step4_check.configure(text="☑")
            self.set_active_footer_step("FINISHED")
        elif phase == "Cancelled":
            status_text = "Aborted by user."
            self.progress_bar.configure(progress_color=("#EF4444", "#F87171"))
            self.lbl_step4_check.configure(text="□")
            self.set_active_footer_step("")
        else:
            status_text = f"Processing... {progress*100:.1f}%"

        self.lbl_status.configure(text=status_text)

    def finalize_upscale_run(self):

        self.is_processing = False
        self.lock_ui(False)

        phase = self.engine.current_phase
        if phase == "Completed":
            self.progress_bar.set(1.0)
            self.lbl_status.configure(text="Upscaling completed! Final output saved to processing folder.")
            messagebox.showinfo("Success", "Video upscaled successfully!")
        elif phase == "Cancelled":
            self.progress_bar.set(0.0)
            self.lbl_status.configure(text="Process cancelled by user.")
            messagebox.showwarning("Cancelled", "The upscaling process was aborted and temporary files were deleted.")
        else:
            self.progress_bar.set(0.0)
            self.lbl_status.configure(text="Upscaling pipeline failed.")
            messagebox.showerror("Pipeline Failed", "Upscaling failed! Check the terminal log for details.")

        self.validate_start_state()

        if hasattr(self, "upscale_start_time"):
            elapsed = int(time.time() - self.upscale_start_time)
            mins = elapsed // 60
            secs = elapsed % 60
            self.lbl_elapsed.configure(
                text=f"ELAPSED: {mins:02d}:{secs:02d}",
                fg_color=COLOR_INPUT_BG,
                text_color=COLOR_TEXT_MUTED
            )

    def lock_ui(self, lock=True):

        state = "disabled" if lock else "readonly"
        self.btn_select_video.configure(state="disabled" if lock else "normal")
        self.btn_select_folder.configure(state="disabled" if lock else "normal")
        self.combo_model.configure(state=state)
        self.combo_vram.configure(state=state)
        self.combo_scale.configure(state=state)
        self.combo_gpu.configure(state=state)
        self.combo_format.configure(state=state)
        self.combo_pre_resize.configure(state=state)
        self.combo_post_resize.configure(state=state)

    def set_active_footer_step(self, active_step_name):

        for name, lbl in self.step_labels.items():
            if name == active_step_name:
                lbl.configure(
                    fg_color=COLOR_ACCENT_BLUE,
                    text_color="#FFFFFF"
                )
            else:
                lbl.configure(
                    fg_color=COLOR_INPUT_BG,
                    text_color=COLOR_TEXT_MUTED
                )

    def update_elapsed_time(self):

        if self.is_processing and hasattr(self, "upscale_start_time"):
            elapsed = int(time.time() - self.upscale_start_time)
            mins = elapsed // 60
            secs = elapsed % 60
            self.lbl_elapsed.configure(
                text=f"ELAPSED: {mins:02d}:{secs:02d}",
                fg_color=COLOR_ACCENT_BLUE,
                text_color="#FFFFFF"
            )
            self.after(1000, self.update_elapsed_time)

    def write_log(self, message):

        self.txt_console.configure(state="normal")
        self.txt_console.insert("end", f"{message}\n")
        self.txt_console.configure(state="disabled")

        self.txt_console.see("end")

if __name__ == "__main__":
    app = MuseUpscaleApp()
    app.mainloop()
