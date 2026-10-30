# API Usage

Start GPT-SoVITS API:

```bat
runtime\python.exe -u -I api_v2.py -a 0.0.0.0 -p 9880 -c GPT_SoVITS/configs/tts_infer_shinku.yaml
```

Local docs:

```text
http://127.0.0.1:9880/docs
```

Network docs:

```text
http://<server-ip>:9880/docs
```

TTS endpoint:

```text
POST http://<server-ip>:9880/tts
```

Example JSON:

```json
{
  "text": "今日はいい天気ですね。",
  "text_lang": "ja",
  "ref_audio_path": "F:\\AI_audio\\shinku_selected_10mb\\output\\deliverables\\reference_shinku_00003390.wav",
  "prompt_text": "以前は毎日のように見る夢の光景を探して 幽魔はいろいろな世界へ行っていたじゃないか",
  "prompt_lang": "ja",
  "text_split_method": "cut5",
  "batch_size": 1,
  "media_type": "wav",
  "streaming_mode": false
}
```

The response body is audio bytes. Save it as a `.wav` file when `media_type` is `wav`.

For a configurable client with language/emotion selection, Hermes CLI support, and DeepSeek Harness / QQ native voice delivery, see [the integration guide](dsh_qq.md).

