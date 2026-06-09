import os
import subprocess
import threading
import shutil
import time
import re
from .downloader import get_realesrgan_executable
from .utils import get_video_info

class UpscaleEngine:
    def __init__(self):
        self.active_process = None
        self.is_running = False
        self.cancel_requested = False
        self.current_phase = ""

    def run_upscale(self, video_path, process_dir, model_name, scale, tile_size, threads, gpu_id, img_format, input_resize_pct, output_resize_pct, progress_callback, log_callback):

        self.is_running = True
        self.cancel_requested = False
        temp_dir = None

        try:

            log_callback("Analyzing video metadata...")
            info = get_video_info(video_path)
            log_callback(f"Video Info: Resolution={info['width']}x{info['height']}, FPS={info['fps']:.2f}, Frames={info['frame_count']}, Audio={info['has_audio']}")

            video_basename = os.path.splitext(os.path.basename(video_path))[0]

            temp_dir = os.path.join(process_dir, f"muse_temp_{int(time.time())}")

            os.makedirs(temp_dir, exist_ok=True)

            frames_in = os.path.join(temp_dir, "frames_in")
            frames_out = os.path.join(temp_dir, "frames_out")
            os.makedirs(frames_in, exist_ok=True)
            os.makedirs(frames_out, exist_ok=True)

            output_name = f"{video_basename}_upscaled_{model_name}_x{scale}.mp4"
            output_path = os.path.join(process_dir, output_name)

            if os.path.exists(output_path):

                output_name = f"{video_basename}_upscaled_{model_name}_x{scale}_{int(time.time())}.mp4"
                output_path = os.path.join(process_dir, output_name)

            log_callback(f"Temporary workspace: {temp_dir}")
            log_callback(f"Final output file: {output_path}")

            if self.cancel_requested:
                raise InterruptedError("Process cancelled by user.")

            self.current_phase = "Extraction"
            log_callback("\n--- Phase 1: Lossless Frame & Audio Extraction ---")
            progress_callback(self.current_phase, 0.0)

            img_format = img_format.lower()
            if img_format not in ["jpg", "webp", "png"]:
                img_format = "jpg"

            if img_format == "jpg":
                extract_frames_cmd = [
                    "ffmpeg", "-y",
                    "-i", video_path,
                    "-qscale:v", "2",
                    "-vsync", "0",
                    os.path.join(frames_in, "frame_%08d.jpg")
                ]
                log_callback("Extracting video frames to high-quality JPG (90% disk space savings)...")
            elif img_format == "webp":
                extract_frames_cmd = [
                    "ffmpeg", "-y",
                    "-i", video_path,
                    "-vcodec", "libwebp",
                    "-lossless", "0",
                    "-q:v", "85",
                    "-vsync", "0",
                    os.path.join(frames_in, "frame_%08d.webp")
                ]
                log_callback("Extracting video frames to compressed WebP...")
            else:
                extract_frames_cmd = [
                    "ffmpeg", "-y",
                    "-i", video_path,
                    "-qscale:v", "1",
                    "-qmin", "1",
                    "-qmax", "1",
                    "-vsync", "0",
                    os.path.join(frames_in, "frame_%08d.png")
                ]
                log_callback("Extracting video frames to lossless PNG...")

            self._run_cmd_live(extract_frames_cmd, log_callback, progress_callback, 0.3)

            if self.cancel_requested:
                raise InterruptedError("Process cancelled by user.")

            audio_path = os.path.join(temp_dir, "audio.wav")
            if info["has_audio"]:
                log_callback("Extracting audio stream to WAV...")
                extract_audio_cmd = [
                    "ffmpeg", "-y",
                    "-i", video_path,
                    "-vn",
                    "-c:a", "pcm_s16le",
                    audio_path
                ]
                self._run_cmd_live(extract_audio_cmd, log_callback, None, 0.0)
            else:
                log_callback("No audio track detected in source video.")

            if input_resize_pct < 100:
                log_callback(f"\n--- Phase 1.5: Pre-Upscale Image Resizer ({input_resize_pct}%) ---")
                self._resize_frame_folder(frames_in, input_resize_pct, img_format, log_callback)

            if self.cancel_requested:
                raise InterruptedError("Process cancelled by user.")

            self.current_phase = "Upscaling"
            log_callback("\n--- Phase 2: AI Video Frame Upscaling ---")
            progress_callback(self.current_phase, 0.0)

            realesrgan_exe = get_realesrgan_executable()
            if not os.path.isfile(realesrgan_exe):
                raise FileNotFoundError(f"Real-ESRGAN executable not found. Please install dependencies first.")

            upscale_cmd = [
                realesrgan_exe,
                "-i", frames_in,
                "-o", frames_out,
                "-n", model_name,
                "-s", str(scale),
                "-t", str(tile_size),
                "-j", threads,
                "-f", img_format
            ]

            if gpu_id != "Auto-detect":
                match = re.search(r"Device\s+(\d+)", gpu_id)
                if match:
                    upscale_cmd.extend(["-g", match.group(1)])

            log_callback(f"Running Real-ESRGAN Vulkan GPU Accel...")
            log_callback(f"Command parameters: Model={model_name}, Scale={scale}x, Tile Size={tile_size if tile_size > 0 else 'Auto'}, Threads={threads}, GPU={gpu_id}, Format={img_format}")

            self._run_realesrgan_live(upscale_cmd, log_callback, progress_callback)

            if self.cancel_requested:
                raise InterruptedError("Process cancelled by user.")

            if output_resize_pct < 100:
                log_callback(f"\n--- Phase 2.5: Post-Upscale Image Resizer ({output_resize_pct}%) ---")
                self._resize_frame_folder(frames_out, output_resize_pct, img_format, log_callback)

            self.current_phase = "Merging"
            log_callback("\n--- Phase 3: Stitching Upscaled Video & Audio ---")
            progress_callback(self.current_phase, 0.0)

            merge_cmd = [
                "ffmpeg", "-y",
                "-framerate", str(info["fps"]),
                "-i", os.path.join(frames_out, f"frame_%08d.{img_format}")
            ]

            if info["has_audio"] and os.path.exists(audio_path):
                merge_cmd.extend([
                    "-i", audio_path,
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    output_path
                ])
            else:
                merge_cmd.extend([
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    output_path
                ])

            log_callback("Assembling frames into H.264 MP4 container...")
            self._run_cmd_live(merge_cmd, log_callback, progress_callback, 0.95)

            self.current_phase = "Completed"
            log_callback(f"\n--- SUCCESS ---")
            log_callback(f"Upscaled video successfully created at:\n{output_path}")
            progress_callback(self.current_phase, 1.0)

        except InterruptedError as ie:
            self.current_phase = "Cancelled"
            log_callback(f"\n[!] Process Cancelled: {ie}")
            progress_callback(self.current_phase, 0.0)
        except Exception as e:
            self.current_phase = "Failed"
            log_callback(f"\n[ERROR] Pipeline failed with error: {e}")
            progress_callback(self.current_phase, 0.0)
        finally:
            self.is_running = False
            self.active_process = None

            if temp_dir and os.path.exists(temp_dir):
                log_callback(f"Cleaning up temporary workspace files...")
                try:
                    shutil.rmtree(temp_dir)
                    log_callback("Cleanup completed.")
                except Exception as e:
                    log_callback(f"Warning: Cleanup failed for {temp_dir}: {e}")

    def cancel(self):

        if not self.is_running:
            return

        self.cancel_requested = True
        if self.active_process:
            try:
                self.active_process.terminate()

                time.sleep(0.5)
                self.active_process.kill()
            except Exception:
                pass

    def _run_cmd_live(self, cmd, log_callback, progress_callback=None, progress_base=0.0):

        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0
        except AttributeError:
            startupinfo = None

        self.active_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            bufsize=1,
            startupinfo=startupinfo
        )

        for line in iter(self.active_process.stdout.readline, ""):
            if self.cancel_requested:
                self.active_process.terminate()
                break
            stripped = line.strip()
            if stripped:

                if "frame=" in stripped or "size=" in stripped:

                    pass
                else:
                    log_callback(stripped)

        self.active_process.stdout.close()
        return_code = self.active_process.wait()

        if return_code != 0 and not self.cancel_requested:
            raise subprocess.CalledProcessError(return_code, cmd)

    def _run_realesrgan_live(self, cmd, log_callback, progress_callback):

        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0
        except AttributeError:
            startupinfo = None

        self.active_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            bufsize=1,
            startupinfo=startupinfo
        )

        def read_stderr():
            percentage_pattern = re.compile(r"(\d+\.\d+)%")
            for line in iter(self.active_process.stderr.readline, ""):
                if self.cancel_requested:
                    break
                stripped = line.strip()
                if stripped:
                    match = percentage_pattern.search(stripped)
                    if match:
                        percent = float(match.group(1))
                        progress_callback(self.current_phase, percent / 100.0)
                    else:

                        log_callback(f"[Real-ESRGAN] {stripped}")
            self.active_process.stderr.close()

        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stderr_thread.start()

        for line in iter(self.active_process.stdout.readline, ""):
            if self.cancel_requested:
                break
            stripped = line.strip()
            if stripped:
                log_callback(f"[Real-ESRGAN Info] {stripped}")
        self.active_process.stdout.close()

        return_code = self.active_process.wait()
        stderr_thread.join()

        if return_code != 0 and not self.cancel_requested:
            raise subprocess.CalledProcessError(return_code, cmd)

    def _resize_frame_folder(self, folder_path, pct, img_format, log_callback):
        from PIL import Image
        import os

        files = [f for f in os.listdir(folder_path) if f.endswith(f".{img_format}")]
        total_files = len(files)
        if total_files == 0:
            return

        log_interval = max(1, total_files // 10)
        scale_factor = pct / 100.0

        for idx, filename in enumerate(files):
            if self.cancel_requested:
                break
            filepath = os.path.join(folder_path, filename)
            try:
                with Image.open(filepath) as img:
                    w, h = img.size
                    new_w = int(w * scale_factor)
                    new_h = int(h * scale_factor)

                    resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                    if img_format == "jpg":
                        resized_img.save(filepath, "JPEG", quality=90)
                    elif img_format == "webp":
                        resized_img.save(filepath, "WEBP", quality=85)
                    else:
                        resized_img.save(filepath, "PNG")
            except Exception as e:
                log_callback(f"[Warning] Failed to resize frame {filename}: {e}")

            if (idx + 1) % log_interval == 0 or (idx + 1) == total_files:
                log_callback(f"Resized {idx + 1}/{total_files} frames ({((idx + 1)/total_files)*100:.0f}%)")
