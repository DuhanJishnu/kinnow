# DropWheel

## Run (Windows)
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
winget install Gyan.FFmpeg      # or put ffmpeg.exe in vendor/
python run.py
pytest
```

## Project layout
```
dropwheel/
  app.py          wires tray icon, hotkey, overlay, worker pool
  hotkey.py       global Ctrl+Shift + mouse listener and modifier suppression
  worker.py       QRunnable that runs one conversion off the UI thread
  utils.py        unique_path(), is_left_mouse_down()
  ui/radial_menu.py   transparent overlay + drag/drop + painting
  converters/
    registry.py   @register + convert() lookup table (add formats here)
    images.py  pdf.py  media.py
tests/            pytest unit tests (no GUI needed)
vendor/           drop ffmpeg.exe here for packaging
run.py            entry point
```

## Add a conversion
```python
from dropwheel.converters.registry import register

@register(["md"], "html")
def md_to_html(src, dst): ...
```

## Package
```
pyinstaller --noconsole --name DropWheel --add-binary "vendor\ffmpeg.exe;vendor" run.py
```
