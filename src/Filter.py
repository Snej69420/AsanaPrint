import pandas as pd
from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QAbstractItemView, QDateEdit,
    QHBoxLayout, QComboBox, QMessageBox, QRadioButton, QButtonGroup, QScrollArea,
    QFrame, QSizePolicy, QPushButton, QCheckBox, QLineEdit
)

IGNORE = ("TaskID", "TaskName", "StartDate", "EndDate", "Created",
          "Completed", "Last Modified", "Assignee Email", "Tags", "Parent task",
          "Blocked By (Dependencies)", "Blocking (Dependencies)", )


class CollapsibleFilter(QWidget):
    """A wrapper widget that contains a header button and a content list."""

    def __init__(self, title, list_widget, color_radio):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Header Row
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(2, 2, 2, 2)

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
        self.collapsibles = []
        self.color_groups = QButtonGroup(self)
        self.layout = QVBoxLayout(self)

        # Time Controls
        self._time_filters()

        # Date Columns
        self._date_columns()

        # Search & Clear Controls ---
        self._search_clear()

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
        self.filters_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll.setWidget(self.filters_container)
        self.scroll.setFrameShape(QFrame.NoFrame)
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

        # Tijdschaal
        scale_row = QHBoxLayout()
        scale_row.addWidget(QLabel("Tijdschaal:"))
        self.scale_combo = QComboBox()
        self.scale_combo.addItems(["Dagen", "Weken", "Maanden", "Kwartalen", "Jaren"])
        self.scale_combo.setCurrentText("Maanden")
        scale_row.addWidget(self.scale_combo)
        self.layout.addLayout(scale_row)

    def _date_columns(self):
        date_row = QHBoxLayout()
        self.dates = QCheckBox("Datums")
        self.dates.setToolTip("Voegt start en einddatum kolommen toe.")
        date_row.addWidget(self.dates)

        # Container for the 3 dropdowns
        settings_box = QHBoxLayout()
        settings_box.setSpacing(5)

        # Day Selector
        self.day_format = QComboBox()
        self.day_format.setToolTip("Dag Formaat")
        self.day_format.addItem("01", "%d")
        self.day_format.addItem("Ma 01", "%a %d")
        self.day_format.addItem("Maandag 01", "%A %d")
        settings_box.addWidget(self.day_format)

        # Month Selector
        self.month_format = QComboBox()
        self.month_format.setToolTip("Maand Formaat")
        self.month_format.addItem("01", "%m")
        self.month_format.addItem("Jan", "%b")
        self.month_format.addItem("Januari", "%B")
        settings_box.addWidget(self.month_format)

        # Year Selector
        self.year_format = QComboBox()
        self.year_format.setToolTip("Jaar Formaat")
        self.year_format.addItem("Geen", "")
        self.year_format.addItem("26", "%y")
        self.year_format.addItem("2026", "%Y")
        settings_box.addWidget(self.year_format)

        date_row.addLayout(settings_box)
        date_row.addStretch()
        self.layout.addLayout(date_row)

    def _search_clear(self):
        search_row = QHBoxLayout()

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Zoek in filters...")
        self.search_bar.textChanged.connect(self.filter_options)  # Connect to search logic
        search_row.addWidget(self.search_bar)

        self.clear_btn = QPushButton("X")
        self.clear_btn.setToolTip("Wis alle selecties")
        self.clear_btn.setFixedWidth(30)
        self.clear_btn.setStyleSheet("font-weight: bold; color: red;")
        self.clear_btn.clicked.connect(self.reset_selections)
        search_row.addWidget(self.clear_btn)

        self.layout.addLayout(search_row)

    def get_show_dates(self) -> bool:
        return self.dates.isChecked()

    def get_date_format(self) -> str:
        """
        Constructs the strftime string based on the 3 dropdowns.
        Auto-selects separator: '-' for numeric months, ' ' for text months.
        """
        d = self.day_format.currentData()
        m = self.month_format.currentData()
        y = self.year_format.currentData()

        # Logic: Use dashes for pure numbers (01-01), spaces for text (01 Jan)
        sep = "-" if m == "%m" else " "

        fmt = f"{d}{sep}{m}"

        if y:
            fmt += f"{sep}{y}"

        return fmt

    def reset_selections(self):
        """Clears all selections in all list widgets."""
        for lw in self.options.values():
            lw.clearSelection()

        self.search_bar.clear()

    def filter_options(self, text):
        """Hides entire collapsible widgets if their title doesn't match."""
        search_text = text.lower()

        for widget in self.collapsibles:
            if not search_text or search_text in widget.toggle_btn.text().lower():
                widget.setVisible(True)
            else:
                widget.setVisible(False)

    def build_from_df(self, df: pd.DataFrame):
        self.remove_filters()
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
        lw.setFrameShape(QFrame.NoFrame)
        lw.setMaximumHeight(180)

        values = sorted(df[column].dropna().astype(str).unique())
        for value in values:
            lw.addItem(value)

        self.options[column] = lw

        # The Collapsible Wrapper
        collapsible = CollapsibleFilter(column, lw, radio)
        self.filters_layout.addWidget(collapsible)
        self.collapsibles.append(collapsible)

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
            return "D7", "%d-%b"
        if text == "Maanden":
            return "M1", "%b\n%Y"
        if text == "Kwartalen":
            return "M3", "Q%q: %b\n%Y"
        if text == "Jaren":
            return "M12", "%Y"
        return "M1", "%b\n%Y"

    def remove_filters(self):
        self.options.clear()
        self.selector_widgets.clear()

        while self.filters_layout.count():
            w = self.filters_layout.takeAt(0).widget()
            if w:
                w.deleteLater()