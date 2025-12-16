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
from math import floor
from pathlib import Path
import tempfile

import pandas as pd
import plotly.express as px

from PySide6.QtCore import Qt, QDate, QUrl
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QLabel, QListWidget, QAbstractItemView,
    QDateEdit, QMessageBox, QSplitter, QLineEdit,
)
from PySide6.QtWebEngineWidgets import QWebEngineView

# Normalize Asana columns
ASANA_MAPPING = {
    'Task Id': 'TaskId',
    'Name': 'TaskName',
    'Start Date': 'StartDate',
    'Due Date': 'EndDate',
    'Created At': 'Created',
    'Completed At': 'Completed',
}
IGNORE = ("TaskID", "TaskName", "StartDate", "EndDate", "Created", "Completed")
FLOOR_COLUMN = "Verdiep"
SUBCONTRACTOR = "O.A."

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

    def assigned(self, cl):
        cl.addWidget(QLabel("Verantwoordelijke:"))
        self.assignee_list = QListWidget()
        self.assignee_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        cl.addWidget(self.assignee_list)

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
        self.selectors.addWidget(QLabel(f"{name}:"))
        search_select = QHBoxLayout()
        if search:
            self.add_search(search_select, name)

        if select_all:
            self.add_select_all(search_select, name)
        self.selectors.addLayout(search_select)

        self.optionsList[name] = QListWidget()
        self.optionsList[name].setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.selectors.addWidget(self.optionsList[name])

        self.populate(name)

    def floor_selector(self, cl):
        cl.addWidget(QLabel("Verdieping:"))
        search_select = QHBoxLayout()
        floor_search = QLineEdit()
        floor_search.setPlaceholderText("Zoek een verdieping")
        floor_search.textChanged.connect(
            lambda text: self.filter_list(self.floor_list, text)
        )
        search_select.addWidget(floor_search)

        btn_all_floors = QPushButton("Selecteer Alles")
        btn_all_floors.clicked.connect(
            lambda: self.select_all_items(self.floor_list)
        )
        search_select.addWidget(btn_all_floors)
        cl.addLayout(search_select)

        self.floor_list = QListWidget()
        self.floor_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        cl.addWidget(self.floor_list)

    def subcontractor_selector(self, cl):
        cl.addWidget(QLabel("Onderaannemers:"))

        search_select = QHBoxLayout()
        self.oa_search = QLineEdit()
        self.oa_search.setPlaceholderText("Zoek een onderaannemer")
        self.oa_search.textChanged.connect(
            lambda text: self.filter_list(self.subcontractor_list, text)
        )
        search_select.addWidget(self.oa_search)
        btn_oa_all = QPushButton("Selecteer Alles")
        btn_oa_all.clicked.connect(
            lambda: self.select_all_items(self.subcontractor_list)
        )
        search_select.addWidget(btn_oa_all)
        cl.addLayout(search_select)

        self.subcontractor_list = QListWidget()
        self.subcontractor_list.setSelectionMode(QListWidget.MultiSelection)
        cl.addWidget(self.subcontractor_list)

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
        # PLACEHOLDER for dynamic selectors
        self.selectors = QVBoxLayout()
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
        print(list(df))
        for k, v in ASANA_MAPPING.items():
            if k in df.columns:
                df = df.rename(columns={k: v})
        # Merge Notes
        df['Notes'] = df.get('Notes', '').astype(str) + " " + df.get('Opmerkingen', '').astype(str)

        return df

    def populate(self, name):
        if not name or name not in self.df.columns:
            return

        options = self.optionsList[name]
        options.clear()

        values = sorted(self.df[name].dropna().astype(str).unique()) # is dropping empty values smart??
        for v in values:
            options.addItem(v)

    def populate_floor_filter(self, df):
        self.floor_list.clear()

        if FLOOR_COLUMN not in df.columns:
            return

        # Normalize column
        col = df[FLOOR_COLUMN].astype(str).str.strip()

        # True floor values (exclude empty / nan)
        floor_values = sorted(
            v for v in col.unique()
            if v and v.lower() not in ("nan", "none")
        )

        # Add special option for tasks without a floor
        self.floor_list.addItem("— General —")

        for v in floor_values:
            self.floor_list.addItem(v)

    def populate_subcontractor_filter(self, df):
        subcontractor_cols = [c for c in df.columns if SUBCONTRACTOR in c]
        if subcontractor_cols:
            oc = subcontractor_cols[0]
            self.populate_filter(self.subcontractor_list, df, oc)

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
            print(f"Title: {title}")
            if title in IGNORE:
                continue
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
        print(list(df))

        # Parse dates
        for c in ['StartDate', 'EndDate']:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors='coerce')

        df = df.dropna(subset=['StartDate', 'EndDate'])

        # Extract filters
        self.populate_filter(self.assignee_list, df, 'Assignee Email')

        self.populate_floor_filter(df)
        self.populate_subcontractor_filter(df)

        self.df = df
        self.apply_btn.setEnabled(True)
        QMessageBox.information(self, "Taken gevonden", f"{len(df)} Asana taken geladen.")

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
        df = self.df.copy()

        s = self.start_date.date().toPython()
        e = self.end_date.date().toPython()
        df = df[(df['StartDate'] >= pd.Timestamp(s)) & (df['EndDate'] <= pd.Timestamp(e))]

        sel_assignee = [i.text() for i in self.assignee_list.selectedItems()]
        if sel_assignee:
            df = df[df['Assignee Email'].astype(str).isin(sel_assignee)]

        selected_floor = [i.text() for i in self.floor_list.selectedItems()]
        if selected_floor:
            floor_series = df[FLOOR_COLUMN].astype(str).str.strip()

            mask = pd.Series(False, index=df.index)

            # Normal floor values
            real_values = [v for v in selected_floor if v != "— General —"]
            if real_values:
                mask |= floor_series.isin(real_values)

            # Tasks without floor
            if "— General —" in selected_floor:
                mask |= floor_series.isin(["", "nan", "None"]) | floor_series.isna()

            df = df[mask]

        if SUBCONTRACTOR:
            selectedSC = [i.text() for i in self.subcontractor_list.selectedItems()]
            print(f"subcontractors: {selectedSC}")
            if selectedSC:
                df = df[df[SUBCONTRACTOR].astype(str).isin(selectedSC)]

        if df.empty:
            QMessageBox.warning(self, "No Data", "No tasks match filters.")
            return

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
