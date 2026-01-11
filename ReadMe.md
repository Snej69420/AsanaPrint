# Gantt Chart Viewer (PySide6 + Plotly)

This repository contains a single-file prototype `main.py` that:
- loads a CSV,
- allows filtering by start/end date and project manager,
- renders an interactive Gantt chart using Plotly inside a PySide6 QWebEngineView,
- exports the chart to PNG, PDF (requires `kaleido`), or HTML.

## Future Work:
- Config enable setting default file paths for saving and loading
  - 

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

4. Load `example.csv` via the "Load CSV" button and play with filters.

## Build an executable (.exe)

We recommend using PyInstaller. A simple command:

```bash
uv run pyinstaller --noconfirm --onefile --windowed --name "AsanaGanttExporter" --collect-all PySide6 --hidden-import PySide6.QtWebEngineWidgets --hidden-import PySide6.QtWebEngineCore ".\src\Application.py"
```

```bash
uv run -m nuitka --output-filename="Asana Gantt Exporter" --windows-icon-from-ico=".\logos\Asana Gantt Exporter 3-2.ico" --mingw64 --standalone --onefile --enable-plugin=pyside6 --include-package=plotly --include-package=_plotly_utils --include-package-data=plotly --include-package=kaleido --include-package-data=kaleido --nofollow-import-to=pytest --windows-console-mode=disable .\src\Application.py
```

Notes when packaging GUI + Qt WebEngine:
- PySide6 Qt WebEngine needs additional Qt resources; you may need to include the QtWebEngineProcess and library files using `--add-data` options.
