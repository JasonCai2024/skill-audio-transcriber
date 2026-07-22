#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Audio Transcriber CLI Script
Extracts full TXT text or SRT subtitles from local audio/video files.
Outputs generated files in the same directory with the same basename.
Uses ServiceHub ASR and ServiceHub OSS Proxy APIs (Zero client-side OSS credentials required).
Supports automatic FFmpeg audio compression for large recording files to guarantee reliable uploads.
"""

import os
import sys
import argparse
import logging
import subprocess
import requests
import urllib3
from datetime import timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Suppress insecure HTTPS request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("audio_transcriber")

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".webm"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".wma"}
PROXY_ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a"}

FALLBACK_CONFIG_PATHS = [
    r"E:\BaiduSyncdisk\WorkSpace\config.json",
    r"E:\BaiduSyncdisk\LocalHub\BiSubtitles\config.json",
]


def get_http_session() -> requests.Session:
    """Create a configured requests session bypassing system proxies & SSL errors."""
    session = requests.Session()
    session.trust_env = False
    return session


def load_credentials() -> Dict[str, Any]:
    """
    Load credentials with priority:
    1. Environment variables / .env
    2. Fallback local config files (WorkSpace/config.json, BiSubtitles/config.json)
    """
    load_dotenv()

    username = os.getenv("SERVICEHUB_USERNAME")
    passtoken = os.getenv("SERVICEHUB_PASSTOKEN")
    api_base_url = os.getenv("SERVICEHUB_API_BASE_URL")
    provider = os.getenv("ASR_PROVIDER")
    model = os.getenv("ASR_MODEL")

    for config_path in FALLBACK_CONFIG_PATHS:
        if os.path.exists(config_path):
            try:
                import json
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)

                # Check WorkSpace/config.json format
                sh_node = cfg.get("servicehub", {}).get("wechat_proxy", {})
                if not username and sh_node.get("username"):
                    username = sh_node.get("username")
                if not passtoken and sh_node.get("passtoken"):
                    passtoken = sh_node.get("passtoken")
                if not api_base_url and sh_node.get("remote_service_url"):
                    api_base_url = sh_node.get("remote_service_url")

                # Check BiSubtitles/config.json format
                llm_node = cfg.get("llm", {})
                asr_node = cfg.get("asr", {})
                if not username and llm_node.get("username"):
                    username = llm_node.get("username")
                if not passtoken and llm_node.get("passtoken"):
                    passtoken = llm_node.get("passtoken")
                if not api_base_url and asr_node.get("api_base_url"):
                    api_base_url = asr_node.get("api_base_url")
                if not provider and asr_node.get("provider"):
                    provider = asr_node.get("provider")
                if not model and asr_node.get("model"):
                    model = asr_node.get("model")

            except Exception as e:
                logger.warning(f"Could not load fallback config from {config_path}: {e}")

    username = username or ""
    passtoken = passtoken or ""
    api_base_url = api_base_url or "https://www.ccailab.top"
    provider = provider or "aliyun"
    model = model or "paraformer-v2"

    return {
        "username": username,
        "passtoken": passtoken,
        "api_base_url": api_base_url,
        "provider": provider,
        "model": model,
    }


def prepare_audio_for_asr(input_media_path: Path) -> Path:
    """
    Preprocess and compress audio using FFmpeg.
    Converts video/unsupported audio/large audio (>20MB) to mono 16kHz 32kbps MP3
    to drastically shrink file size and prevent upload timeouts.
    """
    file_size_mb = input_media_path.stat().st_size / (1024 * 1024)
    ext = input_media_path.suffix.lower()

    # If it's already a supported small audio (<20MB), use directly
    if ext in PROXY_ALLOWED_EXTENSIONS and file_size_mb <= 20:
        logger.info(f"Using original audio file directly ({file_size_mb:.2f} MB): {input_media_path.name}")
        return input_media_path

    # Otherwise, compress/convert via FFmpeg
    output_path = input_media_path.with_name(f"{input_media_path.stem}_asr_tmp.mp3")
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_media_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-b:a",
        "32k",
        str(output_path),
    ]

    logger.info(f"Compressing audio via FFmpeg ({file_size_mb:.2f} MB): {input_media_path.name} -> {output_path.name}")
    try:
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    except FileNotFoundError:
        raise RuntimeError("FFmpeg non-existent on system PATH. Please install FFmpeg.")

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg extraction/compression failed: {result.stderr[:400]}")

    if not output_path.exists():
        raise RuntimeError("FFmpeg failed to produce output compressed file.")

    comp_size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"Audio compressed successfully: {comp_size_mb:.2f} MB")
    return output_path


def upload_to_oss_proxy(local_file: Path, creds: Dict[str, Any]) -> str:
    """Upload audio file via ServiceHub OSS proxy endpoint."""
    base_url = creds["api_base_url"]
    if not base_url.startswith("http"):
        base_url = f"https://{base_url}"
    url = f"{base_url}/api/oss/upload-audio"

    logger.info(f"Uploading file via ServiceHub OSS Proxy: {local_file.name}")
    session = get_http_session()

    with open(local_file, "rb") as f:
        files = {"audio_file": (local_file.name, f)}
        data = {
            "username": creds["username"],
            "passtoken": creds["passtoken"],
        }
        response = session.post(url, data=data, files=files, verify=False, timeout=600)

    response.raise_for_status()
    result = response.json()
    if not result.get("success"):
        error_msg = result.get("message", "Unknown error")
        raise Exception(f"ServiceHub OSS upload failed: {error_msg}")

    oss_url = result.get("data", {}).get("oss_url")
    if not oss_url:
        raise Exception("ServiceHub OSS proxy response missing oss_url")

    return oss_url


def delete_from_oss_proxy(oss_url: str, creds: Dict[str, Any]) -> bool:
    """Delete audio file via ServiceHub OSS proxy endpoint."""
    try:
        base_url = creds["api_base_url"]
        if not base_url.startswith("http"):
            base_url = f"https://{base_url}"
        url = f"{base_url}/api/oss/delete-audio"

        payload = {
            "username": creds["username"],
            "passtoken": creds["passtoken"],
            "oss_url": oss_url,
        }
        logger.info("Cleaning up temporary audio via ServiceHub OSS Proxy...")
        session = get_http_session()
        response = session.post(url, json=payload, verify=False, timeout=30)
        response.raise_for_status()
        result = response.json()
        return bool(result.get("success"))
    except Exception as e:
        logger.warning(f"Failed to delete audio via OSS Proxy {oss_url}: {e}")
        return False


def call_asr_api(media_url: str, creds: Dict[str, Any]) -> Dict[str, Any]:
    """Call ServiceHub ASR API to perform speech-to-text."""
    base_url = creds["api_base_url"]
    if not base_url.startswith("http"):
        base_url = f"https://{base_url}"
    url = f"{base_url}/api/asr/paid-rotation"

    payload = {
        "username": creds["username"],
        "passtoken": creds["passtoken"],
        "provider": creds["provider"],
        "model": creds["model"],
        "media_url": media_url,
        "deduct_points": True,
        "transcript_format": "sentence_timestamps",
    }
    headers = {"Content-Type": "application/json"}

    logger.info("Submitting ASR transcription request...")
    session = get_http_session()
    response = session.post(url, json=payload, headers=headers, verify=False, timeout=900)
    response.raise_for_status()

    result = response.json()
    if result.get("code") != 200:
        raise Exception(f"ASR API Error: {result.get('message', 'Unknown error')}")

    return result.get("data", {})


def format_srt_time(seconds: float) -> str:
    """Format seconds into SRT time format HH:MM:SS,mmm"""
    td = timedelta(seconds=seconds)
    hours = td.seconds // 3600
    minutes = (td.seconds % 3600) // 60
    secs = td.seconds % 60
    millis = td.microseconds // 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_srt(segments: List[Dict[str, Any]], srt_path: Path) -> None:
    """Generate SRT subtitle file from segments."""
    if not segments:
        logger.warning("No transcript segments found for SRT generation.")
        return

    max_time = 0
    for seg in segments:
        b = seg.get("begin_time") or seg.get("start_time", 0)
        e = seg.get("end_time") or seg.get("end_time", 0)
        max_time = max(max_time, b, e)

    is_ms = max_time > 3600  # Assume ms if > 1 hour

    lines = []
    for i, seg in enumerate(segments, start=1):
        text = seg.get("text", "").strip()
        start_t = seg.get("begin_time") or seg.get("start_time", 0)
        end_t = seg.get("end_time") or seg.get("end_time", 0)

        if is_ms:
            start_t /= 1000.0
            end_t /= 1000.0

        lines.append(str(i))
        lines.append(f"{format_srt_time(start_t)} --> {format_srt_time(end_t)}")
        lines.append(text)
        lines.append("")

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.info(f"Generated SRT file: {srt_path}")


def generate_txt(full_text: str, segments: List[Dict[str, Any]], txt_path: Path) -> None:
    """Generate plain TXT transcript file."""
    content = full_text.strip() if full_text else ""

    if not content and segments:
        content = "\n".join([seg.get("text", "").strip() for seg in segments if seg.get("text")])

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info(f"Generated TXT file: {txt_path}")


def main():
    parser = argparse.ArgumentParser(description="Audio Transcription & Subtitle Generator")
    parser.add_argument("input_path", help="Local path to input audio or video file")
    parser.add_argument(
        "--format",
        choices=["txt", "srt", "all"],
        default="all",
        help="Output format: txt, srt, or all (default: all)",
    )
    args = parser.parse_args()

    input_file = Path(args.input_path).resolve()
    if not input_file.exists():
        logger.error(f"Input file not found: {input_file}")
        sys.exit(1)

    ext = input_file.suffix.lower()
    if ext not in VIDEO_EXTENSIONS and ext not in AUDIO_EXTENSIONS:
        logger.error(f"Unsupported media format: {ext}")
        sys.exit(1)

    creds = load_credentials()
    if not creds["username"] or not creds["passtoken"]:
        logger.error("Credentials missing: ServiceHub username and passtoken must be configured.")
        sys.exit(1)

    temp_audio_path: Optional[Path] = None
    upload_file_path: Path = input_file
    oss_url: Optional[str] = None

    try:
        # Preprocess / Compress audio to ensure file size <= 25MB
        processed_path = prepare_audio_for_asr(input_file)
        if processed_path != input_file:
            temp_audio_path = processed_path
            upload_file_path = temp_audio_path

        # Upload via ServiceHub OSS Proxy API
        oss_url = upload_to_oss_proxy(upload_file_path, creds)

        # Call ASR API
        data = call_asr_api(oss_url, creds)

        full_text = data.get("transcribed_text", "")
        segments = data.get("transcript_segments", [])

        # Determine output file paths (Same directory, same stem)
        target_dir = input_file.parent

        if args.format in ["txt", "all"]:
            txt_path = target_dir / f"{input_file.stem}.txt"
            generate_txt(full_text, segments, txt_path)

        if args.format in ["srt", "all"]:
            srt_path = target_dir / f"{input_file.stem}.srt"
            generate_srt(segments, srt_path)

        logger.info("Transcription completed successfully!")

    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        sys.exit(1)

    finally:
        # Cleanup OSS Proxy object
        if oss_url:
            delete_from_oss_proxy(oss_url, creds)
        # Cleanup temporary local audio file
        if temp_audio_path and temp_audio_path.exists():
            try:
                os.remove(temp_audio_path)
                logger.info(f"Cleaned up local temp audio: {temp_audio_path.name}")
            except Exception as e:
                logger.warning(f"Could not remove temp audio {temp_audio_path}: {e}")


if __name__ == "__main__":
    main()
