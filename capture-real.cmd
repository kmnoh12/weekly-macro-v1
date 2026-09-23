@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  py -3 -m venv .venv
  if errorlevel 1 goto fail
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto fail
.venv\Scripts\python.exe app.py capture-real
if errorlevel 1 goto fail
echo Download captured. See runtime\company for the result.
pause
exit /b 0
:fail
echo Capture stopped. Check runtime\company\...\events.jsonl and stopped.png.
pause
exit /b 1
