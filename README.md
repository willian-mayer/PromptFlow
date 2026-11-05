# PromptFlow

**A simple, distraction-free desktop teleprompter for macOS and Windows.**

PromptFlow helps creators, presenters, educators, and speakers write, organize, and read scripts at a comfortable pace. Built with **Python and PySide6**, it features a minimal dark interface and optional AI-assisted script writing.

## Features

- Clean script library and editor
- Import and export plain-text (`.txt`) scripts
- Full-size teleprompter with smooth automatic scrolling
- Adjustable reading speed and font size
- Mirror mode for teleprompter glass
- Optional AI script generation with OpenAI, Gemini, Claude, or Grok (your own API key required)
- Native desktop packaging with PyInstaller; packaged apps do **not** require Python, Java, or Maven on the recipient's computer

## Requirements for running from source

- Python **3.11 or newer**
- Internet connection for the first dependency installation (and for AI features)
- macOS (Intel or Apple Silicon), or Windows 10/11

## Install and run from source

### macOS — Intel (x86_64) or Apple Silicon (arm64)

1. Install Python 3.11+ from [python.org](https://www.python.org/downloads/macos/). On Apple Silicon, choose an ARM64/universal build for native performance.
2. Clone the repository or download and extract its ZIP archive.
3. Open Terminal in the project folder:

```bash
git clone https://github.com/YOUR-USERNAME/PromptFlow.git
cd PromptFlow
chmod +x run-macos.sh package-macos.sh
./run-macos.sh
```

If you downloaded the source ZIP, skip `git clone` and navigate to the extracted folder instead. The script creates `.venv`, installs dependencies, and launches PromptFlow.

### Windows 10/11

1. Install Python 3.11+ from [python.org](https://www.python.org/downloads/windows/), including the **Python launcher (`py`)**.
2. Clone the repository or download and extract the ZIP archive.
3. Open PowerShell in the project folder:

```powershell
git clone https://github.com/YOUR-USERNAME/PromptFlow.git
cd PromptFlow
.\run-windows.bat
```

If using a ZIP, skip `git clone` and open PowerShell in the extracted project folder. The script creates `.venv`, installs dependencies, and launches PromptFlow.

**Note:** Replace `YOUR-USERNAME` with the actual GitHub username or organization after publishing the repository. Git is only needed for cloning, not when downloading a ZIP.

## Build a standalone app (no Python required for end users)

Building requires Python on the **build machine**, but recipients of the packaged app do not need Python, pip, Java, or Maven.

### macOS Intel

On an Intel Mac with x86_64 Python, first grant execution permission to the packaging script (especially after downloading a ZIP):

```bash
chmod +x package-macos.sh
./package-macos.sh
```

Output: `dist/PromptFlow.app`. Zip the `.app` to share it or place it in a DMG. The recipient copies it into Applications.

### macOS Apple Silicon

On an Apple Silicon Mac with native ARM64 Python, first grant execution permission to the packaging script:

```bash
chmod +x package-macos.sh
./package-macos.sh
```

Output: `dist/PromptFlow.app` compiled for Apple Silicon. To check the Python architecture on the build machine:

```bash
python3 -c "import platform; print(platform.machine())"
```

Expected: `arm64` for Apple Silicon or `x86_64` for Intel. **One script supports both architectures, but each build targets the architecture of the Python used to build it.**

### Windows

On a Windows PC with Python installed, run:

```powershell
.\package-windows.bat
```

Output: `dist\PromptFlow\PromptFlow.exe`. **Distribute the entire `dist\PromptFlow` folder**, not only the `.exe`. Recipients can double-click `PromptFlow.exe` without installing Python.

**Cross-compilation:** PyInstaller does not directly build Windows executables on macOS or macOS apps on Windows. Build on the target OS, or use separate CI runners for each platform.

If Terminal reports `zsh: permission denied: ./package-macos.sh`, run `chmod +x package-macos.sh` and try again. Alternatively, run `bash package-macos.sh` without changing permissions.

## AI script generation

Click **Generate with AI**, choose a provider, enter a supported model and your own API key, then describe your idea. You can review and edit the result before inserting it into the script editor.

- API keys are not stored by PromptFlow; they are used for the current session.
- Requests are sent directly to the selected AI provider over the internet.
- Providers may charge for API usage. Default model names may change over time.
- Generated scripts are requested in English by default.

## Scripts and storage

Saved scripts appear in the library when they are stored in `~/Documents/PromptFlow/Scripts` on macOS or the corresponding `Documents/PromptFlow/Scripts` directory on Windows. You can also open and save `.txt` files elsewhere.

## Project structure

```text
PromptFlow/
├── main.py                # Desktop UI and teleprompter
├── ai_service.py          # Optional AI provider integrations
├── requirements.txt
├── assets/
│   ├── promptflow.png     # Window icon
│   ├── promptflow.icns    # macOS app icon
│   └── promptflow.ico     # Windows app icon
├── run-macos.sh
├── run-windows.bat
├── package-macos.sh
├── package-windows.bat
└── README.md
```

## Notes for distribution

- Unsigned macOS apps may be blocked by Gatekeeper; public releases should be signed and notarized with Apple Developer ID.
- Unsigned Windows apps may trigger Microsoft Defender SmartScreen warnings; code signing is recommended for public releases.
- This source repository is not an installer. For a download-and-double-click experience, publish the **built** artifacts in GitHub Releases.
- Add a `LICENSE` file before claiming that the project is open source under a particular license.

## Development status

The Python files have been syntax-checked, but this updated release has **not** been tested in a graphical macOS or Windows environment here. Please test on both architectures and Windows before publishing official binaries.
