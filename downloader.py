import os
import tempfile
from urllib.parse import urlparse

from yt_dlp import YoutubeDL

from config import MAX_FILE_SIZE_MB


def validate_url(url):
    try:
        parsed = urlparse(url)
        return (
            parsed.scheme in ("http", "https")
            and bool(parsed.netloc)
            and " " not in url
        )
    except Exception:
        return False


def download_media(url, quality):
    if not validate_url(url):
        raise ValueError("Invalid URL")

    # Telegram upload limits vary by API/account configuration.
    # Keep a conservative default; increase only if your delivery method supports it.
    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    temp_dir = tempfile.mkdtemp(prefix="media_bot_")

    if quality == "audio":
        output_template = os.path.join(temp_dir, "%(title).70s.%(ext)s")
        options = {
            "format": "bestaudio/best",
            "outtmpl": output_template,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "max_filesize": max_bytes,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192"
            }]
        }
        media_kind = "audio"
    else:
        if quality == "best":
            format_selector = "bestvideo+bestaudio/best"
        else:
            height = int(quality)
            format_selector = (
                f"bestvideo[height<={height}]+bestaudio/"
                f"best[height<={height}]/best"
            )

        output_template = os.path.join(temp_dir, "%(title).70s.%(ext)s")
        options = {
            "format": format_selector,
            "outtmpl": output_template,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "merge_output_format": "mp4",
            "max_filesize": max_bytes
        }
        media_kind = "video"

    with YoutubeDL(options) as ydl:
        ydl.download([url])

    candidates = [
        os.path.join(temp_dir, name)
        for name in os.listdir(temp_dir)
        if os.path.isfile(os.path.join(temp_dir, name))
    ]
    if not candidates:
        raise RuntimeError("No output file was created")

    # Pick the largest generated file, usually the merged media file.
    result_path = max(candidates, key=os.path.getsize)
    if os.path.getsize(result_path) > max_bytes:
        raise RuntimeError("File exceeds configured upload size")
    return result_path, media_kind
