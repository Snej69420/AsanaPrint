import os
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QFileDialog, QMessageBox

LINE_COLOR = "#3b3b3b"
MARGINS = dict(l=10, r=10, t=10, b=10)

DAY_IN_MS = 86400000
D7 = 7 * DAY_IN_MS


class GanttRenderer:
    def __init__(self):
        self.current_df = None
        self.current_fig = None
        self.task_count = 0
        self.row_height = 0
        self.col_width = 0
        self.timescale = "M1"
        self.time_format = "%b\n%Y"
        self.days_scale = 0

        self.date_width = 0
        self.date_format = ""

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

    def _date_width(self, fmt: str) -> int:
        width = 40
        if "%A" in fmt:
            width += 80
        elif "%a" in fmt:
            width += 30
        if "%d" in fmt: width += 20
        if "%B" in fmt:
            width += 100
        elif "%b" in fmt:
            width += 40
        elif "%m" in fmt:
            width += 20
        if "%Y" in fmt:
            width += 40
        elif "%y" in fmt:
            width += 20
        return width

    def _calculate_dimensions(self):
        if self.current_df is None:
            return 1920, 1080

        interval = self.current_df["EndDate"].max() - self.current_df["StartDate"].min()
        timeline_width = interval.days * self.col_width
        timeline_width = max(timeline_width, 480)

        height = self.task_count * self.row_height
        height = max(height, 50)
        return timeline_width, height

    def add_dates(self, df, fig, dates, group_column):
        if not dates:
            return

        if group_column and group_column in df.columns:
            y_data = [df[group_column], df["UniqueName"]]
        else:
            y_data = df["UniqueName"]

        fig.add_trace(
            go.Scatter(x=[0] * len(df), y=y_data, text=df["StartDate"].dt.strftime(self.date_format), mode="text",
                       textposition="middle center", showlegend=False, hoverinfo="skip"), row=1, col=1)
        fig.add_trace(
            go.Scatter(x=[0] * len(df), y=y_data, text=df["EndDate"].dt.strftime(self.date_format), mode="text",
                       textposition="middle center", showlegend=False, hoverinfo="skip"), row=1, col=2)

    def create_gantt_chart(self, df, fig, color_column, target_col, group_column):
        colors = px.colors.qualitative.G10
        groups = [("Tasks", df)] if not color_column or color_column not in df.columns else df.groupby(color_column)

        color_idx = 0
        for name, group in groups:
            c = colors[color_idx % len(colors)]
            color_idx += 1
            duration = (group["EndDate"] - group["StartDate"]).dt.total_seconds() * 1000

            if group_column and group_column in df.columns:
                y_data = [group[group_column], group["UniqueName"]]
            else:
                y_data = group["UniqueName"]

            fig.add_trace(
                go.Bar(
                    name=str(name), y=y_data, base=group["StartDate"], x=duration,
                    orientation='h', marker=dict(color=c), width=0.8,
                    hovertemplate=(
                        f"<b>{name}</b><br>Taak: %{{customdata[1]}}<br>Start Datum: %{{base|%d-%m-%Y}}<br>Eind Datum: %{{customdata[0]|%d-%m-%Y}}<br><extra></extra>"),
                    customdata=group[["EndDate", "TaskName"]],
                ),
                row=1, col=target_col
            )

    def apply_layout(self, fig, width, height, target_col):
        fig.update_xaxes(
            title_text="", type='date', dtick=self.timescale, tickformat=self.time_format,
            tickson="boundaries", tickmode='linear', showgrid=True, gridcolor='lightgray',
            side='top', row=1, col=target_col
        )

        # Force Y-axis to read top-to-bottom so the earliest task sits at the top
        fig.update_yaxes(
            autorange="reversed", showgrid=True, gridcolor=LINE_COLOR,
            gridwidth=1, tickson="boundaries", zeroline=False
        )

        if target_col == 3:
            fig.update_xaxes(visible=False, range=[-1, 1], row=1, col=1)
            fig.update_xaxes(visible=False, range=[-1, 1], row=1, col=2)
            fig.add_vline(x=1, row=1, col=1, line_width=2, line_color=LINE_COLOR)
            fig.add_vline(x=1, row=1, col=2, line_width=2, line_color=LINE_COLOR)

        fig.update_layout(
            width=int(width), height=int(height) + 120, margin=MARGINS, yaxis_title="",
            showlegend=True, legend=dict(orientation="v", xanchor="right", x=0.995, yanchor="top", y=0.995,
                                         bgcolor="rgba(255, 255, 255, 0.8)", bordercolor="Black", borderwidth=1),
            barmode='overlay', hovermode='closest'
        )

    def render(self, df: pd.DataFrame, timescale_config: tuple, row_height: int,
               col_width: int, dates, date_format, color_column: str = None, group_column: str = None):
        if df.empty:
            return None

        # Filter out NaNs
        if color_column and color_column in df.columns:
            df = df[df[color_column].notna() & (df[color_column] != "")]
        if group_column and group_column in df.columns:
            df = df[df[group_column].notna() & (df[group_column] != "")]

        if df.empty: return None

        # 1. SETUP & SORT DATA
        # Ascending=True ensures earliest start dates are first. Same start date -> earlier end date first.
        if group_column and group_column in df.columns:
            df_sorted = df.sort_values([group_column, "StartDate", "EndDate"], ascending=[True, True, True])
            df_sorted[group_column] = f"{group_column}: " + df_sorted[group_column].astype(str)

        else:
            df_sorted = df.sort_values(["StartDate", "EndDate"], ascending=[True, True])

        # Create guaranteed unique task names using zero-width spaces (\u200b)
        counts = {}
        unique_names = []
        for name in df_sorted["TaskName"].astype(str):
            if name in counts:
                counts[name] += 1
                unique_names.append(name + ("\u200b" * counts[name]))
            else:
                counts[name] = 0
                unique_names.append(name)
        df_sorted["UniqueName"] = unique_names

        self.current_df = df_sorted
        self.task_count = len(df)
        self.row_height = row_height
        self.col_width = col_width
        self._timescale(timescale_config)

        timeline_width, chart_height = self._calculate_dimensions()

        if dates:
            target_col = 3
            self.date_format = date_format
            self.date_width = self._date_width(date_format)
            total_width = self.date_width * 2 + timeline_width + MARGINS['l'] + MARGINS['r']
            if total_width == 0: total_width = 1

            r_date = self.date_width / total_width
            fig = make_subplots(
                rows=1, cols=3, shared_yaxes=True, horizontal_spacing=0,
                column_widths=[r_date, r_date, timeline_width / total_width],
                subplot_titles=("Start<br>Datum", "Eind<br>Datum", "")
            )
        else:
            target_col = 1
            total_width = timeline_width
            fig = make_subplots(rows=1, cols=1, shared_yaxes=True, horizontal_spacing=0)

        # 2. DUMMY TRACE
        # This invisible trace passes all tasks to Plotly in exactly the sorted order FIRST.
        # This locks the Y-Axis into perfect chronological order, preventing color groups from ruining it.
        if group_column and group_column in df.columns:
            y_dummy = [df_sorted[group_column], df_sorted["UniqueName"]]
        else:
            y_dummy = df_sorted["UniqueName"]

        fig.add_trace(
            go.Scatter(
                x=[df_sorted["StartDate"].min()] * len(df_sorted),
                y=y_dummy, mode='markers', marker=dict(color='rgba(0,0,0,0)'),
                showlegend=False, hoverinfo='skip'
            ),
            row=1, col=target_col
        )

        # 3. DRAW CHART
        self.add_dates(df_sorted, fig, dates, group_column)
        self.create_gantt_chart(df_sorted, fig, color_column, target_col, group_column)
        self.apply_layout(fig, total_width, chart_height, target_col)

        # 4. DRAW GROUP SEPARATOR LINES
        if group_column and group_column in df_sorted.columns:
            group_values = df_sorted[group_column].tolist()
            total_tasks = len(group_values)

            # 1. Draw the top boundary line (above the first item)
            fig.add_shape(
                type="line",
                xref="paper", x0=0, x1=1,
                yref="y", y0=-0.5, y1=-0.5,
                line=dict(color="#111111", width=2),
                layer="above"
            )

            # 2. Draw the inner separator lines (between groups)
            for i in range(1, total_tasks):
                if group_values[i] != group_values[i - 1]:
                    fig.add_shape(
                        type="line",
                        xref="paper", x0=0, x1=1,
                        yref="y", y0=i - 0.5, y1=i - 0.5,
                        line=dict(color="#111111", width=2),
                        layer="above"
                    )

            # 3. Draw the bottom boundary line (below the last item)
            fig.add_shape(
                type="line",
                xref="paper", x0=0, x1=1,
                yref="y", y0=total_tasks - 0.5, y1=total_tasks - 0.5,
                line=dict(color="#111111", width=2),
                layer="above"
            )

        self.current_fig = fig
        return fig

    def export(self, parent_widget, fmt: str):
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