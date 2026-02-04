import sys
import os
from pathlib import Path

from PySide6.QtCore import Qt, QStandardPaths
from PySide6.QtWidgets import (QApplication, QMainWindow, QFileDialog,
                               QPushButton, QSplitter, QHBoxLayout, QVBoxLayout,
                               QWidget, QMessageBox, QLabel, QFrame, QSpacerItem, QSizePolicy, QSpinBox, QGridLayout
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
        main_layout.setContentsMargins(0, 0, 0, 0)  # Clean edges
        main_layout.setSpacing(0)

        # ---- Left panel ----
        self.control_panel = QWidget()
        control_panel_layout = QHBoxLayout(self.control_panel)
        control_panel_layout.setContentsMargins(0, 0, 0, 0)
        control_panel_layout.setSpacing(0)

        self.content = QWidget()
        content_layout = QVBoxLayout(self.content)

        # Load
        load_btn = QPushButton("Laad CSV")
        load_btn.clicked.connect(self.load_csv)
        load_btn.setMinimumHeight(40)
        load_btn.setStyleSheet("font-weight: bold;")

        content_layout.addWidget(load_btn)
        content_layout.addWidget(create_hline())

        # Filter
        content_layout.addWidget(self.filters, 1)

        # self.apply_btn = QPushButton("Pas filters toe en creeer een gantt chart")
        # self.apply_btn.clicked.connect(self.apply)
        # self.apply_btn.setMinimumHeight(40)
        # self.apply_btn.setStyleSheet("font-weight: bold;")
        # self.apply_btn.setEnabled(False)
        # content_layout.addWidget(self.apply_btn)

        # --- Create ---
        settings_group = QWidget()
        settings_layout = QHBoxLayout(settings_group)
        settings_layout.setContentsMargins(0, 5, 0, 5)
        settings_layout.setSpacing(5)

        inputs_widget = QWidget()
        inputs_grid = QGridLayout(inputs_widget)
        inputs_grid.setContentsMargins(0, 0, 0, 0)
        inputs_grid.setSpacing(2)

        # Row Height
        lbl_height = QLabel("↕")
        lbl_height.setStyleSheet("QLabel {font-size: 20px;}")
        lbl_height.setToolTip("Taak Hoogte (pixels)")
        inputs_grid.addWidget(lbl_height, 0, 0)

        self.row_height = QSpinBox()
        self.row_height.setRange(25, 100)
        self.row_height.setValue(25)
        self.row_height.setFixedWidth(60)
        self.row_height.setToolTip("Pas de hoogte van taken aan")
        inputs_grid.addWidget(self.row_height, 0, 1)

        # Column Width
        lbl_width = QLabel("↔")
        lbl_width.setStyleSheet("QLabel {font-size: 20px;}")
        lbl_width.setToolTip("Kolom Breedte (pixels)")
        inputs_grid.addWidget(lbl_width, 1, 0)

        self.col_width = QSpinBox()
        self.col_width.setRange(10, 300)
        self.col_width.setValue(14)
        self.col_width.setFixedWidth(60)
        self.col_width.setToolTip("Pas de breedte van tijdsblokken aan")
        inputs_grid.addWidget(self.col_width, 1, 1)

        settings_layout.addWidget(inputs_widget)

        # Generate
        self.apply_btn = QPushButton("Update")
        self.apply_btn.clicked.connect(self.apply)
        self.apply_btn.setStyleSheet("font-weight: bold;")
        self.apply_btn.setToolTip("Genereer of ververs de Gantt chart")
        self.apply_btn.setEnabled(False)

        self.apply_btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)

        settings_layout.addWidget(self.apply_btn, 1)

        content_layout.addWidget(settings_group)

        content_layout.addWidget(create_hline())

        # Export
        content_layout.addWidget(QLabel("Exporteer de Gantt Chart naar:"))
        export_layout = QHBoxLayout()
        for fmt in ['png', 'pdf', 'html']:
            btn = QPushButton(fmt.upper())
            btn.clicked.connect(lambda checked=False, f=fmt: self.renderer.export(self, f))
            export_layout.addWidget(btn)

        content_layout.addLayout(export_layout)

        # --- Toggle Button ---
        self.toggle_btn = QPushButton("<")
        self.toggle_btn.setFixedWidth(15)  # Thin strip
        self.toggle_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)  # Full height
        self.toggle_btn.setToolTip("Verberg/Toon Filters")
        self.toggle_btn.clicked.connect(self.toggle_sidebar)

        control_panel_layout.addWidget(self.content)
        control_panel_layout.addWidget(self.toggle_btn)

        # ---- Right panel ----
        self.web = QWebEngineView()

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.control_panel)
        self.splitter.addWidget(self.web)
        self.splitter.setStretchFactor(1, 3)
        self.saved_splitter_state = self.splitter.saveState()

        main_layout.addWidget(self.splitter)

    def toggle_sidebar(self):
        if self.content.isVisible():
            self.content.hide()
            self.toggle_btn.setText(">")
            self.splitter.setSizes([15, 10000])
        else:
            self.content.show()
            self.toggle_btn.setText("<")
            self.splitter.restoreState(self.saved_splitter_state)

    def load_csv(self):
        downloads_path = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)

        if not downloads_path:
            downloads_path = QStandardPaths.writableLocation(QStandardPaths.HomeLocation)

        path, _ = QFileDialog.getOpenFileName(self, "CSV", downloads_path, "*.csv")

        if not path:
            return
        self.web.setHtml("")
        df = self.data.load_csv(path)
        self.filters.build_from_df(df)

        self.apply_btn.setEnabled(True)

    def apply(self):
        df = self.data.df.copy()
        df = self.filters.apply_filters(df)

        if df.empty:
            return
        scale = self.filters.get_scale_config()
        color_col = self.filters.get_color_column()
        r_height = self.row_height.value()
        c_width = self.col_width.value()

        show_dates = self.filters.get_show_dates()
        date_fmt = self.filters.get_date_format()

        fig = self.renderer.render(df, scale, r_height, c_width, show_dates, date_fmt, color_col)
        self.web.setHtml(fig.to_html(include_plotlyjs="cdn"))


if __name__ == '__main__':
    app = QApplication(sys.argv)

    window = GanttApp()
    window.show()
    sys.exit(app.exec())