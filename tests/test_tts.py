import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from shinku_tts import ShinkuTTS, TTSError, detect_language
from configure_dsh import build_patch


def make_wav():
    stream = io.BytesIO()
    with wave.open(stream, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(32000)
        wav.writeframes(b"\0\0" * 3200)
    return stream.getvalue()


class Backend:
    """Local HTTP double, including actual JSON request parsing and WAV bytes."""
    def __enter__(self):
        self.body = make_wav()
        self.status = 200
        self.requests = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                owner.requests.append((self.path, json.loads(self.rfile.read(int(self.headers["Content-Length"])))))
                self.send_response(owner.status)
                self.send_header("Content-Length", str(len(owner.body)))
                self.end_headers()
                self.wfile.write(owner.body)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}/tts"
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


def write_config(folder, url):
    path = folder / "tts.json"
    path.write_text(json.dumps({"api_url": url, "output_dir": "audio",
                               "reference": {"ref_audio_path": "Z:/server/neutral.wav",
                                             "prompt_text": "こんにちは", "prompt_lang": "ja"}}), encoding="utf-8")
    return path


class ClientTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "work").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "work")
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.backend = self.enterContext(Backend())
        self.config = write_config(self.folder, self.backend.url)
        self.client = ShinkuTTS(self.config)

    def test_http_contract_and_unique_paths(self):
        first = self.client.synthesize("  今日は晴れ。  ")
        second = self.client.synthesize("你好。")
        self.assertNotEqual(first["file_path"], second["file_path"])
        self.assertEqual(Path(first["file_path"]).read_bytes(), make_wav())
        endpoint, payload = self.backend.requests[0]
        self.assertEqual(endpoint, "/tts")
        self.assertEqual(payload["text"], "今日は晴れ。")
        self.assertEqual(payload["ref_audio_path"], "Z:/server/neutral.wav")
        self.assertFalse(payload["streaming_mode"])
        self.assertEqual(first["text_lang"], "ja")
        self.assertEqual(second["text_lang"], "zh")
        self.assertEqual(first["duration_seconds"], 0.1)

    def test_emotion_mapping(self):
        refs = {"soft": {"ref_audio_path": "/remote/soft.wav", "prompt_text": "静かに", "prompt_lang": "ja"}}
        (self.folder / "refs.json").write_text(json.dumps(refs), encoding="utf-8")
        data = json.loads(self.config.read_text())
        data["emotion_refs"] = "refs.json"
        self.config.write_text(json.dumps(data))
        client = ShinkuTTS(self.config)
        self.assertEqual(client.available_emotions(), ["neutral", "soft"])
        self.assertEqual(client.payload("你好", "soft", "ja")["ref_audio_path"], "/remote/soft.wav")
        self.assertEqual(client.payload("你好", "soft", "ja")["text_lang"], "ja")

    def test_rejects_invalid_inputs_before_http(self):
        for text, emotion, lang in [(" ", "neutral", "auto"), ("a" * 2001, "neutral", "auto"),
                                    ("hi", "missing", "auto"), ("hi", "neutral", "invalid")]:
            with self.assertRaises(TTSError):
                self.client.synthesize(text, emotion, lang)
        with self.assertRaises(TTSError):
            self.client.synthesize("hi", output=self.folder / "wrong.ogg")
        self.assertEqual(self.backend.requests, [])

    def test_http_and_invalid_audio_preserve_existing_output(self):
        destination = self.folder / "existing.wav"
        destination.write_bytes(b"original")
        for status, body in [(500, b'{}'), (200, b'{"error":"not audio"}'), (200, make_wav()[:-10])]:
            self.backend.status, self.backend.body = status, body
            with self.assertRaises(TTSError):
                self.client.synthesize("hi", output=destination)
            self.assertEqual(destination.read_bytes(), b"original")

    def test_ogg_failure_is_not_a_wav_with_wrong_extension(self):
        destination = self.folder / "speech.ogg"
        with patch("shinku_tts.subprocess.run", side_effect=FileNotFoundError):
            with self.assertRaises(TTSError):
                self.client.synthesize("hi", output=destination, audio_format="ogg")
        self.assertFalse(destination.exists())
        self.assertFalse(list(self.folder.glob(".shinku-*")))

    def test_cli_accepts_hermes_flags_and_reports_errors(self):
        source = self.folder / "text.txt"
        source.write_text("你好。", encoding="utf-8")
        command = [sys.executable, str(ROOT / "scripts/shinku_tts.py"), "--config", str(self.config),
                   "--text-file", str(source), "--output", str(self.folder / "cli.wav"), "--format", "wav"]
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["text_lang"], "zh")
        source.write_text("")
        failed = subprocess.run(command, capture_output=True, text=True, timeout=10)
        self.assertNotEqual(failed.returncode, 0)
        self.assertEqual(failed.stdout, "")

    def test_language_and_dsh_overlay(self):
        self.assertEqual(detect_language("Hello"), "en")
        row = build_patch(self.config, Path(sys.executable))[0]["insert"][0]
        self.assertEqual(row["config"]["serverName"], "shinku")
        self.assertGreater(row["config"]["toolCallTimeoutMs"], 150000)
        self.assertEqual(row["config"]["args"][-1], str(self.config))


if __name__ == "__main__":
    unittest.main()
