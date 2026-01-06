from pathlib import Path
import json
from PySide6.QtWidgets import QWidget, QHBoxLayout, QComboBox, QPushButton, QInputDialog, QLabel
from PySide6.QtCore import Signal

class PresetManager(QWidget):
    preset_requested = Signal(list)
    save_requested = Signal(str)

    def __init__(self, path: Path):
        super().__init__()
        self.path = path
        self.presets = self._load_file()
        self._init_UI()

    def _init_UI(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Preset:")

        self.combo = QComboBox()
        self.combo.addItem("— Kies preset —")
        self.refresh_combo()
        self.combo.currentTextChanged.connect(self._on_preset_changed)

        save_btn = QPushButton("Opslaan")
        save_btn.clicked.connect(self.prompt_save)

        layout.addWidget(title)
        layout.addWidget(self.combo)
        layout.addWidget(save_btn)

    def _load_file(self) -> dict:
        if self.path.exists():
            return json.loads(self.path.read_text(encoding="utf-8"))
        return {}

    def refresh_combo(self):
        self.combo.blockSignals(True)
        self.combo.clear()
        self.combo.addItem("— Kies preset —")
        self.combo.addItems(sorted(self.presets.keys()))
        self.combo.blockSignals(False)

    def prompt_save(self):
        name, ok = QInputDialog.getText(self, "Preset opslaan", "Naam van preset:")
        if ok and name:
            self.save_requested.emit(name)

    def add_and_save(self, name: str, filter_names: list[str]):
        self.presets[name] = {"filters": filter_names}
        self.path.write_text(json.dumps(self.presets, indent=2), encoding="utf-8")
        self.refresh_combo()
        self.combo.setCurrentText(name)

    def _on_preset_changed(self, name):
        if name in self.presets:
            # Send the list of filter names back to Application
            self.preset_requested.emit(self.presets[name]["filters"])