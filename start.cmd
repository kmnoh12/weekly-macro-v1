@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  py -3 -m venv .venv
  if errorlevel 1 goto fail
  .venv\Scripts\python.exe -m pip install -r requirements.txt
  if errorlevel 1 goto fail
)
.venv\Scripts\python.exe app.py serve
if errorlevel 1 goto fail
exit /b 0
:fail
echo Python, Microsoft Edge and desktop Excel are required. See README.md.
pause
exit /b 1
