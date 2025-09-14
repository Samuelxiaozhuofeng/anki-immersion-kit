# Copyright: Ren Tatsumoto <tatsu at autistici.org> and FileX <filex.stuff@proton.me>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import os
from urllib import request, parse
import zipfile

from aqt import mw
from aqt.qt import *
from aqt.utils import restoreGeom, saveGeom, disable_help_button, showInfo, ask_user

from .subsearch_ajt.about_menu import tweak_window, menu_root_entry
from .common import ADDON_NAME, add_kakasi, LogDebug
from .config import config
from .widgets import ItemBox, SpinBox
from .note_getter import import_kakasi

logDebug = LogDebug()


def make_checkboxes() -> dict[str, QCheckBox]:
    return {key: QCheckBox(key.replace('_', ' ').capitalize()) for key in config.bool_keys()}


class SubSearchSettingsDialog(QDialog):
    name = 'subsearch_settings_dialog'

    def __init__(self, *args, **kwargs) -> None:
        QDialog.__init__(self, *args, **kwargs)
        disable_help_button(self)
        self._setup_ui()
        tweak_window(self)
        restoreGeom(self, self.name, adjustSize=True)

    def _setup_ui(self) -> None:
        self.setMinimumWidth(300)
        self.setWindowTitle(f"{ADDON_NAME}'s Settings")
        self.setLayout(self._make_layout())
        self.connect_widgets()
        self.add_tooltips()

    def _make_layout(self) -> QLayout:
        self.hidden_fields_box = ItemBox(parent=self, initial_values=config['hidden_fields'])
        self.button_box = QDialogButtonBox((QDialogButtonBox.StandardButton.Help | QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
                                           if config['show_help_buttons'] else (QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel))
        self.checkboxes = make_checkboxes()

        layout = QVBoxLayout()

        layout.addLayout(self._make_form())
        layout.addWidget(self.hidden_fields_box)
        for key, checkbox in self.checkboxes.items():
            layout.addWidget(checkbox)
            checkbox.setChecked(config.get(key))
        layout.addStretch()
        layout.addWidget(self.button_box)
        return layout

    def _make_form(self) -> QFormLayout:
        self.max_notes_edit = SpinBox(min_val=10, max_val=10_000, step=50, value=config['notes_per_page'])
        self.hidden_fields_edit = QLineEdit()
        self.hidden_fields_edit.setPlaceholderText("New item")

        layout = QFormLayout()
        layout.addRow("Max displayed notes", self.max_notes_edit)
        layout.addRow("Hide fields matching", self.hidden_fields_edit)
        return layout

    def connect_widgets(self):
        qconnect(self.button_box.accepted, self.accept)
        qconnect(self.button_box.rejected, self.reject)
        qconnect(self.button_box.helpRequested, self.show_help)
        qconnect(self.hidden_fields_edit.textChanged, lambda: self.hidden_fields_box.new_item(self.hidden_fields_edit))

    def add_tooltips(self) -> None:
        self.hidden_fields_edit.setToolTip(
            "Hide fields whose names contain these words.\n"
            "Press space or comma to commit."
        )

    def show_help(self): 
        with open(os.path.join(os.path.dirname(__file__), 'config.md')) as c_help:
            showInfo(c_help.read(), title=ADDON_NAME+" Settings Help", textFormat="markdown")

    def done(self, result: int) -> None:
        saveGeom(self, self.name)
        return super().done(result)

    def accept(self) -> None:
        config['notes_per_page'] = self.max_notes_edit.value()
        config['hidden_fields'] = self.hidden_fields_box.values()
        for key, checkbox in self.checkboxes.items():
            if key == "jlab_format" and checkbox.isChecked() and not config[key] and not os.path.exists(os.path.join(os.path.dirname(__file__), 'pykakasi', 'src', '__init__.py')):
                    logDebug("Pykakasi not found, asking for add...")
                    ask_user("Sub2Srs Search:\n\nFor Jlab Format required pykakasi not found. Do you want to download it now?", 
                             lambda yes: add_kakasi(import_kakasi) if yes else 0, parent=mw)
            config[key] = checkbox.isChecked()
        config.write_config()
        return super().accept()


def init():
    def on_open_settings():
        dialog = SubSearchSettingsDialog(parent=mw)
        dialog.exec()

    root_menu = menu_root_entry()
    action = root_menu.addAction(f"{ADDON_NAME}'s Settings...")
    qconnect(action.triggered, on_open_settings)
