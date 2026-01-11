import pandas as pd
from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QAbstractItemView, QDateEdit,
    QHBoxLayout, QComboBox, QMessageBox, QRadioButton, QButtonGroup, QScrollArea,
    QFrame, QSizePolicy, QPushButton,
)

IGNORE = ("TaskID", "TaskName", "StartDate", "EndDate", "Created",
          "Completed", "Last Modified", "Assignee Email", "Tags", "Parent task",
          "Blocked By (Dependencies)", "Blocking (Dependencies)", )
DAY_IN_MS = 86400000


class CollapsibleFilter(QWidget):
    """A wrapper widget that contains a header button and a content list."""

    def __init__(self, title, list_widget, color_radio):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.layout = QVBoxLayout(self)

        # Header Row
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)

        self.toggle_btn = QPushButton(f"▶ {title}")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setStyleSheet("QPushButton { text-align: left; font-weight: bold; border: none; }")
        self.toggle_btn.clicked.connect(self.toggle_content)

        header_layout.addWidget(self.toggle_btn, 1)
        header_layout.addWidget(color_radio)

        # Content (The ListWidget)
        self.content = list_widget
        self.content.setVisible(False)  # Start collapsed

        self.layout.addWidget(header_widget)
        self.layout.addWidget(self.content)

    def toggle_content(self):
        is_visible = self.toggle_btn.isChecked()
        self.content.setVisible(is_visible)
        self.toggle_btn.setText(f"{'▼' if is_visible else '▶'} {self.toggle_btn.text()[2:]}")


class FilterPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.options = {}
        self.selector_widgets = {}
        self.color_groups = QButtonGroup(self)
        self.layout = QVBoxLayout(self)

        # Time Controls
        self._time_filters()

        # Scrollable Area to populate with filters
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setMinimumHeight(180)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.StyledPanel)
        self.scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # This widget holds the actual filter lists
        self.filters_container = QWidget()
        self.filters_layout = QVBoxLayout(self.filters_container)
        self.filters_layout.setAlignment(Qt.AlignTop)  # Keep selectors at the top

        self.scroll.setWidget(self.filters_container)
        self.layout.addWidget(self.scroll)

    def _time_filters(self):
        start_row = QHBoxLayout()
        start_row.addWidget(QLabel("Start Datum ≥"))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("dd-MM-yyyy")
        self.start_date.setDate(QDate.currentDate())
        start_row.addWidget(self.start_date)
        self.layout.addLayout(start_row)

        end_row = QHBoxLayout()
        end_row.addWidget(QLabel("Eind Datum ≤"))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("dd-MM-yyyy")
        self.end_date.setDate(QDate.currentDate().addMonths(6))
        end_row.addWidget(self.end_date)
        self.layout.addLayout(end_row)

        scale_row = QHBoxLayout()
        scale_row.addWidget(QLabel("Tijdschaal:"))
        self.scale_combo = QComboBox()
        self.scale_combo.addItems(["Dagen", "Weken", "Maanden", "Kwartalen", "Jaren"])
        self.scale_combo.setCurrentText("Maanden")
        scale_row.addWidget(self.scale_combo)
        self.layout.addLayout(scale_row)

    def build_from_df(self, df: pd.DataFrame):
        self.clear_filters()
        for col in df.columns:
            if col in IGNORE:
                continue

            unique_count = df[col].nunique()
            if unique_count <= 0:
                continue

            self.add_filter_block(col, df)

    def add_filter_block(self, column: str, df: pd.DataFrame):
        # Color Radio Button
        radio = QRadioButton("Kleur")
        radio.setProperty("column_name", column)
        self.color_groups.addButton(radio)

        # The List Widget
        lw = QListWidget()
        lw.setSelectionMode(QAbstractItemView.ExtendedSelection)
        lw.setSizeAdjustPolicy(QAbstractItemView.AdjustToContentsOnFirstShow)
        lw.setMaximumHeight(180)

        values = sorted(df[column].dropna().astype(str).unique())
        for value in values:
            lw.addItem(value)

        self.options[column] = lw

        # The Collapsible Wrapper
        collapsible = CollapsibleFilter(column, lw, radio)
        self.filters_layout.addWidget(collapsible)

    def get_color_column(self) -> str:
        """Returns the name of the column currently selected for coloring."""
        checked_button = self.color_groups.checkedButton()
        if checked_button:
            return checked_button.property("column_name")
        return None

    def apply_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df

        df = df.copy()

        start_ts = pd.Timestamp(self.start_date.date().toPython())
        end_ts = pd.Timestamp(self.end_date.date().toPython())

        df["StartDate"] = pd.to_datetime(df["StartDate"]).dt.tz_localize(None)
        df["EndDate"] = pd.to_datetime(df["EndDate"]).dt.tz_localize(None)

        mask = (df["StartDate"] <= end_ts) & (df["EndDate"] >= start_ts)
        df = df[mask].copy()

        for col, lw in self.options.items():
            selected = [i.text() for i in lw.selectedItems()]
            if selected:
                df = df[df[col].astype(str).isin(selected)]

        if df.empty:
            QMessageBox.warning(self, "Geen Taken", "Er zijn geen taken gevonden die aan de huidige filters voldoen.")

        return df

    def get_scale_config(self):
        """
        Returns a tuple of (dtick, tickformat)
        """
        text = self.scale_combo.currentText()
        if text == "Dagen":
            return "D1", "%d-%b"
        if text == "Weken":
            return 7*DAY_IN_MS, "%d-%b"
        if text == "Maanden":
            return "M1", "%b\n%Y"
        if text == "Kwartalen":
            return "M3", "Q%q: %b\n%Y"
        if text == "Jaren":
            return "M12", "%Y"
        return "M1", "%b\n%Y"

    def clear_filters(self):
        self.options.clear()
        self.selector_widgets.clear()

        while self.filters_layout.count():
            w = self.filters_layout.takeAt(0).widget()
            if w:
                w.deleteLater()