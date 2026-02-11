import os
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QFileDialog, QMessageBox

LINE_COLOR = "#3b3b3b"

DAY_IN_MS = 86400000
D7 = 7 * DAY_IN_MS

class GanttRenderer:
    """
    Handles the generation and export of Gantt charts using Plotly.

    This class manages the state of the current chart, calculates dimensions based on
    time scales, and handles the actual drawing of bars and axes.
    """
    def __init__(self):
        """Initializes the renderer with default state values."""
        self.current_df = None
        self.current_fig = None
        self.task_count = 0
        self.row_height = 0
        self.col_width = 0
        self.timescale = "M1"
        self.time_format = "%b\n%Y" # for Gantt Chart
        self.days_scale = 0

        self.date_width = 0
        self.date_format = ""

    def _timescale(self, raw_scale):
        """
        Parses the timescale configuration tuple into Plotly-compatible formats.

        Args:
            raw_scale (tuple): A tuple containing (tick_interval, tick_format).
                               Example: ("M1", "%b\\n%Y")
        """
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

    def _date_width(self, fmt: str) -> int:
        """
        Calculates the required pixel width for date columns based on the format string.

        Args:
            fmt (str): The strftime format string (e.g., "%d-%b-%Y").

        Returns:
            int: The calculated width in pixels including padding.
        """
        width = 40  # Base padding

        # Day components
        if "%A" in fmt:
            width += 60  # Full Day Name (Monday)
        elif "%a" in fmt:
            width += 30  # Short Day Name (Mon)

        if "%d" in fmt: width += 20  # Day Number

        # Month components
        if "%B" in fmt:
            width += 60  # Full Month Name
        elif "%b" in fmt:
            width += 30  # Short Month Name
        elif "%m" in fmt:
            width += 20  # Month Number

        # Year components
        if "%Y" in fmt:
            width += 40  # Full Year
        elif "%y" in fmt:
            width += 20  # Short Year

        return width

    def _calculate_dimensions(self):
        """
        Calculates the total chart dimensions based on the data range and settings.

        Returns:
            tuple: (timeline_width, height) in pixels.
        """
        if self.current_df is None:
            return 1920, 1080

        # Calculate Chart Width & Height
        interval = self.current_df["EndDate"].max() - self.current_df["StartDate"].min()
        timeline_width = interval.days * self.col_width

        height = self.task_count * self.row_height

        return timeline_width, height

    def add_dates(self, df, fig, dates):
        """
        Adds textual date columns (Start/End) to the left of the Gantt chart.

        Args:
            df (pd.DataFrame): The sorted dataframe containing task data.
            fig (go.Figure): The Plotly figure object to update.
            dates (bool): If False, this method returns immediately.
        """
        if not dates:
            return

        fig.add_trace(
            go.Scatter(
                x=[0] * len(df),
                y=df["TaskID"].astype(str),
                text=df["StartDate"].dt.strftime(self.date_format),
                mode="text",
                textposition="middle center",
                showlegend=False,
                hoverinfo="skip"
            ), row=1, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=[0] * len(df),
                y=df["TaskID"].astype(str),
                text=df["EndDate"].dt.strftime(self.date_format),
                mode="text",
                textposition="middle center",
                showlegend=False,
                hoverinfo="skip"
            ), row=1, col=2
        )

    def create_gantt_chart(self, df, fig, color_column, target_col):
        """
        Draws the horizontal bars representing tasks on the timeline.

        It uses `go.Bar` with a base value (start date) rather than `px.timeline`
        to ensure compatibility with subplots and custom layouts.

        Args:
            df (pd.DataFrame): The task data.
            fig (go.Figure): The figure to draw on.
            color_column (str): The column name to use for color grouping.
            target_col (int): The subplot column index where the chart should be drawn.
        """

        colors = px.colors.qualitative.G10

        # If no color column, treat everything as one group
        if not color_column or color_column not in df.columns:
            groups = [("Tasks", df)]
        else:
            groups = df.groupby(color_column)

        color_idx = 0
        for name, group in groups:
            c = colors[color_idx % len(colors)]
            color_idx += 1

            # Calculate Duration
            # Plotly Horizontal Bars on a Date Axis:
            # base = Start Date
            # x = Duration (milliseconds)
            duration = (group["EndDate"] - group["StartDate"]).dt.total_seconds() * 1000

            fig.add_trace(
                go.Bar(
                    name=str(name),
                    y=group["TaskID"].astype(str),
                    base=group["StartDate"],
                    x=duration,
                    orientation='h',
                    marker=dict(color=c),
                    # IMPORTANT: width=0.8 forces the bar to be thick (80% of row height)
                    width=0.8,
                    hovertemplate=(
                            f"<b>{name}</b><br>" +
                            "Taak: %{y}<br>" +
                            "Start Datum: %{base|%d-%m-%Y}<br>" +
                            "Eind Datum: %{customdata[0]|%d-%m-%Y}<br>" +
                            "<extra></extra>"  # Hides the secondary box
                    ),
                    customdata=group[["EndDate"]],  # Pass EndDate for hover
                ),
                row=1, col=target_col
            )

    def apply_layout(self, task_ids, task_names, fig, width, height, target_col):
        """
        Configures the axes, grid, legend, and sizing of the final figure.

        Args:
            task_ids (list): List of Task IDs for the Y-axis.
            task_names (list): List of readable Task Names for the Y-axis labels.
            fig (go.Figure): The figure to style.
            width (int): Total width of the figure.
            height (int): Total height of the figure.
            target_col (int): The subplot column index of the main timeline.
        """
        # Configure Gantt Axis
        fig.update_xaxes(
            title_text="",
            type='date',
            dtick=self.timescale,
            tickformat=self.time_format,
            tickson="boundaries",
            tickmode='linear',
            showgrid=True,
            gridcolor='lightgray',
            side='top',
            row=1, col=target_col
        )

        fig.update_yaxes(
            tickmode='array',
            categoryarray=task_ids,
            tickvals=task_ids,
            ticktext=task_names,
            showgrid=True,
            gridcolor=LINE_COLOR,
            gridwidth=1,
            tickson="boundaries",
            zeroline=False,
        )

        if target_col == 3:
            # No X-axis for the date columns
            fig.update_xaxes(visible=False, range=[-1, 1], row=1, col=1)
            fig.update_xaxes(visible=False, range=[-1, 1], row=1, col=2)

            # --- Vertical Separators for date colums ---
            fig.add_vline(x=1, row=1, col=1, line_width=2, line_color=LINE_COLOR)
            fig.add_vline(x=1, row=1, col=2, line_width=2, line_color=LINE_COLOR)

        fig.update_layout(
            width=int(width),
            height=int(height) + 120,
            margin=dict(l=10, r=10, t=10, b=10),
            yaxis_title="",
            showlegend=True,
            legend=dict(
                orientation="v",
                xanchor="right", x=0.995,
                yanchor="top", y=0.995,
                bgcolor="rgba(255, 255, 255, 0.8)",
                bordercolor="Black",
                borderwidth=1
            ),
            barmode='overlay',  # Ensures bars draw over grid lines correctly
            hovermode='closest'
        )

    def render(self, df: pd.DataFrame, timescale_config: tuple, row_height: int,
               col_width: int, dates, date_format, color_column: str = None):
        """
        Main entry point. Coordinates the creation of the Gantt chart.

        Args:
            df (pd.DataFrame): The filtered dataframe containing tasks.
            timescale_config (tuple): Configuration for the time axis (interval, format).
            row_height (int): Height of a single task row in pixels.
            col_width (int): Width of a single time unit column in pixels.
            dates (bool): Whether to show the specific Start/End date columns.
            date_format (str): Format string for date text (e.g., "%d-%m").
            color_column (str, optional): Column name to color-code bars by.

        Returns:
            go.Figure: The fully constructed Plotly figure, or None if input is empty.
        """
        if df.empty:
            return None

        if color_column and color_column in df.columns:
            # Filter out NaNs and empty strings
            df = df[df[color_column].notna() & (df[color_column] != "")]

            # Double check if we still have data after filtering
            if df.empty:
                return None

        # Setup & Sort Data
        df_sorted = df.sort_values(["StartDate", "EndDate"], ascending=[False, False])

        task_ids = df_sorted["TaskID"].astype(str).tolist()
        task_names = df_sorted["TaskName"].astype(str).tolist()

        # store values to use when saving the chart
        self.current_df = df_sorted
        self.task_count = len(df)
        self.row_height = row_height
        self.col_width = col_width
        self._timescale(timescale_config)

        # Calculate Dimensions for the Gantt Chart specifically
        timeline_width, chart_height = self._calculate_dimensions()

        if dates:
            target_col = 3
            self.date_format = date_format
            self.date_width = self._date_width(date_format)
            total_width = self.date_width + self.date_width + timeline_width
            if total_width == 0: total_width = 1

            r_date = self.date_width / total_width
            r_time = timeline_width / total_width

            fig = make_subplots(
                rows=1, cols=3,
                shared_yaxes=True,
                horizontal_spacing=0,
                column_widths=[r_date, r_date, r_time],
                subplot_titles=("Start<br>Datum", "Eind<br>Datum", "")
            )
        else:
            target_col = 1
            total_width = timeline_width
            fig = make_subplots(
                rows=1, cols=1,
                shared_yaxes=True,
                horizontal_spacing=0,
                column_widths=[1],
                subplot_titles=""
            )

        self.add_dates(df_sorted, fig, dates)
        self.create_gantt_chart(df_sorted, fig, color_column, target_col)
        self.apply_layout(task_ids, task_names, fig, total_width, chart_height, target_col)

        self.current_fig = fig
        return fig

    def export(self, parent_widget, fmt: str):
        """
        Opens a file dialog to save the current chart to disk.

        Args:
            parent_widget (QWidget): The parent UI widget (used for the dialog).
            fmt (str): The export format ('html', 'png', or 'pdf').
        """
        if not self.current_fig:
            QMessageBox.warning(parent_widget, "Export", "Er is geen chart om te exporteren.")
            return

        timeline_width, chart_height = self._calculate_dimensions()
        total_width = self.date_width * 2 + timeline_width
        total_height = chart_height + 120

        filters = {
            'html': "HTML (*.html)",
            'pdf': "PDF (*.pdf)",
            'png': "PNG (*.png)"
        }

        downloads_path = QStandardPaths.writableLocation(
            QStandardPaths.DownloadLocation) or QStandardPaths.writableLocation(QStandardPaths.HomeLocation)
        default_path = os.path.join(downloads_path, f"gantt_export.{fmt}")

        path, _ = QFileDialog.getSaveFileName(
            parent_widget, "Export Gantt Chart", default_path, filters.get(fmt, "All Files (*)")
        )

        if not path:
            return

        try:
            if fmt == 'html':
                self.current_fig.write_html(path)
            elif fmt == 'png':
                self.current_fig.write_image(path, width=total_width, height=total_height, scale=2)
            elif fmt == 'pdf':
                self.current_fig.write_image(path, width=total_width, height=total_height)

            QMessageBox.information(parent_widget, "Succes", f"Bestand opgeslagen: {path}")
        except Exception as e:
            QMessageBox.critical(parent_widget, "Export Fout", f"Fout bij opslaan: {str(e)}")