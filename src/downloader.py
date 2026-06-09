import os
import zipfile
import requests
import shutil

REAL_ESRGAN_URL = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip"

import sys

def get_bin_dir():

    if getattr(sys, 'frozen', False):

        base_dir = os.path.dirname(sys.executable)
    else:

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "bin")

def get_realesrgan_dir():

    return os.path.join(get_bin_dir(), "realesrgan")

def get_realesrgan_executable():

    return os.path.join(get_realesrgan_dir(), "realesrgan-ncnn-vulkan.exe")

def is_realesrgan_installed():

    exe_path = get_realesrgan_executable()
    return os.path.isfile(exe_path)

def download_realesrgan(progress_callback=None):

    bin_dir = get_bin_dir()
    os.makedirs(bin_dir, exist_ok=True)

    zip_path = os.path.join(bin_dir, "realesrgan.zip")

    if progress_callback:
        progress_callback(0.0, "Initiating download from GitHub...")

    try:
        response = requests.get(REAL_ESRGAN_URL, stream=True)
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))

        downloaded = 0
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0 and progress_callback:
                        progress = downloaded / total_size

                        progress_callback(progress * 0.8, f"Downloading: {progress * 100:.1f}% ({downloaded / (1024*1024):.1f}MB / {total_size / (1024*1024):.1f}MB)")
    except Exception as e:
        if os.path.exists(zip_path):
            os.remove(zip_path)
        raise RuntimeError(f"Failed to download Real-ESRGAN: {e}")

    if progress_callback:
        progress_callback(0.85, "Extracting components...")

    try:
        realesrgan_dir = get_realesrgan_dir()
        if os.path.exists(realesrgan_dir):
            shutil.rmtree(realesrgan_dir)
        os.makedirs(realesrgan_dir, exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:

            temp_extract_dir = os.path.join(bin_dir, "temp_realesrgan")
            if os.path.exists(temp_extract_dir):
                shutil.rmtree(temp_extract_dir)
            os.makedirs(temp_extract_dir, exist_ok=True)

            zip_ref.extractall(temp_extract_dir)

            contents = os.listdir(temp_extract_dir)
            if contents:

                if len(contents) == 1 and os.path.isdir(os.path.join(temp_extract_dir, contents[0])):
                    inner_dir = os.path.join(temp_extract_dir, contents[0])
                    for item in os.listdir(inner_dir):
                        s = os.path.join(inner_dir, item)
                        d = os.path.join(realesrgan_dir, item)
                        if os.path.isdir(s):
                            shutil.copytree(s, d)
                        else:
                            shutil.copy2(s, d)
                else:

                    for item in contents:
                        s = os.path.join(temp_extract_dir, item)
                        d = os.path.join(realesrgan_dir, item)
                        if os.path.isdir(s):
                            shutil.copytree(s, d)
                        else:
                            shutil.copy2(s, d)

            shutil.rmtree(temp_extract_dir)

        os.remove(zip_path)

        if progress_callback:
            progress_callback(1.0, "Ready to use!")

    except Exception as e:
        if os.path.exists(realesrgan_dir):
            shutil.rmtree(realesrgan_dir)
        raise RuntimeError(f"Failed to extract Real-ESRGAN zip: {e}")
