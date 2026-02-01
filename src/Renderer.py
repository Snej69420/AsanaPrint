import math
from unittest import case

import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QFileDialog, QMessageBox

DAY_IN_MS = 86400000
D7 = 7 * DAY_IN_MS

class GanttRenderer:
    def __init__(self):
        self.current_df = None
        self.current_fig = None
        self.task_count = 0
        self.row_height = 8
        self.col_width = 20
        self.timescale = "M1"
        self.time_format = "%b\n%Y"
        self.days_scale = 28

    def _timescale(self, raw_scale):
        key = raw_scale[0]
        self.timescale = key
        self.time_format = raw_scale[1]
        match key:
            case "D1":
                self.days_scale = 1
            case "D7":
                self.timescale = D7
                self.days_scale = 7
            case "M1":
                self.days_scale = 28
            case "M3":
                self.days_scale = 84
            case "M12":
                self.days_scale = 365

    def _calculate_dimensions(self):
        """Calculates width based on date range and height based on task count."""
        if self.current_df is None:
            return 1920, 1080

        interval = self.current_df["EndDate"].max() - self.current_df["StartDate"].min()
        width = interval.days * self.col_width
        height = self.task_count * self.row_height
        return width, height

    def render(self, df: pd.DataFrame, timescale_config: tuple, color_column: str = None, row_height: int = 8, col_width: int = 20):
        """
        Renders the Gantt chart and applies the selected timescale.
        time_scale: Plotly dtick format (e.g., 'D1', 'D7', 'M1')
        """
        if df.empty:
            return None
        self.current_df = df

        self.task_count = len(df)
        self.row_height = row_height
        self.col_width = col_width
        self._timescale(timescale_config)
        width, height = self._calculate_dimensions()



        fig = px.timeline(
            df.sort_values("StartDate"),
            x_start="StartDate",
            x_end="EndDate",
            y="TaskName",
            color=color_column,
            color_discrete_sequence=px.colors.qualitative.G10,
            hover_data=df.columns,
            labels=dict(TaskName="Taak")
        )

        fig.update_yaxes(autorange="reversed")
        fig.update_xaxes(
            type='date',
            dtick=self.timescale,
            tickformat=self.time_format,
            tickson="boundaries",
            tickmode='linear',
            showgrid=True,
        )
        fig.update_layout(
            width=width,
            height=height,
            margin=dict(l=10, r=10, t=30, b=10),
            xaxis_title="Datum",
            xaxis={'side': 'top'},
            yaxis_title="Taken"
        )

        self.current_fig = fig
        return fig

    def export(self, parent_widget, fmt: str):
        """
        Handles exporting the current figure to various formats.
        """
        if not self.current_fig:
            QMessageBox.warning(parent_widget, "Export", "Er is geen chart om te exporteren.")
            return

        width, height = self._calculate_dimensions()
        filters = {
            'html': "HTML (*.html)",
            'pdf': "PDF (*.pdf)",
            'png': "PNG (*.png)"
        }

        downloads_path = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)
        if not downloads_path:
            downloads_path = QStandardPaths.writableLocation(QStandardPaths.HomeLocation)

        default_filename = f"gantt_export.{fmt}"
        default_path = os.path.join(downloads_path, default_filename)

        path, _ = QFileDialog.getSaveFileName(
            parent_widget,
            "Export Gantt Chart",
            default_path,
            filters.get(fmt, "All Files (*)")
        )

        if not path:
            return

        try:
            if fmt == 'html':
                self.current_fig.write_html(path)
            elif fmt == 'png':
                self.current_fig.write_image(path, width=width, height=height, scale=2)
            elif fmt == 'pdf':
                self.current_fig.write_image(path, width=width, height=height)

            QMessageBox.information(parent_widget, "Succes", f"Bestand opgeslagen: {path}")
        except Exception as e:
            QMessageBox.critical(parent_widget, "Export Fout", f"Fout bij opslaan: {str(e)}")