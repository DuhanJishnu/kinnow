# Kinnow

**Drag a file, press Shift, drop it on a format.** Kinnow is a small Windows utility that converts files without opening any app or website. While you drag a file in Explorer, a radial menu appears under your cursor. Drop the file on a slice and the converted copy appears right next to the original.

Everything runs locally. No uploads, no accounts.

<!-- Add your demo GIF here, e.g.  ![Kinnow demo](docs/demo.gif) -->

Inspired by Tangerine for macOS (drag + Shift to convert). Kinnow is an independent Windows implementation written in Python.

## How to use

1. Start dragging a file in Explorer.
2. While still dragging:
   - Press **Shift** for the **Format Conversion Wheel** (`.JPG`, `.PNG`, `.HTML`, `.PDF`, etc.).
   - Press **Tab** for the **Quick Tools Wheel** (`COMPRESS`, `MERGE`, `SPLIT`).
   - *(You can also press Shift or Tab while the wheel is open to switch modes instantly!)*
3. Move onto a slice and release the mouse.
4. The converted/processed file is saved next to the original, and a tray notification confirms it (click to reveal in Explorer).

> **Tip:** press Shift or Tab *after* you start dragging. If a modifier is already held when you click, Explorer treats the click as "extend selection" and never starts a file drag.

Your original file is never moved, modified or deleted. Existing names are never overwritten: duplicate conversions become `name (1).png`.

## Supported conversions & actions

| Type | From | Available Targets / Tools |
|---|---|---|
| **Markdown** | MD, MARKDOWN | **HTML** (clean standalone document), **PDF** (printable), **TXT** |
| **PDF Tools** | PDF | **COMPRESS** (optimize file size), **SPLIT** (pages to folder), **MERGE** (combine 2+ PDFs in natural order) |
| **Images** | PNG, JPG, WEBP, BMP, GIF, TIFF | PNG, JPG, WEBP, BMP, GIF, PDF, plus **COMPRESS**, **STRIP EXIF**, **RESIZE 50%**, **GRAYSCALE** |
| **PDF Conversion** | PDF | PNG (one image, or folder of pages), TXT |
| **Audio** | MP3, WAV, OGG, FLAC, M4A | MP3, WAV, OGG, FLAC |
| **Video** | MP4, MKV, AVI, MOV, WEBM | MP4, WEBM, GIF, plus audio extraction to MP3, WAV, OGG, FLAC |

Dropping several files at once converts each of them in parallel. The wheel only offers formats that every dropped file supports.

## Requirements

- Windows 10 or 11
- Python 3.12 or newer (when running from source)
- [FFmpeg](https://ffmpeg.org) for audio and video conversions. Install it with `winget install Gyan.FFmpeg`, or place `ffmpeg.exe` in the `vendor/` folder. Image and PDF conversions work without it.

## Run from source

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
python run.py
```

Kinnow runs in the system tray (orange circle icon). Right-click the icon and choose **Quit** to exit.

Run the tests with:

```powershell
python -m pytest
```

## Build an .exe (Portable)

Kinnow is a portable app — it runs directly without needing an installer wizard or admin privileges:

```powershell
pyinstaller --noconsole --name Kinnow --icon "assets\kinnow.ico" --add-data "assets;assets" --add-binary "vendor\ffmpeg.exe;vendor" --collect-all pymupdf --clean -y run.py
```

The resulting folder is in `dist\Kinnow\`, and a ready-to-share archive is in `dist\Kinnow.zip`. Double-click `Kinnow.exe` to run immediately.

## Project structure

```
kinnow/
├── run.py                      entry point
├── requirements.txt
├── dropwheel/                  the application package
│   ├── app.py                  wires together tray icon, trigger, overlay and workers
│   ├── hotkey.py               detects "dragging + Shift" by polling input state
│   ├── worker.py               runs one conversion on a background thread
│   ├── utils.py                unique output names, Win32 key/mouse state helpers
│   ├── ui/
│   │   └── radial_menu.py      transparent overlay: drag and drop, hit-testing, painting
│   └── converters/
│       ├── registry.py         source format -> target format -> function
│       ├── images.py           Pillow
│       ├── pdf.py              PyMuPDF
│       └── media.py            FFmpeg
├── tests/                      pytest unit tests (no GUI needed)
└── vendor/                     put ffmpeg.exe here for packaging
```

## How it works

- **Trigger.** A 20 ms timer reads the left mouse button and Shift state with the Win32 `GetAsyncKeyState` call. The wheel is requested once the button is down, Shift is held and the cursor has moved a few pixels (a real drag). Polling means no keyboard hook, no extra thread and no swallowed keystrokes.
- **Overlay.** A frameless, always-on-top, non-focus-stealing Qt window that accepts drops. It stays invisible until a file drag actually enters it, so ordinary clicks never show anything. Windows treats fully transparent pixels of a layered window as click-through, so a nearly invisible fill is painted behind the wheel to keep drags from "leaving" it between slices.
- **Registry.** Converters register themselves with a decorator. The wheel asks the registry which targets exist for the dropped files and draws that many slices, so the UI never hardcodes formats.
- **Workers.** Conversions run on a Qt thread pool and report back with signals, so the UI never freezes.

## Add a new conversion

Write one function and register it. The wheel picks it up automatically.

```python
from dropwheel.converters.registry import register

@register(["md"], "html")
def markdown_to_html(src, dst):
    ...  # read src, write dst
```

Then import your module in `dropwheel/converters/__init__.py` (`load_all`).

## Known limitations

- Windows only.
- Windows does not allow a normal app to receive drops from an elevated (administrator) window. Run Kinnow as administrator if you need that.
- FFmpeg must be installed (or bundled) for audio and video.
- PDF to PNG renders at 150 DPI.
- Unsigned executables built with PyInstaller can trigger antivirus or SmartScreen warnings.

## Features

- **Drag + Shift trigger**: Instant conversion wheel appears right where your cursor is.
- **Click to reveal**: Click the completion notification (or right-click the tray icon) to reveal the converted file in Windows Explorer.
- **Zero installation**: Purely portable standalone executable.
- **Non-destructive**: Output files are saved alongside originals with collision-free naming (`(1)`, `(2)`, etc.).

## Roadmap

- Conversion history in the tray menu
- Start with Windows
- Compress, crop, trim and merge tools
- More formats (Markdown, Office documents)

## Licensing note

FFmpeg is distributed under the LGPL or GPL depending on the build. If you bundle it with Kinnow, include its license and attribution. Pillow, PyMuPDF and PySide6 have their own licenses (PyMuPDF is AGPL or commercial), so check them before distributing a build commercially.

## License

Add your license here (for example MIT for your own code).