@echo off
cd /d "%~dp0"
if "%~1"=="" (
  echo Drag the downloaded analysis.sapaox onto this file.
  pause
  exit /b 1
)
if not exist .venv\Scripts\python.exe (
  echo Run capture-real.cmd first to install dependencies.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
  echo Dependency installation failed.
  pause
  exit /b 1
)
.venv\Scripts\python.exe app.py inspect-ao --file "%~1"
if errorlevel 1 (
  echo AO inspection stopped. See runtime\company for details.
  pause
  exit /b 1
)
echo AO and Excel structure saved under runtime\company.
pause
