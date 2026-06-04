@echo off
echo Starting Shinku GPT-SoVITS API...
echo.
echo When you see "Uvicorn running on http://0.0.0.0:9880", open:
echo   http://127.0.0.1:9880/docs
echo.
echo Do not close this window while using the API.
echo.
runtime\python.exe -u -I api_v2.py -a 0.0.0.0 -p 9880 -c GPT_SoVITS/configs/tts_infer_shinku.yaml
