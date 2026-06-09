import os
import sys
import threading
import time
from tkinter import messagebox
import customtkinter as ctk

from .checker_utils import (
    check_ffmpeg,
    check_realesrgan,
    install_ffmpeg,
    download_realesrgan
)

COLOR_BG = ("#EBEFF2", "#0B0E14")
COLOR_CARD = ("#FFFFFF", "#141923")
COLOR_BORDER = ("#D4DCE2", "#222D3F")
COLOR_TEXT_PRIMARY = ("#0F172A", "#F8FAFC")
COLOR_TEXT_MUTED = ("#475569", "#94A3B8")
COLOR_INPUT_BG = ("#F1F5F9", "#1E293B")

COLOR_ACCENT_BLUE = ("#0066FF", "#3385FF")
COLOR_ACCENT_BLUE_HOVER = ("#0052CC", "#1A75FF")

class PrerequisiteCheckerWindow(ctk.CTkToplevel):

    def __init__(self, parent, on_close_callback=None):
        super().__init__(parent)

        self.title("MuseUpscale — System Prerequisites")
        self.geometry("850x520")
        self.minsize(850, 480)
        self.configure(fg_color=COLOR_BG)
        self.resizable(True, True)

        self.on_close_callback = on_close_callback

        self.transient(parent)
        self.grab_set()
        self.focus_force()
        self.lift()

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

        self.is_installing = False
        self.requirements = {
            "ffmpeg": {
                "name": "FFmpeg & FFprobe Binary Tools",
                "desc": "Lossless frame extraction, stitching and audio container re-muxing.",
                "check_fn": check_ffmpeg,
                "install_fn": install_ffmpeg
            },
            "realesrgan": {
                "name": "Real-ESRGAN Vulkan Core",
                "desc": "Vulkan-accelerated AI Upscaling core engine models and modules.",
                "check_fn": check_realesrgan,
                "install_fn": download_realesrgan
            }
        }

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.build_ui()
        self.scan_requirements()

        self.protocol("WM_DELETE_WINDOW", self.on_window_close)

    def on_window_close(self):

        if self.is_installing:
            messagebox.showwarning(
                "Installation Running",
                "An installation is still running. Please wait for it to finish.",
                parent=self
            )
            return

        self.grab_release()
        if self.on_close_callback:
            self.on_close_callback()
        self.destroy()

    def build_ui(self):
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=0, sticky="nsew", padx=25, pady=20)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(1, weight=1)

        self.header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(5, 15))
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="SYSTEM PREREQUISITES",
            font=ctk.CTkFont(family="Outfit", size=20, weight="bold"),
            text_color=COLOR_ACCENT_BLUE
        )
        self.title_label.grid(row=0, column=0, sticky="w")

        self.subtitle_label = ctk.CTkLabel(
            self.header_frame,
            text="Diagnose & install external dependencies required by MuseUpscale",
            font=ctk.CTkFont(family="Inter", size=11),
            text_color=COLOR_TEXT_MUTED
        )
        self.subtitle_label.grid(row=1, column=0, sticky="w", pady=(2, 0))

        self.content_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 15))
        self.content_frame.grid_columnconfigure(0, weight=4)
        self.content_frame.grid_columnconfigure(1, weight=3)
        self.content_frame.grid_rowconfigure(0, weight=1)

        self.cards_scroll = ctk.CTkScrollableFrame(
            self.content_frame,
            fg_color="transparent",
            label_text="REQUIRED COMPONENTS",
            label_text_color=COLOR_TEXT_MUTED,
            label_font=ctk.CTkFont(family="Consolas", size=11, weight="bold")
        )
        self.cards_scroll.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.cards_scroll.grid_columnconfigure(0, weight=1)

        self.card_widgets = {}
        for idx, (key, info) in enumerate(self.requirements.items()):

            outer = ctk.CTkFrame(self.cards_scroll, fg_color=COLOR_BORDER, corner_radius=10)
            outer.grid(row=idx, column=0, sticky="ew", pady=(0, 12))

            card = ctk.CTkFrame(outer, fg_color=COLOR_CARD, corner_radius=9)
            card.pack(expand=True, fill="both", padx=1, pady=1)
            card.grid_columnconfigure(1, weight=1)

            lbl_check = ctk.CTkLabel(
                card,
                text="□",
                font=ctk.CTkFont(family="Inter", size=18, weight="bold"),
                text_color=COLOR_TEXT_MUTED
            )
            lbl_check.grid(row=0, column=0, rowspan=2, padx=(15, 10))

            lbl_name = ctk.CTkLabel(
                card,
                text=info["name"],
                font=ctk.CTkFont(family="Outfit", size=13, weight="bold"),
                text_color=COLOR_TEXT_PRIMARY,
                anchor="w"
            )
            lbl_name.grid(row=0, column=1, pady=(10, 2), sticky="ew")

            lbl_desc = ctk.CTkLabel(
                card,
                text=info["desc"],
                font=ctk.CTkFont(family="Inter", size=10),
                text_color=COLOR_TEXT_MUTED,
                wraplength=220,
                justify="left",
                anchor="w"
            )
            lbl_desc.grid(row=1, column=1, padx=(0, 10), pady=(0, 12), sticky="ew")

            btn_install = ctk.CTkButton(
                card,
                text="Install",
                width=80,
                height=28,
                font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
                fg_color=COLOR_ACCENT_BLUE,
                hover_color=COLOR_ACCENT_BLUE_HOVER,
                text_color="#FFFFFF",
                corner_radius=6,
                command=lambda k=key: self.trigger_installation(k)
            )
            btn_install.grid(row=0, column=2, rowspan=2, padx=(5, 15))

            self.card_widgets[key] = {
                "check": lbl_check,
                "name": lbl_name,
                "btn": btn_install,
                "outer": outer
            }

        self.right_container = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.right_container.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self.right_container.grid_columnconfigure(0, weight=1)
        self.right_container.grid_rowconfigure(0, weight=1)

        self.console_frame_outer = ctk.CTkFrame(self.right_container, fg_color=COLOR_BORDER, corner_radius=10)
        self.console_frame_outer.grid(row=0, column=0, sticky="nsew", pady=(0, 5))

        self.console_frame = ctk.CTkFrame(self.console_frame_outer, fg_color=COLOR_CARD, corner_radius=9)
        self.console_frame.pack(expand=True, fill="both", padx=1, pady=1)
        self.console_frame.grid_columnconfigure(0, weight=1)
        self.console_frame.grid_rowconfigure(1, weight=1)

        self.terminal_header = ctk.CTkFrame(self.console_frame, fg_color="transparent")
        self.terminal_header.grid(row=0, column=0, sticky="ew", padx=15, pady=(10, 5))

        ctk.CTkLabel(
            self.terminal_header,
            text="DIAGNOSTICS LOG",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=COLOR_TEXT_MUTED
        ).grid(row=0, column=0, sticky="w")

        self.txt_console = ctk.CTkTextbox(
            self.console_frame,
            font=ctk.CTkFont(family="Consolas", size=10),
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
            text="Ready: Scanning system environment...",
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
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=(0, 12))

        self.actions_frame = ctk.CTkFrame(self.bottom_panel, fg_color="transparent")
        self.actions_frame.grid(row=2, column=0, sticky="ew", pady=(0, 5))
        self.actions_frame.grid_columnconfigure((0, 1), weight=1)

        self.btn_scan = ctk.CTkButton(
            self.actions_frame,
            text="Re-Scan",
            height=36,
            fg_color=("#E5E7EB", "#1C2028"),
            hover_color=("#D1D5DB", "#2E3545"),
            text_color=("#374151", "#E5E7EB"),
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            command=self.scan_requirements,
            corner_radius=6
        )
        self.btn_scan.grid(row=0, column=0, padx=(0, 10), sticky="ew")

        self.btn_install_all = ctk.CTkButton(
            self.actions_frame,
            text="Install All Missing",
            height=36,
            fg_color=COLOR_ACCENT_BLUE,
            hover_color=COLOR_ACCENT_BLUE_HOVER,
            text_color="#FFFFFF",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
            command=self.install_all_missing,
            corner_radius=6
        )
        self.btn_install_all.grid(row=0, column=1, sticky="ew")

    def write_log(self, message):
        self.txt_console.configure(state="normal")
        self.txt_console.insert("end", f"{message}\n")
        self.txt_console.configure(state="disabled")
        self.txt_console.see("end")

    def scan_requirements(self):

        if self.is_installing:
            return

        self.write_log("\n--- Starting Environment Diagnostics Scan ---")
        all_passed = True

        for key, info in self.requirements.items():
            self.write_log(f"Scanning component: {info['name']}...")
            passed = info["check_fn"]()
            widgets = self.card_widgets[key]

            if passed:
                self.write_log(f"-> [OK] {info['name']} is installed.")
                widgets["check"].configure(text="☑", text_color=COLOR_ACCENT_BLUE)
                widgets["btn"].configure(
                    text="Installed",
                    state="disabled",
                    fg_color=("#E5E7EB", "#1C2028"),
                    text_color=("#9CA3AF", "#4B5563")
                )
            else:
                self.write_log(f"-> [MISSING] {info['name']} was NOT found!")
                all_passed = False
                widgets["check"].configure(text="□", text_color=("#EF4444", "#F87171"))
                widgets["btn"].configure(
                    text="Install",
                    state="normal",
                    fg_color=COLOR_ACCENT_BLUE,
                    text_color="#FFFFFF"
                )

        if all_passed:
            self.write_log("\n[SUCCESS] All system prerequisites are verified OK!")
            self.lbl_status.configure(text="Ready: All requirements are met. You can close this window.")
            self.btn_install_all.configure(state="disabled", text="All Installed")
        else:
            self.write_log("\n[WARNING] Some prerequisites are missing. Please click Install or 'Install All Missing'.")
            self.lbl_status.configure(text="Warning: Missing dependencies. Please run installer.")
            self.btn_install_all.configure(state="normal", text="Install All Missing")

        self.progress_bar.set(1.0 if all_passed else 0.0)
        self.lbl_pct.configure(text="100%" if all_passed else "0%")

    def trigger_installation(self, key):

        if self.is_installing:
            return

        self.is_installing = True
        self.lock_app(True)

        threading.Thread(target=self.install_worker_proc, args=([key],), daemon=True).start()

    def install_all_missing(self):

        if self.is_installing:
            return

        missing_keys = []
        for key, info in self.requirements.items():
            if not info["check_fn"]():
                missing_keys.append(key)

        if not missing_keys:
            messagebox.showinfo("Already Complete", "All prerequisites are already installed!", parent=self)
            return

        self.is_installing = True
        self.lock_app(True)

        threading.Thread(target=self.install_worker_proc, args=(missing_keys,), daemon=True).start()

    def install_worker_proc(self, keys):

        total = len(keys)

        for idx, key in enumerate(keys):
            info = self.requirements[key]

            def progress_callback(progress, message):

                overall_progress = (idx + progress) / total
                self.after(0, self.update_install_progress, overall_progress, f"{info['name']}: {message}")

            self.after(0, self.write_log, f"\nInstalling missing requirement: {info['name']}...")

            try:

                info["install_fn"](progress_callback)
                self.after(0, self.write_log, f"[SUCCESS] Fully integrated {info['name']}.")
            except Exception as e:
                import traceback
                self.after(0, self.write_log, f"[FATAL ERROR] Installation of {info['name']} failed: {e}")
                self.after(0, self.write_log, traceback.format_exc())
                self.after(0, lambda: messagebox.showerror("Installation Error", f"Failed to install {info['name']}:\n{e}", parent=self))
                break

        self.after(0, self.finalize_installation)

    def update_install_progress(self, progress, status_text):
        self.progress_bar.set(progress)
        self.lbl_pct.configure(text=f"{progress*100:.0f}%")
        self.lbl_status.configure(text=status_text)

    def finalize_installation(self):
        self.is_installing = False
        self.lock_app(False)
        self.progress_bar.set(0.0)
        self.lbl_pct.configure(text="0%")
        self.scan_requirements()

    def lock_app(self, lock=True):
        state = "disabled" if lock else "normal"
        self.btn_scan.configure(state=state)
        self.btn_install_all.configure(state=state)
        for key, widgets in self.card_widgets.items():
            if lock:
                widgets["btn"].configure(state="disabled")
            else:

                pass
