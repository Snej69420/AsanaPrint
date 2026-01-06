"""
Simple Gantt Chart Viewer
- Load CSV (expects Start/End columns parseable by pandas)
- Filter by date range and Project Manager
- Render interactive Plotly Gantt inside a PySide6 QWebEngineView
- Export to PNG / PDF (via plotly + kaleido) and HTML

Single-file prototype. For production, split into modules.
"""

import sys
import os
import json
from math import floor
from pathlib import Path

import pandas as pd
import plotly.express as px

from PySide6.QtCore import Qt, QDate, QUrl
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QLabel, QListWidget, QListWidgetItem,
    QAbstractItemView, QDateEdit, QMessageBox, QSplitter, QLineEdit,
    QComboBox, QInputDialog, QToolButton
)
from PySide6.QtWebEngineWidgets import QWebEngineView

# Normalize Asana columns
ASANA_MAPPING = {
    'Task ID': 'TaskID',
    'Name': 'TaskName',
    'Start Date': 'StartDate',
    'Due Date': 'EndDate',
    'Created At': 'Created',
    'Completed At': 'Completed',
}
IGNORE = ("TaskID", "TaskName", "StartDate", "EndDate", "Created",
          "Completed", "Last Modified", "Assignee Email", "Tags", "Parent task",
          "Blocked By (Dependencies)", "Blocking (Dependencies)", )

GENERAL_LABEL = "— General —"
PROJECT_DIR = Path(__file__).resolve().parent.parent
PRESET_FILE = PROJECT_DIR / "presets.json"


# TODO separate the class into subclasses (clean up)
# TODO add fixed scales week/month
# TODO add a selector to determine which property will determine the colour in the gantt chart
class GanttApp(QMainWindow):
    def load_file(self, cl):
        btn = QPushButton("Selecteer een Asana CSV")
        btn.clicked.connect(self.load_csv)
        cl.addWidget(btn)

    def date_selector(self, cl):
        cl.addWidget(QLabel("Start Datum ≥"))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("dd-MM-yyyy")
        self.start_date.setDate(QDate.currentDate().addMonths(-3))
        cl.addWidget(self.start_date)

        cl.addWidget(QLabel("Eind Datum ≤"))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("dd-MM-yyyy")
        self.end_date.setDate(QDate.currentDate().addMonths(6))
        cl.addWidget(self.end_date)

    def add_selector_item(self, name):
        item = QListWidgetItem(name)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Unchecked)
        self.filter_selector.addItem(item)

    def add_search(self, layout, name):
        search_field = QLineEdit()
        search_field.setPlaceholderText(f"Zoek een {name}")
        search_field.textChanged.connect(
            lambda text: self.filter_list(self.optionsList[name], text)
        )
        layout.addWidget(search_field)

    def add_select_all(self, layout, name):
        select_all_button = QPushButton("Selecteer Alles")
        select_all_button.clicked.connect(
            lambda: self.select_all_items(self.optionsList[name])
        )
        layout.addWidget(select_all_button)

    def add_selector(self, name:str, search:bool = False, select_all:bool = False):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel(f"{name}:"))
        search_select = QHBoxLayout()
        if search:
            self.add_search(search_select, name)

        if select_all:
            self.add_select_all(search_select, name)
        layout.addLayout(search_select)

        self.optionsList[name] = QListWidget()
        self.optionsList[name].setSelectionMode(QAbstractItemView.ExtendedSelection)
        layout.addWidget(self.optionsList[name])

        self.populate(name)

        self.selector_widgets[name] = container
        container.setVisible(False)
        self.selectors.addWidget(container)

    def apply_preset(self, name):
        preset = self.presets.get(name)
        if not preset:
            return

        # Show/hide filters
        for k, w in self.selector_widgets.items():
            w.setVisible(k in preset["filters"])

    def load_presets(self):
        if PRESET_FILE.exists():
            with open(PRESET_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_presets(self):
        with open(PRESET_FILE, "w", encoding="utf-8") as f:
            json.dump(self.presets, f)

    def save_current_as_preset(self, name):
        filters = [k for k, w in self.selector_widgets.items() if w.isVisible()]
        if not filters:
            QMessageBox.warning(
                self, "Preset leeg",
                "Geen actieve filters om op te slaan."
            )
            return

        preset = {"filters": filters}

        self.presets[name] = preset
        self.save_presets()
        self.refresh_preset_combo()
        self.preset_combo.setCurrentText(name)

    def prompt_save_preset(self):
        name, ok = QInputDialog.getText(
            self, "Preset opslaan", "Naam van preset:"
        )
        if ok and name:
            self.save_current_as_preset(name)

    def refresh_preset_combo(self):
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItem("— Kies preset —")

        for name in sorted(self.presets.keys()):
            self.preset_combo.addItem(name)

        self.preset_combo.blockSignals(False)

    def toggle_filter_selector(self):
        open = self.toggle_filters_btn.isChecked()
        self.filter_selector_widget.setVisible(open)
        self.toggle_filters_btn.setArrowType(
            Qt.DownArrow if open else Qt.RightArrow
        )

    def update_active_filters(self):
        for i in range(self.filter_selector.count()):
            item = self.filter_selector.item(i)
            name = item.text()
            print(f"Name: {name}")

            if name in self.selector_widgets.keys():
                print(f"Name: {name}")
                print(f"Checked: {item.checkState()}")
                self.selector_widgets[name].setVisible(
                    item.checkState() == Qt.Checked
                )

    def apply(self, cl):
        self.apply_btn = QPushButton("Pas filters toe en creeer een gantt chart")
        self.apply_btn.clicked.connect(self.apply_filters)
        self.apply_btn.setEnabled(False)
        cl.addWidget(self.apply_btn)

    def export(self, cl):
        self.export_png = QPushButton("Export naar PNG")
        self.export_pdf = QPushButton("Export naar PDF")
        self.export_html = QPushButton("Export naar HTML")
        self.export_png.setEnabled(False)
        self.export_pdf.setEnabled(False)
        self.export_html.setEnabled(False)
        cl.addWidget(self.export_png)
        cl.addWidget(self.export_pdf)
        cl.addWidget(self.export_html)

        self.export_png.clicked.connect(lambda: self.export_chart("png"))
        self.export_pdf.clicked.connect(lambda: self.export_chart("pdf"))
        self.export_html.clicked.connect(lambda: self.export_chart("html"))

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Asana Gantt Viewer")
        self.resize(1280, 720)

        self.optionsList = {}
        self.df = None
        self.current_fig = None

        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)

        # LEFT CONTROL PANEL
        controls = QWidget()
        cl = QVBoxLayout(controls)

        # Load
        self.load_file(cl)
        self.date_selector(cl)

        # selectors
        self.filter_selector = QListWidget()
        self.filter_selector.setSelectionMode(QAbstractItemView.NoSelection)
        self.filter_selector.itemChanged.connect(self.update_active_filters)
        cl.addWidget(QLabel("Beschikbare filters:"))
        cl.addWidget(self.filter_selector)

        # presets
        self.presets = self.load_presets()
        preset_row = QHBoxLayout()
        self.preset_combo = QComboBox()
        self.preset_combo.addItem("— Kies preset —")
        self.preset_combo.currentTextChanged.connect(self.apply_preset)

        btn_save = QPushButton("Opslaan")
        btn_save.clicked.connect(self.prompt_save_preset)

        preset_row.addWidget(self.preset_combo)
        preset_row.addWidget(btn_save)
        self.refresh_preset_combo()

        cl.addLayout(preset_row)

        # PLACEHOLDER for dynamic selectors
        self.selectors = QVBoxLayout()
        self.selector_widgets = {}
        cl.addLayout(self.selectors)

        self.apply(cl)
        self.export(cl)

        cl.addStretch()

        # RIGHT VIEWER
        self.web = QWebEngineView()

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(controls)
        splitter.addWidget(self.web)
        splitter.setStretchFactor(1, 3)

        layout.addWidget(splitter)

    def clean(self, df):
        for k, v in ASANA_MAPPING.items():
            if k in df.columns:
                df = df.rename(columns={k: v})
        # Merge Notes
        df['Notes'] = df.get('Notes', '').astype(str) + " " + df.get('Opmerkingen', '').astype(str)
        df.drop(columns=['Notes', 'Opmerkingen'], inplace=True)

        return df

    def populate(self, name):
        if not name or name not in self.df.columns:
            return

        options = self.optionsList[name]
        options.clear()

        values = sorted(self.df[name].dropna().astype(str).unique()) # is dropping empty values smart??
        for v in values:
            options.addItem(v)

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())

    def build_dynamic_selectors(self, df):
        # Clear previous selectors
        self.clear_layout(self.selectors)
        self.optionsList.clear()

        for title in list(df):
            if title in IGNORE:
                continue
            self.add_selector_item(title)
            self.add_selector(title, True, True)

    def load_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Asana CSV", os.getcwd(), "CSV (*.csv)")
        if not path:
            return
        try:
            df = pd.read_csv(path)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        df = self.clean(df)

        # Parse dates
        for c in ['StartDate', 'EndDate']:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors='coerce')

        df = df.dropna(subset=['StartDate', 'EndDate'])
        self.df = df

        self.build_dynamic_selectors(df)

        # Extract filters
        # self.populate_filter(self.assignee_list, df, 'Assignee Email')
        #
        # self.populate_floor_filter(df)
        # self.populate_subcontractor_filter(df)

        self.apply_btn.setEnabled(True)
        QMessageBox.information(self, "Taken gevonden", f"{len(df)} Asana taken geladen.")
        current = self.preset_combo.currentText()
        if current in self.presets:
            self.apply_preset(current)

    def populate_filter(self, widget, df, col):
        if col not in df.columns:
            return
        widget.clear()
        vals = sorted(df[col].dropna().astype(str).unique())
        for v in vals:
            widget.addItem(v)

    def filter_list(self, list_widget, text: str):
        text = text.lower()
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            item.setHidden(text not in item.text().lower())

    def select_all_items(self, list_widget):
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if not item.isHidden():
                item.setSelected(True)


    # ------------------ Apply filters ------------------
    def apply_filters(self):
        if self.df is None:
            return

        df = self.df.copy()

        # ---------------- Date filter (still special, global) ----------------
        s = self.start_date.date().toPython()
        e = self.end_date.date().toPython()

        df = df[
            (df["StartDate"] >= pd.Timestamp(s)) &
            (df["EndDate"] <= pd.Timestamp(e))
            ]

        # ---------------- Dynamic selectors ----------------
        for filter_name, list_widget in self.optionsList.items():

            # Skip hidden selectors
            widget = self.selector_widgets.get(filter_name)
            if widget and not widget.isVisible():
                continue
            if widget.isVisible():
                print(f"{filter_name} filter is visible.")

            selected_values = [i.text() for i in list_widget.selectedItems()]
            if not selected_values:
                continue

            # Resolve dataframe column
            column = ASANA_MAPPING.get(filter_name, filter_name)
            if column not in df.columns:
                continue

            series = df[column].astype(str).str.strip()

            # ---- Special case: Verdiep / Floor ----
            if filter_name == "Verdiep":
                mask = pd.Series(False, index=df.index)

                real_values = [v for v in selected_values if v != GENERAL_LABEL]
                if real_values:
                    mask |= series.isin(real_values)

                if GENERAL_LABEL in selected_values:
                    mask |= series.isna() | series.isin(["", "nan", "None"])

                df = df[mask]

            # ---- Default categorical filter ----
            else:
                df = df[series.isin(selected_values)]

        # ---------------- Result ----------------
        if df.empty:
            QMessageBox.warning(self, "Geen data", "Geen taken voldoen aan de filters.")
            return
        print(df.keys())

        self.render_gantt(df)
        self.export_png.setEnabled(True)
        self.export_pdf.setEnabled(True)
        self.export_html.setEnabled(True)

    # ------------------ Render Gantt ------------------
    def render_gantt(self, df):
        try:
            fig = px.timeline(
                df.sort_values('StartDate'),
                x_start='StartDate', x_end='EndDate',
                y='TaskName',
                color='O.A. Kristof CU',
                labels=dict(TaskName="Taak", Subcontractor="Onderaannemer"),
                hover_data=df.columns
            )
            fig.update_yaxes(autorange='reversed')
            fig.update_layout(height=650)
            self.current_fig = fig
            self.web.setHtml(fig.to_html(include_plotlyjs='cdn'))
        except Exception as e:
            QMessageBox.critical(self, "Render Error", str(e))

    # ------------------ Export ------------------
    def export_chart(self, fmt):
        if not self.current_fig:
            return
        filt = "HTML (*.html)" if fmt=='html' else ("PDF (*.pdf)" if fmt=='pdf' else "PNG (*.png)")
        path, _ = QFileDialog.getSaveFileName(self, "Export", f"gantt.{fmt}", filt)
        if not path:
            return
        try:
            if fmt == 'html':
                self.current_fig.write_html(path)
            else:
                self.current_fig.write_image(path)
            QMessageBox.information(self, "Exported", f"Saved to {path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # On some platforms, QWebEngine requires this import side-effect
    # If you get errors related to Qt WebEngine, ensure PySide6[webengine] is installed.

    window = GanttApp()
    window.show()
    sys.exit(app.exec())
