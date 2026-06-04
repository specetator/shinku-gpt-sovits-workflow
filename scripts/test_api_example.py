from pathlib import Path

import requests


API_URL = "http://10.10.20.187:9880/tts"
OUTPUT_PATH = Path("shinku_reply.wav")

payload = {
    "text": "今日はいい天気ですね。",
    "text_lang": "ja",
    "ref_audio_path": r"F:\AI_audio\shinku_selected_10mb\output\deliverables\reference_shinku_00003390.wav",
    "prompt_text": "以前は毎日のように見る夢の光景を探して 幽魔はいろいろな世界へ行っていたじゃないか",
    "prompt_lang": "ja",
    "text_split_method": "cut5",
    "batch_size": 1,
    "media_type": "wav",
    "streaming_mode": False,
}

response = requests.post(API_URL, json=payload, timeout=120)
response.raise_for_status()

OUTPUT_PATH.write_bytes(response.content)
print(f"Saved: {OUTPUT_PATH.resolve()}")
