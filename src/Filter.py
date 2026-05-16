import pandas as pd
from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QAbstractItemView, QDateEdit,
    QHBoxLayout, QComboBox, QMessageBox, QRadioButton, QButtonGroup, QScrollArea,
    QFrame, QSizePolicy, QPushButton, QCheckBox, QLineEdit, QListWidgetItem,
)

IGNORE = ("TaskID", "TaskName", "StartDate", "EndDate", "Created",
          "Completed", "Last Modified", "Assignee Email", "Tags", "Parent task",
          "Blocked By (Dependencies)", "Blocking (Dependencies)", )

CUTOFF = 60

class ToggleableRadioButton(QRadioButton):
    """
    A custom radio button that allows deselection when clicked again.

    Standard QRadioButtons inside a QButtonGroup cannot be deselected by the user.
    This subclass overrides mouse events to allow toggling off an already-checked state.
    """

    def mousePressEvent(self, event):
        """
        Records the checked state before the standard press event occurs.

        Args:
            event (QMouseEvent): The mouse press event.
        """
        self._was_checked = self.isChecked()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """
        Toggles off the radio button if it was already checked before the press.

        Temporarily disables exclusivity on the parent group to allow deselection.

        Args:
            event (QMouseEvent): The mouse release event.
        """
        super().mouseReleaseEvent(event)
        if self._was_checked:
            # QButtonGroup enforces exclusivity, so we must disable it temporarily
            group = self.group()
            if group:
                group.setExclusive(False)
                self.setChecked(False)
                group.setExclusive(True)
            else:
                self.setAutoExclusive(False)
                self.setChecked(False)
                self.setAutoExclusive(True)


class CollapsibleFilter(QWidget):
    """
    A wrapper widget that contains a header button and a collapsible content list.

    Used to present individual column filters in a space-saving manner.
    It also includes radio buttons to select the column for coloring or grouping.

    Attributes:
        layout (QVBoxLayout): The main layout for the wrapper.
        toggle_btn (QPushButton): The button used to expand/collapse the content.
        content (QListWidget): The list widget containing the actual filter items.
    """

    def __init__(self, title, list_widget, color_radio, group_radio):
        """
        Initializes the collapsible wrapper.

        Args:
            title (str): The name of the category/column.
            list_widget (QListWidget): The widget containing the selectable options.
            color_radio (ToggleableRadioButton): The radio button for color-coding.
            group_radio (ToggleableRadioButton): The radio button for grouping.
        """
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
        header_layout.addWidget(group_radio)

        # Content (The ListWidget)
        self.content = list_widget
        self.content.setVisible(False)  # Start collapsed

        self.layout.addWidget(header_widget)
        self.layout.addWidget(self.content)

    def toggle_content(self):
        """
        Expands or collapses the inner list widget.
        Updates the arrow icon on the toggle button (▶ or ▼) to reflect the state.
        """
        is_visible = self.toggle_btn.isChecked()
        self.content.setVisible(is_visible)
        self.toggle_btn.setText(f"{'▼' if is_visible else '▶'} {self.toggle_btn.text()[2:]}")


class FilterPanel(QWidget):
    """
    The main control panel for filtering tasks and setting view parameters.

    This panel dynamically generates UI elements based on the loaded DataFrame,
    allowing users to filter by date range, specific searchable categories.
    It also manages global visualization settings like timescale and date formatting.

    Attributes:
        options (dict): Maps column names to their respective QListWidgets.
        collapsibles (list): Stores references to all created CollapsibleFilter widgets.
        color_groups (QButtonGroup): Manages the exclusivity of the 'Color' radio buttons.
        aggregate_groups (QButtonGroup): Manages the exclusivity of the 'Group' radio buttons.
    """
    def __init__(self):
        """Initializes the FilterPanel, setting up static UI components."""
        super().__init__()
        self.options = {}
        self.selector_widgets = {}
        self.collapsibles = []
        self.color_groups = QButtonGroup(self)
        self.aggregate_groups = QButtonGroup(self)
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
        """
        Initialisation Helper
        Sets up the start/end date selectors and the timescale dropdown.
        """
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
        """
        Initialisation Helper
        Sets up the UI for enabling date columns and selecting their text format.
        """
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
        """
        Initialisation Helper
        Sets up the text search bar and the global clear/reset button.
        """
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
        """
        Checks if the user wants date columns rendered on the chart.

        Returns:
            bool: True if the 'Datums' checkbox is checked, False otherwise.
        """
        return self.dates.isChecked()

    def get_date_format(self) -> str:
        """
        Constructs the strftime format string based on user dropdown selections.

        Auto-selects separator: '-' for numeric months, ' ' for text months.

        Returns:
            str: A formatted datetime string (e.g., "%d-%m-%Y").
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
        """
        Clears all active user selections across the entire panel.

        This unselects list items, clears the search bar, and unchecks all
        color and grouping radio buttons.
        """
        for lw in self.options.values():
            lw.clearSelection()

        self.search_bar.clear()

        # Uncheck Color radio buttons
        if self.color_groups.buttons():
            self.color_groups.setExclusive(False)
            for btn in self.color_groups.buttons():
                btn.setChecked(False)
            self.color_groups.setExclusive(True)

        # Uncheck Group radio buttons
        if self.aggregate_groups.buttons():
            self.aggregate_groups.setExclusive(False)
            for btn in self.aggregate_groups.buttons():
                btn.setChecked(False)
            self.aggregate_groups.setExclusive(True)

    def filter_options(self, text):
        """
        Filters the visibility of collapsible blocks based on the search input.

        Args:
            text (str): The search string entered by the user.
        """
        search_text = text.lower()

        for widget in self.collapsibles:
            if not search_text or search_text in widget.toggle_btn.text().lower():
                widget.setVisible(True)
            else:
                widget.setVisible(False)

    def build_from_df(self, df: pd.DataFrame):
        """
        Dynamically generates categorical filter lists from the provided DataFrame.
        Skips specific columns defined in `IGNORE` and columns with no unique values.

        Args:
            df (pd.DataFrame): The full loaded Asana data.
        """
        self.remove_filters()
        for col in df.columns:
            if col in IGNORE:
                continue

            unique_count = df[col].nunique()
            if unique_count <= 0:
                continue

            self.add_filter_block(col, df)

    def add_filter_block(self, column: str, df: pd.DataFrame):
        """
        Creates a new collapsible widget for a specific dataframe column.

        Extracts unique values, truncates them if they exceed `CUTOFF`, and places
        them in a QListWidget.

        Args:
            column (str): The name of the DataFrame column.
            df (pd.DataFrame): The data used to populate the list options.
        """
        color = ToggleableRadioButton("Kleur")
        color.setProperty("column_name", column)
        self.color_groups.addButton(color)

        aggregate = ToggleableRadioButton("Groepeer")
        aggregate.setProperty("column_name", column)
        self.aggregate_groups.addButton(aggregate)

        # The List Widget
        lw = QListWidget()
        lw.setSelectionMode(QAbstractItemView.ExtendedSelection)
        lw.setSizeAdjustPolicy(QAbstractItemView.AdjustToContentsOnFirstShow)
        lw.setFrameShape(QFrame.NoFrame)
        lw.setMaximumHeight(180)

        values = sorted(df[column].dropna().astype(str).unique())
        for value in values:
            display_text = value
            if len(value) > CUTOFF:
                display_text = value[:47] + "..."

            item = QListWidgetItem(display_text)
            item.setToolTip(value)  # Show full text on hover
            item.setData(Qt.UserRole, value)  # Store original value for filtering
            lw.addItem(item)

        self.options[column] = lw

        # The Collapsible Wrapper
        collapsible = CollapsibleFilter(column, lw, color, aggregate)
        self.filters_layout.addWidget(collapsible)
        self.collapsibles.append(collapsible)

    def get_color_column(self) -> str:
        """
        Retrieves the DataFrame column currently selected for coloring.

        Returns:
            str: The column name, or None if no color radio button is checked.
        """
        checked_button = self.color_groups.checkedButton()
        if checked_button:
            return checked_button.property("column_name")
        return None

    def get_group_column(self) -> str:
        """
        Retrieves the DataFrame column currently selected for grouping.

        Returns:
            str: The column name, or None if no group radio button is checked.
        """
        checked_button = self.aggregate_groups.checkedButton()
        if checked_button:
            return checked_button.property("column_name")
        return None

    def apply_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies all selected UI filters (date range and categories) to the DataFrame.

        Filters out tasks that fall entirely outside the selected global start/end
        dates. Also filters by any specifically selected items within the list widgets.

        Args:
            df (pd.DataFrame): The un-filtered data.

        Returns:
            pd.DataFrame: A new DataFrame containing only the tasks that match the criteria.
        """
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
            selected = [i.toolTip() for i in lw.selectedItems()]
            if selected:
                df = df[df[col].astype(str).isin(selected)]

        if df.empty:
            QMessageBox.warning(self, "Geen Taken", "Er zijn geen taken gevonden die aan de huidige filters voldoen.")

        return df

    def get_scale_config(self):
        """
        Retrieves the Plotly timescale parameters based on the selected granularity.

        Returns:
            tuple: A pair of (dtick, tickformat) strings tailored for Plotly axes.
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
        """
        Clears and destroys all dynamically generated filter widgets.
        Called before rebuilding the panel when a new CSV is loaded.
        """
        self.options.clear()
        self.selector_widgets.clear()

        while self.filters_layout.count():
            w = self.filters_layout.takeAt(0).widget()
            if w:
                w.deleteLater()