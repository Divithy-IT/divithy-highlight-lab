@echo off
chcp 65001 >nul
if "%~1"=="" (
  echo Przeciagnij plik MP4 na ten plik.
  pause
  exit /b 1
)
"%~dp0.venv\Scripts\python.exe" "%~dp0censor_profanity.py" "%~1" --render
echo.
echo Gotowe. Oryginal pozostal bez zmian.
pause
