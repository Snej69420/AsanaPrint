# Gantt Chart Viewer (PySide6 + Plotly)

This repository contains a single-file prototype `main.py` that:
- loads a CSV,
- allows filtering by start/end date and project manager,
- renders an interactive Gantt chart using Plotly inside a PySide6 QWebEngineView,
- exports the chart to PNG, PDF (requires `kaleido`), or HTML.

## Future Work:
- Config enable setting default file paths for saving and loading

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
uv pip install pyinstaller
pyinstaller --onefile --windowed main.py
```

Notes when packaging GUI + Qt WebEngine:
- PySide6 Qt WebEngine needs additional Qt resources; you may need to include the QtWebEngineProcess and library files using `--add-data` options.
## Troubleshooting

- If export to PNG/PDF fails, ensure `kaleido` is installed (`uv pip install kaleido`).
- If the QWebEngineView fails to initialize, ensure PySide6 was installed with webengine support and your platform has the necessary Qt libraries.

