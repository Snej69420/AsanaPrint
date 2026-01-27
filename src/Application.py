import sys
import os
from pathlib import Path

from PySide6.QtCore import Qt, QStandardPaths
from PySide6.QtWidgets import (QApplication, QMainWindow, QFileDialog,
                               QPushButton, QSplitter, QHBoxLayout, QVBoxLayout,
                               QWidget, QMessageBox, QLabel, QFrame, QSpacerItem, QSizePolicy
                               )
from PySide6.QtWebEngineWidgets import QWebEngineView

from DataHandler import DataModel
from Filter import FilterPanel
from Renderer import GanttRenderer


def create_hline():
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Sunken)
    return line

class GanttApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Asana Gantt Viewer")
        self.resize(1920, 1080)

        self.data = DataModel()
        self.filters = FilterPanel()
        self.renderer = GanttRenderer()

        # -------- UI --------
        root = QWidget()
        self.setCentralWidget(root)

        main_layout = QHBoxLayout(root)

        # ---- Left panel ----
        left = QWidget()
        left_layout = QVBoxLayout(left)

        load_btn = QPushButton("Laad CSV")
        load_btn.clicked.connect(self.load_csv)
        load_btn.setMinimumHeight(40)
        load_btn.setStyleSheet("font-weight: bold;")

        left_layout.addWidget(load_btn)
        left_layout.addWidget(create_hline())

        left_layout.addWidget(self.filters, 1)

        self.apply_btn = QPushButton("Pas filters toe en creeer een gantt chart")
        self.apply_btn.clicked.connect(self.apply)
        self.apply_btn.setMinimumHeight(40)
        self.apply_btn.setStyleSheet("font-weight: bold;")
        self.apply_btn.setEnabled(False)
        left_layout.addWidget(self.apply_btn)

        left_layout.addWidget(create_hline())

        left_layout.addWidget(QLabel("Exporteer de Gantt Chart naar:"))
        export_layout = QHBoxLayout()
        for fmt in ['png', 'pdf', 'html']:
            btn = QPushButton(fmt.upper())
            btn.clicked.connect(lambda checked=False, f=fmt: self.renderer.export(self, f))
            export_layout.addWidget(btn)

        left_layout.addLayout(export_layout)

        # ---- Right panel ----
        self.web = QWebEngineView()

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(self.web)
        splitter.setStretchFactor(1, 3)

        main_layout.addWidget(splitter)

    def load_csv(self):
        downloads_path = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)

        if not downloads_path:
            downloads_path = QStandardPaths.writableLocation(QStandardPaths.HomeLocation)

        path, _ = QFileDialog.getOpenFileName(self, "CSV", downloads_path, "*.csv")

        if not path:
            return

        df = self.data.load_csv(path)
        self.filters.build_from_df(df)

        self.apply_btn.setEnabled(True)

    def apply(self):
        df = self.data.df.copy()
        df = self.filters.apply_filters(df)
        scale = self.filters.get_scale_config()

        if df.empty:
            return
        color_col = self.filters.get_color_column()

        fig = self.renderer.render(df, scale, color_col)
        self.web.setHtml(fig.to_html(include_plotlyjs="cdn"))


if __name__ == '__main__':
    app = QApplication(sys.argv)

    window = GanttApp()
    window.show()
    sys.exit(app.exec())