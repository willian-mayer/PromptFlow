@echo off
setlocal
cd /d "%~dp0"
if not exist .venv (
    py -3 -m venv .venv
    if errorlevel 1 goto :error
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 goto :error
python -m pip install -r requirements.txt
if errorlevel 1 goto :error
python -m PyInstaller --noconfirm --clean --windowed --name PromptFlow --icon assets\promptflow.ico --add-data "assets\promptflow.png;assets" main.py
if errorlevel 1 goto :error
echo.
echo Application created at dist\PromptFlow\PromptFlow.exe
echo Share the entire folder dist\PromptFlow, not just the .exe.
pause
exit /b 0
:error
echo Failed to build PromptFlow.
pause
exit /b 1
