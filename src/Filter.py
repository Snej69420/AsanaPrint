import pandas as pd
from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QAbstractItemView, QListWidgetItem,
    QDateEdit, QHBoxLayout, QComboBox, QMessageBox, QRadioButton, QButtonGroup, QScrollArea,
    QFrame, QSizePolicy
)

IGNORE = ("TaskID", "TaskName", "StartDate", "EndDate", "Created",
          "Completed", "Last Modified", "Assignee Email", "Tags", "Parent task",
          "Blocked By (Dependencies)", "Blocking (Dependencies)", )
DAY_IN_MS = 86400000


class FilterPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.options = {}
        self.selector_widgets = {}
        self.color_groups = QButtonGroup(self)
        self.layout = QVBoxLayout(self)

        # Time Controls
        self._time_filters()

        # ---- Filter selector (controls visibility) ----
        self.layout.addWidget(QLabel("Beschikbare filters:"))

        self.filter_selector = QListWidget()
        self.filter_selector.setFixedHeight(180)
        self.filter_selector.itemChanged.connect(self.update_active_filters)
        self.layout.addWidget(self.filter_selector)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        # This prevents the scroll area from disappearing or growing too small
        # self.scroll.setMinimumHeight(300)
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
        self.start_date.setDate(QDate.currentDate().addMonths(-3))
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

    def get_active_filter_names(self) -> list[str]:
        active = []
        for i in range(self.filter_selector.count()):
            item = self.filter_selector.item(i)
            if item.checkState() == Qt.Checked:
                active.append(item.text())
        return active

    def set_active_filters(self, filter_names: list[str]):
        """Checks the boxes for the given names and unchecks others."""
        for i in range(self.filter_selector.count()):
            item = self.filter_selector.item(i)
            state = Qt.Checked if item.text() in filter_names else Qt.Unchecked
            item.setCheckState(state)

    def build_from_df(self, df: pd.DataFrame):
        self.clear_filters()
        for col in df.columns:
            if col in IGNORE:
                continue

            unique_count = df[col].nunique()
            if unique_count <= 1:
                continue

            item = QListWidgetItem(col)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.filter_selector.addItem(item)

            self.add_selector(col, df)

    def toggle_filter_selector(self):
        open = self.toggle_filters_btn.isChecked()
        self.filter_selector_widget.setVisible(open)
        self.toggle_filters_btn.setArrowType(
            Qt.DownArrow if open else Qt.RightArrow
        )

    def update_active_filters(self, item):
        name = item.text()
        if name in self.selector_widgets:
            self.selector_widgets[name].setVisible(
                item.checkState() == Qt.Checked
            )

    def add_selector(self, column: str, df: pd.DataFrame):
        container = QWidget()
        container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        v = QVBoxLayout(container)

        # Header
        header_layout = QHBoxLayout()
        v.addLayout(header_layout)

        radio = QRadioButton("Gebruik voor kleur")
        radio.setProperty("column_name", column)  # Store column name in widget
        self.color_groups.addButton(radio)

        header_layout.addWidget(QLabel(f"<b>{column}</b>"))
        header_layout.addStretch()
        header_layout.addWidget(radio)

        # List
        lw = QListWidget()
        lw.setSelectionMode(QAbstractItemView.ExtendedSelection)
        lw.setSizeAdjustPolicy(QAbstractItemView.AdjustToContents)
        lw.setMaximumHeight(180)

        values = sorted(df[column].dropna().astype(str).unique())
        for value in values:
            lw.addItem(value)


        self.options[column] = lw
        self.selector_widgets[column] = container

        v.addWidget(lw)
        container.setVisible(False)
        self.filters_layout.addWidget(container)

    def get_color_column(self) -> str:
        """Returns the name of the column currently selected for coloring."""
        checked_button = self.color_groups.checkedButton()
        if checked_button:
            return checked_button.property("column_name")
        return None

    def apply_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df

        start_ts = pd.Timestamp(self.start_date.date().toPython())
        end_ts = pd.Timestamp(self.end_date.date().toPython())

        df["StartDate"] = pd.to_datetime(df["StartDate"]).dt.tz_localize(None)
        df["EndDate"] = pd.to_datetime(df["EndDate"]).dt.tz_localize(None)

        mask = (df["StartDate"] <= end_ts) & (df["EndDate"] >= start_ts)
        df = df[mask].copy()

        for col, lw in self.options.items():
            if not self.selector_widgets[col].isVisible():
                continue
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
        self.filter_selector.clear()
        self.options.clear()
        self.selector_widgets.clear()

        while self.filters_layout.count():
            w = self.filters_layout.takeAt(0).widget()
            if w:
                w.deleteLater()