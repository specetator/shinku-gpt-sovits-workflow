# Shinku GPT-SoVITS Workflow

This repository documents a GPT-SoVITS v2Pro voice cloning workflow and shares the final model artifacts needed to run the voice through the GPT-SoVITS API.

## Contents

Core artifacts:

- `model/shinku_v2pro-e15.ckpt` - GPT semantic model weights
- `model/shinku_v2pro_e8_s384.pth` - SoVITS acoustic model weights
- `model/reference_shinku_00003390.wav` - reference audio used for inference
- `model/reference_shinku_00003390.txt` - reference transcript

Support files:

- `configs/tts_infer_shinku.yaml` - GPT-SoVITS API inference config
- `scripts/test_api_example.py` - Python example for calling the `/tts` API
- `scripts/start_api_from_gpt_sovits_root.bat` - Windows API startup helper
- `docs/workflow.md` - training and packaging notes
- `docs/api_usage.md` - API usage guide
- `MODEL_CARD.md` - model usage notes and limitations

## Requirements

- GPT-SoVITS v2Pro
- Windows or Linux environment capable of running GPT-SoVITS
- CUDA GPU recommended
- Git LFS for downloading model files from this repository

The large model files are tracked with Git LFS. Before cloning, install Git LFS:

```bash
git lfs install
git clone <this-repository-url>
```

## Quick Start

1. Install and verify GPT-SoVITS v2Pro.
2. Copy the model files into your GPT-SoVITS project:

```text
model/shinku_v2pro-e15.ckpt        -> GPT_weights_v2/shinku_v2pro-e15.ckpt
model/shinku_v2pro_e8_s384.pth     -> SoVITS_weights_v2/shinku_v2pro_e8_s384.pth
configs/tts_infer_shinku.yaml      -> GPT_SoVITS/configs/tts_infer_shinku.yaml
```

3. Start the API from the GPT-SoVITS root directory:

```bat
runtime\python.exe -u -I api_v2.py -a 0.0.0.0 -p 9880 -c GPT_SoVITS/configs/tts_infer_shinku.yaml
```

4. Open the API docs:

```text
http://127.0.0.1:9880/docs
```

5. Call the TTS endpoint:

```text
POST http://127.0.0.1:9880/tts
```

See `docs/api_usage.md` for a complete request example.

## Reference Prompt

Reference text:

```text
以前は毎日のように見る夢の光景を探して 幽魔はいろいろな世界へ行っていたじゃないか
```

Language:

```text
ja
```

## Notes

- `0.0.0.0` is a listening address, not a browser URL. Use `127.0.0.1` locally or the server IP from another machine.
- The `ref_audio_path` sent to the API must be a path that exists on the machine running GPT-SoVITS.
- Check the original GPT-SoVITS license and the rights of any training data before redistributing trained voice models.
