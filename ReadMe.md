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

Run PyInstaller:
```bash
uv run pyinstaller --noconfirm --optimize 2 --onedir --windowed --name "AsanaGanttExporter" --icon="logos\Asana Gantt Exporter 3-2.ico" --collect-all PySide6 --hidden-import PySide6.QtWebEngineWidgets --hidden-import PySide6.QtWebEngineCore ".\src\Application.py"
```
Then run the InnoSetup script to create an installer