import math
import pandas as pd
import plotly.express as px
from PySide6.QtWidgets import QFileDialog, QMessageBox


class GanttRenderer:
    def __init__(self):
        self.current_df = None
        self.current_fig = None
        self.task_count = 0

    def render(self, df: pd.DataFrame, timescale_config: tuple, color_column: str = None):
        """
        Renders the Gantt chart and applies the selected timescale.
        time_scale: Plotly dtick format (e.g., 'D1', 'D7', 'M1')
        """
        timescale, time_format = timescale_config

        if df.empty:
            return None
        self.current_df = df
        self.task_count = len(df)

        fig = px.timeline(
            df.sort_values("StartDate"),
            x_start="StartDate",
            x_end="EndDate",
            y="TaskName",
            color=color_column,  # Ensure this column exists in your CSV
            hover_data=df.columns,
            labels=dict(TaskName="Taak")
        )

        fig.update_yaxes(autorange="reversed")
        fig.update_xaxes(
            type='date',
            dtick=timescale,
            tickformat=time_format,
            tickson="boundaries",
            # ticklabelmode="period",
            tickmode='linear',
            showgrid=True
        )
        fig.update_layout(
            height=650,
            margin=dict(l=10, r=10, t=30, b=10),
            xaxis_title="Datum",
            xaxis={'side': 'top'},
            yaxis_title="Taken"
        )

        self.current_fig = fig
        return fig

    def _calculate_export_dimensions(self):
        """Calculates width based on date range and height based on task count."""
        if self.current_df is None:
            return 1920, 1080

        # Calculate days in range
        delta = self.current_df["EndDate"].max() - self.current_df["StartDate"].min()
        days = max(delta.days, 30)

        # Width: roughly 40 pixels per day for readability, min 1920
        width = max(1920, days * 20)
        # Height: 35 pixels per task + margins
        height = max(800, (self.task_count * 20) + 200)

        return width, height

    def export(self, parent_widget, fmt: str):
        """
        Handles exporting the current figure to various formats.
        """
        if not self.current_fig:
            QMessageBox.warning(parent_widget, "Export", "Er is geen chart om te exporteren.")
            return

        width, height = self._calculate_export_dimensions()
        filters = {
            'html': "HTML (*.html)",
            'pdf': "PDF (*.pdf)",
            'png': "PNG (*.png)"
        }

        path, _ = QFileDialog.getSaveFileName(
            parent_widget,
            "Export Gantt Chart",
            f"gantt_export.{fmt}",
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