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

class GanttApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Asana Gantt Viewer")
        self.resize(1280, 720)

        self.df = None
        self.current_fig = None

        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)

        # LEFT CONTROL PANEL
        controls = QWidget()
        cl = QVBoxLayout(controls)

        # Load
        btn = QPushButton("Load Asana CSV")
        btn.clicked.connect(self.load_csv)
        cl.addWidget(btn)

        # Date filters
        cl.addWidget(QLabel("Start Date ≥"))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.setDate(QDate.currentDate().addMonths(-3))
        cl.addWidget(self.start_date)

        cl.addWidget(QLabel("Due Date ≤"))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.setDate(QDate.currentDate().addMonths(6))
        cl.addWidget(self.end_date)

        # Assignee
        cl.addWidget(QLabel("Assignee(s):"))
        self.assignee_list = QListWidget()
        self.assignee_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        cl.addWidget(self.assignee_list)

        # Floors
        cl.addWidget(QLabel("Verdiep (+00, +01, ...):"))


        self.floor_search = QLineEdit()
        self.floor_search.setPlaceholderText("Search verdiep...")
        self.floor_search.textChanged.connect(
            lambda text: self.filter_list(self.floor_list, text)
        )
        cl.addWidget(self.floor_search)

        self.floor_list = QListWidget()
        self.floor_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        cl.addWidget(self.floor_list)

        btn_all_floors = QPushButton("Selecteer Alles")
        btn_all_floors.clicked.connect(
            lambda: self.select_all_items(self.floor_search)
        )
        cl.addWidget(btn_all_floors)

        # Onderaannemers filter
        cl.addWidget(QLabel("Onderaannemers:"))
        self.oa_search = QLineEdit()
        self.oa_search.setPlaceholderText("Search O.A. values...")
        self.oa_search.textChanged.connect(
            lambda text: self.filter_list(self.oa_list, text)
        )
        cl.addWidget(self.oa_search)

        self.oa_list = QListWidget()
        self.oa_list.setSelectionMode(QListWidget.MultiSelection)
        cl.addWidget(self.oa_list)

        btn_oa_all = QPushButton("Selecteer Alles")
        btn_oa_all.clicked.connect(
            lambda: self.select_all_items(self.oa_list)
        )
        cl.addWidget(btn_oa_all)

        # Apply
        self.apply_btn = QPushButton("Apply Filters & Render")
        self.apply_btn.clicked.connect(self.apply_filters)
        self.apply_btn.setEnabled(False)
        cl.addWidget(self.apply_btn)

        # Export
        self.export_png = QPushButton("Export PNG")
        self.export_pdf = QPushButton("Export PDF")
        self.export_html = QPushButton("Export HTML")
        self.export_png.setEnabled(False)
        self.export_pdf.setEnabled(False)
        self.export_html.setEnabled(False)
        cl.addWidget(self.export_png)
        cl.addWidget(self.export_pdf)
        cl.addWidget(self.export_html)

        self.export_png.clicked.connect(lambda: self.export_chart("png"))
        self.export_pdf.clicked.connect(lambda: self.export_chart("pdf"))
        self.export_html.clicked.connect(lambda: self.export_chart("html"))

        cl.addStretch()

        # RIGHT VIEWER
        self.web = QWebEngineView()

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(controls)
        splitter.addWidget(self.web)
        splitter.setStretchFactor(1, 3)

        layout.addWidget(splitter)

    def load_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Asana CSV", os.getcwd(), "CSV (*.csv)")
        if not path:
            return
        try:
            df = pd.read_csv(path)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        # Normalize Asana columns
        rename_map = {
            'Task Id': 'TaskId',
            'Name': 'Task',
            'Start Date': 'Start',
            'Due Date': 'End',
            'Notes': 'Notes_orig',
            'Opmerkingen': 'Notes_extra'
        }
        for k, v in rename_map.items():
            if k in df.columns:
                df = df.rename(columns={k: v})

        # Merge Notes
        df['Notes'] = df.get('Notes_orig', '').astype(str) + " " + df.get('Notes_extra', '').astype(str)

        # Parse dates
        for c in ['Start', 'End']:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors='coerce')

        df = df.dropna(subset=['Start', 'End'])

        # Extract filters
        self.populate_filter(self.assignee_list, df, 'Assignee Email')

        # Verdiep detection from custom fields: find columns containing "+"
        floor_cols = [c for c in df.columns if df[c].astype(str).str.contains("\\+").any()]
        floors = df.columns["Verdiep"]
        if floor_cols:
            vc = floor_cols[0]
            self.populate_filter(self.floor_list, df, vc)
        self.floor_col = floor_cols[0] if floor_cols else None

        # OA detection
        onderaannemer_cols = [c for c in df.columns if "O.A" in c or "OA" in c]
        if onderaannemer_cols:
            oc = onderaannemer_cols[0]
            self.populate_filter(self.oa_list, df, oc)
        self.onderaannemer_col = onderaannemer_cols[0] if onderaannemer_cols else None

        self.df = df
        self.apply_btn.setEnabled(True)
        QMessageBox.information(self, "Loaded", f"Loaded {len(df)} Asana tasks.")

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
        df = df[(df['Start'] >= pd.Timestamp(s)) & (df['End'] <= pd.Timestamp(e))]

        sel_assignee = [i.text() for i in self.assignee_list.selectedItems()]
        if sel_assignee:
            df = df[df['Assignee Email'].astype(str).isin(sel_assignee)]

        if self.floor_col:
            sel_v = [i.text() for i in self.floor_list.selectedItems()]
            if sel_v:
                df = df[df[self.floor_col].astype(str).isin(sel_v)]

        if self.onderaannemer_col:
            sel_o = [i.text() for i in self.oa_list.selectedItems()]
            if sel_o:
                df = df[df[self.onderaannemer_col].astype(str).isin(sel_o)]

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
                df.sort_values('Start'),
                x_start='Start', x_end='End',
                y='Task',
                color='Assignee Email',
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
