# Gantt Chart Viewer (PySide6 + Plotly)

This repository contains a prototype that:
- loads a CSV,
- allows filtering by start/end date and project manager,
- renders an interactive Gantt chart using Plotly inside a PySide6 QWebEngineView,
- exports the chart to PNG, PDF, or HTML.

## Quick start

1. Create a virtual environment (recommended):

```bash
uv venv .venv
source venv/bin/activate   # macOS/Linux
venv\Scripts\activate     # Windows
```

2. Install dependencies:

```bash
uv sync
```

3. Run the app:

```bash
uv run Application.py
```

## Build an executable (.exe)

PyInstaller:
```bash
uv run pyinstaller --noconfirm --onefile --windowed --name "AsanaGanttExporter" --collect-all PySide6 --hidden-import PySide6.QtWebEngineWidgets --hidden-import PySide6.QtWebEngineCore ".\src\Application.py"
```
Nuitka
```bash
uv run -m nuitka --deployment --output-filename="Asana Gantt Exporter" --windows-icon-from-ico=".\logos\Asana Gantt Exporter 3-2.ico" --mingw64 --standalone --onefile --enable-plugin=pyside6 --include-package=plotly --include-package=_plotly_utils --include-package-data=plotly --include-package=kaleido --include-package-data=kaleido --nofollow-import-to=pytest --windows-console-mode=disable .\src\Application.py
```
