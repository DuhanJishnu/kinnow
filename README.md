# Kinnow 🍊

**Drag a file in Windows Explorer, press Shift or Tab, drop it on an action.**

Kinnow is a lightweight, 100% offline Windows utility for instant file conversions and quick productivity tools right under your cursor. No websites, no uploads, no cloud subscriptions.

---

## ⚡ How to Use

<div style="text-align: center;">
  <video width="700" controls>
    <source src="assets/Kinnow.mp4" type="video/mp4">
    Your browser does not support the video tag.
  </video>
</div>

1. **Start dragging** any file in Windows Explorer.
2. While dragging:
   - Hold **Shift** for the **Format Conversion Wheel** (`.JPG`, `.PNG`, `.PDF`, `.DOCX`, etc.).
   - Hold **Tab** for the **Quick Tools Wheel** (`COMPRESS`, `SPLIT`, `MERGE`, `MUTE`, etc.).
   *(Press Shift or Tab while the wheel is open to switch modes instantly!)*
3. **Drop** onto a slice. The converted file appears right next to the original without overwriting.

---

## ✨ Features & Supported Formats

| Category | Formats | Actions & Tools |
|---|---|---|
| **Office & Docs** | `DOCX`, `DOC` | Convert to `PDF`, `TXT`, `HTML`, `MD`, `PNG`, `EPUB` |
| **Spreadsheets** | `XLSX`, `XLS` | Convert to `PDF` (table), `CSV`, `TSV`, `ODS` |
| **Presentations** | `PPTX`, `PPT` | Convert to `PDF`, `PNG`, `JPG` slides |
| **PDF** | `PDF` | Reverse convert to `DOCX`, `MD`, `XLSX`, `PPTX`, `PNG`, `JPG`<br>*(Tools: **COMPRESS**, **SPLIT**, **MERGE**)* |
| **Markdown & Code**| `MD`, `TXT`, `LOG`, `PY`, `JSON` | Convert to printable vector `PDF` or `HTML` |
| **Images** | `PNG`, `JPG`, `WEBP`, `BMP`, `GIF`, `TIFF` | Convert format, plus **COMPRESS**, **STRIP EXIF**, **RESIZE 50%**, **GRAYSCALE** |
| **Video & Audio** | `MP4`, `MKV`, `MOV`, `WEBM`, `MP3`, `WAV` | Convert format, plus **MUTE** (&lt;1s), **AUDIO** (to MP3), **MAKE GIF** |
| **Archives & General**| Any File, Folder, `ZIP`, `TAR`, `GZ` | **ZIP** (compress), **EXTRACT** (unzip), **METADATA** (file properties) |

- **Haptic Audio**: Subtle mechanical micro-tick sound as you hover through slices.
- **Smart Edge Clamping**: Wheel never overflows screen boundaries or multi-monitor edges.
- **Non-Destructive**: Originals are untouched; collisions are automatically named `name (1).ext`.

---

## 📦 Downloads

Grab the latest release from [GitHub Releases](https://github.com/DuhanJishnu/kinnow/releases):

- **`Kinnow-Setup.exe` (Installer - Recommended)**: Standard setup wizard that creates Desktop and Start Menu shortcuts, and automatically launches with Windows.
- **`Kinnow.zip` (Portable)**: Extract anywhere and run `Kinnow.exe` directly. No installer or admin rights needed.

> [!NOTE]
> **Windows SmartScreen Note**: Because Kinnow is a free, independent open-source project without an expensive corporate code-signing certificate, Windows SmartScreen may show a blue prompt stating *"Windows protected your PC"* when launching for the first time. Simply click **"More info"** &rarr; **"Run anyway"**. Kinnow is 100% offline and open-source.

---

## 🛠️ Run from Source

Requires Windows 10/11 and Python 3.12+:

```powershell
# Clone and enter directory
git clone https://github.com/DuhanJishnu/kinnow.git
cd kinnow

# Setup virtual environment
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

# Run Kinnow
python run.py
```

To run tests:
```powershell
pytest
```

---

## 📄 License

Released under the [MIT License](LICENSE). Copyright © 2026 Jishnu Duhan.
