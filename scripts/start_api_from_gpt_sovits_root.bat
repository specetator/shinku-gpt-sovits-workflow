@echo off
echo Starting Shinku GPT-SoVITS API...
echo.
echo Run this file from the GPT-SoVITS project root, or copy it into that root first.
echo.
runtime\python.exe -u -I api_v2.py -a 0.0.0.0 -p 9880 -c GPT_SoVITS/configs/tts_infer_shinku.yaml
