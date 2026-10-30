#!/usr/bin/env python3
"""Shared GPT-SoVITS client for Hermes, DSH and other local callers (Python 3.10+)."""
from __future__ import annotations

import argparse
import io
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import uuid
import wave

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ("auto", "ja", "zh", "en", "ko", "yue", "all_ja", "all_zh", "all_ko", "all_yue")
MAX_AUDIO_BYTES = 64 * 1024 * 1024


class TTSError(ValueError):
    """Actionable configuration, synthesis or conversion failure."""


def local_path(value: str, base: Path) -> Path:
    path = Path(value).expanduser()
    return (path if path.is_absolute() else base / path).resolve()


def read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise TTSError(f"Cannot read JSON config {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise TTSError(f"Expected a JSON object: {path}")
    return data


def detect_language(text: str) -> str:
    if any("\u3040" <= c <= "\u30ff" for c in text):
        return "ja"
    if any("\u4e00" <= c <= "\u9fff" for c in text):
        return "zh"
    return "en"


class ShinkuTTS:
    def __init__(self, config_path: str | Path | None = None):
        self.config_path = Path(config_path or os.environ.get(
            "SHINKU_CONFIG", ROOT / "configs/tts.local.json"
        )).expanduser().resolve()
        self.config = read_json(self.config_path)
        self.base = self.config_path.parent
        self.api_url = self.config.get("api_url", "http://127.0.0.1:9880/tts")
        parsed = urlparse(self.api_url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise TTSError("api_url must be an http(s) GPT-SoVITS /tts endpoint")
        self.timeout = self.config.get("timeout_seconds", 120)
        if (isinstance(self.timeout, bool) or not isinstance(self.timeout, (float, int))
                or not math.isfinite(self.timeout) or not 0 < self.timeout <= 150):
            raise TTSError("timeout_seconds must be between 0 and 150")
        self.output_dir = local_path(self.config.get("output_dir", "../outputs/audio"), self.base)
        self.emotions = {}
        if self.config.get("emotion_refs"):
            self.emotions = read_json(local_path(self.config["emotion_refs"], self.base))

    def available_emotions(self) -> list[str]:
        return sorted({"neutral", *self.emotions})

    def payload(self, text: str, emotion: str = "neutral", lang: str = "auto") -> dict:
        if not isinstance(text, str) or not text.strip():
            raise TTSError("Text must not be empty")
        if len(text) > 2000:
            raise TTSError("Split text into utterances of at most 2000 characters")
        if lang not in LANGUAGES:
            raise TTSError(f"Unsupported language: {lang}")
        if emotion in self.emotions:
            ref = self.emotions[emotion]
        elif emotion == "neutral":
            ref = self.config.get("reference", {})
        else:
            raise TTSError(f"Unknown emotion {emotion!r}; available: {self.available_emotions()}")
        if not isinstance(ref, dict):
            raise TTSError(f"Invalid reference for emotion {emotion!r}")
        for key in ("ref_audio_path", "prompt_text", "prompt_lang"):
            if not isinstance(ref.get(key), str) or not ref[key].strip():
                raise TTSError(f"Missing {key} for emotion {emotion!r}")
        # Reference paths belong to the API host, NOT this client machine.
        return {
            "text": text.strip(), "text_lang": detect_language(text) if lang == "auto" else lang,
            "ref_audio_path": ref["ref_audio_path"], "prompt_text": ref["prompt_text"],
            "prompt_lang": ref["prompt_lang"], "text_split_method": "cut5",
            "batch_size": 1, "media_type": "wav", "streaming_mode": False,
        }

    def synthesize(self, text: str, emotion: str = "neutral", lang: str = "auto",
                   output: str | Path | None = None, audio_format: str = "wav") -> dict:
        if audio_format not in ("wav", "ogg"):
            raise TTSError("format must be wav or ogg")
        payload = self.payload(text, emotion, lang)
        destination = (Path(output).expanduser().resolve() if output else
                       self.output_dir / f"shinku-{uuid.uuid4().hex}.{audio_format}")
        if destination.suffix.lower() != f".{audio_format}":
            raise TTSError("Output suffix must match the selected audio format")
        request = Request(self.api_url, data=json.dumps(payload).encode("utf-8"),
                          headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                audio = response.read(MAX_AUDIO_BYTES + 1)
        except HTTPError as exc:
            raise TTSError(f"GPT-SoVITS returned HTTP {exc.code}; check its server log") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise TTSError(f"GPT-SoVITS request failed: {exc}") from exc
        if len(audio) > MAX_AUDIO_BYTES:
            raise TTSError("Audio response exceeds 64 MiB")
        try:
            with wave.open(io.BytesIO(audio), "rb") as wav:
                frames, rate = wav.getnframes(), wav.getframerate()
                if frames <= 0 or rate <= 0:
                    raise TTSError("GPT-SoVITS returned an empty WAV")
                expected = frames * wav.getnchannels() * wav.getsampwidth()
                if len(wav.readframes(frames)) != expected:
                    raise TTSError("GPT-SoVITS returned a truncated WAV")
                duration = frames / rate
        except (wave.Error, EOFError) as exc:
            raise TTSError("GPT-SoVITS did not return a valid PCM WAV") from exc
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Stage beside the output; never expose partial audio or rename WAV as OGG.
        with tempfile.TemporaryDirectory(prefix=".shinku-", dir=destination.parent) as scratch:
            wav_path = Path(scratch) / "speech.wav"
            wav_path.write_bytes(audio)
            staged = wav_path
            if audio_format == "ogg":
                staged = Path(scratch) / "speech.ogg"
                try:
                    subprocess.run([self.config.get("ffmpeg", "ffmpeg"), "-nostdin", "-y",
                                    "-i", str(wav_path), "-c:a", "libopus", "-b:a", "64k",
                                    "-ar", "48000", "-ac", "1", "-application", "voip", str(staged)],
                                   check=True, capture_output=True, timeout=30)
                except (OSError, subprocess.SubprocessError) as exc:
                    raise TTSError("OGG conversion failed; install ffmpeg with libopus or use WAV") from exc
            os.replace(staged, destination)
        return {"file_path": str(destination), "file_uri": destination.as_uri(),
                "mime_type": "audio/wav" if audio_format == "wav" else "audio/ogg",
                "bytes": destination.stat().st_size, "duration_seconds": round(duration, 3),
                "emotion": emotion, "text_lang": payload["text_lang"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help="JSON config; defaults to SHINKU_CONFIG or configs/tts.local.json")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text")
    source.add_argument("--text-file", help="UTF-8 input file; use - for stdin")
    parser.add_argument("--output", help="Destination audio path (otherwise a unique file is created)")
    parser.add_argument("--emotion", default="neutral")
    parser.add_argument("--lang", choices=LANGUAGES, default="auto")
    parser.add_argument("--format", choices=("wav", "ogg"), default="wav")
    args = parser.parse_args()
    try:
        text = args.text if args.text is not None else (
            sys.stdin.read() if args.text_file == "-" else Path(args.text_file).read_text(encoding="utf-8-sig"))
        result = ShinkuTTS(args.config).synthesize(text, args.emotion, args.lang, args.output, args.format)
        print(json.dumps(result, ensure_ascii=True))
        return 0
    except (TTSError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
