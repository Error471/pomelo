@echo off
cd /d "%~dp0"
if not exist .venv ( py -3 -m venv .venv )
call .venv\Scripts\activate.bat
pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --windowed --name Pomelo --icon assets\pomelo.ico ^
  --add-data "assets;assets" ^
  --collect-data imageio_ffmpeg --collect-binaries imageio_ffmpeg ^
  --collect-all pillow_heif --collect-submodules pomelo.ops ^
  main.py
echo.
echo App generada en dist\Pomelo\Pomelo.exe
pause
