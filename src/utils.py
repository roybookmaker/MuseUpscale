import os
import subprocess
import json
import shutil

def check_ffmpeg_ffprobe():

    ffmpeg_ok = shutil.which("ffmpeg") is not None
    ffprobe_ok = shutil.which("ffprobe") is not None
    return ffmpeg_ok, ffprobe_ok

def get_video_info(video_path):

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        video_path
    ]

    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
    except AttributeError:
        startupinfo = None

    result = subprocess.run(cmd, capture_output=True, encoding="utf-8", check=True, startupinfo=startupinfo)
    data = json.loads(result.stdout)

    video_stream = None
    audio_stream = None

    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video" and not video_stream:
            video_stream = stream
        elif stream.get("codec_type") == "audio" and not audio_stream:
            audio_stream = stream

    if not video_stream:
        raise ValueError("No video stream found in the source file.")

    r_frame_rate = video_stream.get("r_frame_rate", "30/1")
    if "/" in r_frame_rate:
        num, den = map(int, r_frame_rate.split("/"))
        fps = num / den if den != 0 else 30.0
    else:
        fps = float(r_frame_rate)

    duration = float(data.get("format", {}).get("duration", 0.0))
    if duration == 0.0:
        duration = float(video_stream.get("duration", 0.0))

    width = int(video_stream.get("width", 0))
    height = int(video_stream.get("height", 0))
    codec = video_stream.get("codec_name", "unknown")

    frame_count = int(video_stream.get("nb_frames", 0))
    if frame_count == 0 and duration > 0 and fps > 0:
        frame_count = int(duration * fps)

    has_audio = audio_stream is not None

    return {
        "width": width,
        "height": height,
        "fps": fps,
        "duration": duration,
        "frame_count": frame_count,
        "codec": codec,
        "has_audio": has_audio,
        "format": data.get("format", {}).get("format_name", "unknown")
    }

def get_vram_presets():

    return {
        "8GB VRAM (Safe/Low VRAM)": {
            "tile_size": 120,
            "threads": "1:2:2",
            "desc": "Best for 8GB GPUs. Safe tiling avoids Out-Of-Memory errors."
        },
        "12GB VRAM (Standard)": {
            "tile_size": 240,
            "threads": "1:2:2",
            "desc": "Balanced performance and safety for 12GB GPUs."
        },
        "16GB VRAM (Extreme Performance)": {
            "tile_size": 0,
            "threads": "1:4:4",
            "desc": "Unlocks maximum speeds for 16GB GPUs like the AMD 9060XT."
        }
    }

def get_gpu_devices():

    gpus = []
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
    except AttributeError:
        startupinfo = None

    try:
        cmd = ["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True, startupinfo=startupinfo)
        for line in res.stdout.splitlines():
            line = line.strip()
            if line:
                gpus.append(line)
    except Exception:
        pass
    return gpus
