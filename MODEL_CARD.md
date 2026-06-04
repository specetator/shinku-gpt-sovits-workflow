# Model Card

## Model

Shinku GPT-SoVITS v2Pro voice model.

## Files

- `model/shinku_v2pro-e15.ckpt`
- `model/shinku_v2pro_e8_s384.pth`
- `model/reference_shinku_00003390.wav`
- `model/reference_shinku_00003390.txt`

## Intended Use

This model package is intended for research, workflow documentation, and personal experimentation with GPT-SoVITS inference.

## Inference

Use GPT-SoVITS `api_v2.py` with:

```text
configs/tts_infer_shinku.yaml
```

Recommended API endpoint:

```text
POST /tts
```

## Limitations

- Output quality depends on input text, language tags, reference audio quality, and GPT-SoVITS runtime settings.
- The reference audio path must exist on the host running GPT-SoVITS.
- Redistribution of trained voice models may require permission from the rights holder of the original audio source.

