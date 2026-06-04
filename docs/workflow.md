# Workflow Notes

This project records a compact GPT-SoVITS v2Pro workflow:

1. Prepare selected source audio files.
2. Slice and preprocess audio for GPT-SoVITS.
3. Train the SoVITS acoustic model.
4. Train the GPT semantic model.
5. Select one clean reference audio clip and transcript.
6. Package the final inference artifacts.
7. Deploy `api_v2.py` with a custom inference config.

## Final Artifacts

The final package contains:

```text
model/shinku_v2pro-e15.ckpt
model/shinku_v2pro_e8_s384.pth
model/reference_shinku_00003390.wav
model/reference_shinku_00003390.txt
configs/tts_infer_shinku.yaml
```

## Deployment Layout

Inside a GPT-SoVITS v2Pro project, use this layout:

```text
GPT-SoVITS-v2pro/
  GPT_weights_v2/
    shinku_v2pro-e15.ckpt
  SoVITS_weights_v2/
    shinku_v2pro_e8_s384.pth
  GPT_SoVITS/
    configs/
      tts_infer_shinku.yaml
```

Reference audio can live anywhere on the GPT-SoVITS host, but the API request must use its full local path.

On the original Windows host, the reference audio path was:

```text
F:\AI_audio\shinku_selected_10mb\output\deliverables\reference_shinku_00003390.wav
```

