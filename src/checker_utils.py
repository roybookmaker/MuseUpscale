import os
import sys
import shutil
import zipfile
import subprocess
import requests

from .downloader import is_realesrgan_installed, download_realesrgan

FFMPEG_ZIP_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

def check_ffmpeg():

    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None

def check_realesrgan():

    return is_realesrgan_installed()

def get_install_dir():

    app_data = os.environ.get("APPDATA", os.path.expanduser("~\\AppData\\Roaming"))
    install_dir = os.path.join(app_data, "MuseUpscale")
    os.makedirs(install_dir, exist_ok=True)
    return install_dir

def download_file(url, dest_path, progress_cb=None):

    response = requests.get(url, stream=True)
    response.raise_for_status()
    total_size = int(response.headers.get("content-length", 0))

    downloaded = 0
    with open(dest_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0 and progress_cb:
                    progress_cb(downloaded / total_size, f"Downloading: {downloaded / (1024*1024):.1f}MB / {total_size / (1024*1024):.1f}MB")

def add_to_user_path(path_dir):

    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
    except AttributeError:
        startupinfo = None

    try:

        cmd_get = ["powershell", "-NoProfile", "-Command", "[Environment]::GetEnvironmentVariable('PATH', 'User')"]
        res = subprocess.run(cmd_get, capture_output=True, text=True, check=True, startupinfo=startupinfo)
        current_path = res.stdout.strip()

        if path_dir.lower() not in current_path.lower():
            new_path = f"{current_path};{path_dir}" if current_path else path_dir
            cmd_set = ["powershell", "-NoProfile", "-Command", f"[Environment]::SetEnvironmentVariable('PATH', '{new_path}', 'User')"]
            subprocess.run(cmd_set, check=True, startupinfo=startupinfo)

            os.environ["PATH"] = os.environ["PATH"] + os.path.pathsep + path_dir
            return True
    except Exception:
        pass
    return False

def install_ffmpeg(progress_cb):

    install_dir = get_install_dir()
    ffmpeg_dir = os.path.join(install_dir, "ffmpeg")
    zip_path = os.path.join(install_dir, "ffmpeg.zip")

    progress_cb(0.1, "Downloading FFmpeg static build (~35MB)...")
    download_file(FFMPEG_ZIP_URL, zip_path, lambda p, msg: progress_cb(0.1 + p * 0.7, msg))

    progress_cb(0.85, "Extracting FFmpeg zip files...")

    if os.path.exists(ffmpeg_dir):
        try:
            shutil.rmtree(ffmpeg_dir)
        except Exception:
            pass

    os.makedirs(ffmpeg_dir, exist_ok=True)

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        temp_extract = os.path.join(install_dir, "ffmpeg_temp")
        if os.path.exists(temp_extract):
            shutil.rmtree(temp_extract)
        os.makedirs(temp_extract, exist_ok=True)

        zip_ref.extractall(temp_extract)

        contents = os.listdir(temp_extract)
        if contents:
            inner_dir = os.path.join(temp_extract, contents[0])
            for item in os.listdir(inner_dir):
                s = os.path.join(inner_dir, item)
                d = os.path.join(ffmpeg_dir, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d)
                else:
                    shutil.copy2(s, d)

        shutil.rmtree(temp_extract)

    if os.path.exists(zip_path):
        try:
            os.remove(zip_path)
        except Exception:
            pass

    progress_cb(0.95, "Configuring Environment PATH variables...")
    ffmpeg_bin_dir = os.path.join(ffmpeg_dir, "bin")
    add_to_user_path(ffmpeg_bin_dir)

    progress_cb(1.0, "FFmpeg Installed and PATH updated!")
    return True
