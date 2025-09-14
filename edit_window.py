from typing import Protocol, Optional

import anki.notes
import aqt
from anki.notes import Note, NoteId
from aqt import mw, gui_hooks, addcards
from aqt.qt import *

from .config import config
from .note_importer import download_media_files, remove_media_files, get_matching_model
from .widgets import DeckCombo, ComboBox, NoteList, StatusBar
from .common import LogDebug

logDebug = LogDebug()


class SubSearchWindow(Protocol):
    current_profile_deck_combo: DeckCombo
    note_type_selection_combo: ComboBox
    note_list: NoteList
    status_bar: StatusBar


def current_add_dialog() -> Optional[addcards.AddCards]:
    return aqt.dialogs._dialogs['AddCards'][1]


class AddDialogLauncher:
    def __init__(self, subsearch: SubSearchWindow):
        super().__init__()
        self.subsearch = subsearch
        self.add_window: Optional[addcards.AddCards] = None
        self.new_note: Optional[Note] = None
        self.pre_note: Optional[Note] = None
        self.block_close_cb: bool = False
        gui_hooks.add_cards_will_add_note.append(self.on_add_import)

    def create_window(self, pre_note=None) -> NoteId:
        if pre_note is None:
            self.add_window = aqt.dialogs.open('AddCards', mw)
            self.add_window.activateWindow()
            return self.add_window.editor.note.id

        self.pre_note = pre_note
        logDebug("Preparing add window")

        if self.subsearch.current_profile_deck_combo.currentData() is None:
            raise Exception(f'deck was not found: {self.subsearch.current_profile_deck_combo.currentData()}')

        mw.col.decks.select(self.subsearch.current_profile_deck_combo.currentData())

        model = get_matching_model(self.subsearch.note_type_selection_combo.currentData(), pre_note)

        mw.col.models.setCurrent(model)
        mw.col.models.update_dict(model)

        self.new_note = anki.notes.Note(mw.col, model)

        # fill out card beforehand, so we can be sure of other_note's id
        for key in self.new_note.keys():
            if key in pre_note.keys() and key != 'source_info' or config['import_source_info']:
                self.new_note[key] = str(pre_note[key])

        # Get media just yet, so it can still be deleted later but causes no unwanted behaviour
        download_media_files(self.pre_note)

        def open_window():
            self.add_window = aqt.dialogs.open('AddCards', mw)

            self.add_window.editor.set_note(self.new_note)

            self.add_window.activateWindow()
            # Modify Bottom Button Bar against confusion
            self.add_window.addButton.setText('Import')
            self.add_window.historyButton.hide()
            if config['show_help_buttons']:
                self.add_window.helpButton.setText('Anki Help')
            else:
                self.add_window.helpButton.hide()

            aqt.dialogs.open('AddCards', mw)

            self.add_window.setAndFocusNote(self.add_window.editor.note)

            self.subsearch.status_bar.set_status(custom_text="Waiting for edit to finish...")

        if current_add_dialog() is not None:
            current_add_dialog().closeWithCallback(open_window)
        else:
            open_window()

            def on_visibility_changed():
                if not self.block_close_cb and self.new_note:
                    self.subsearch.status_bar.hide()
                    remove_media_files(self.new_note)

            # Remove Media on close if not in saving progress
            qconnect(self.add_window.windowHandle().visibilityChanged, on_visibility_changed)

        self.subsearch.status_bar.hide()
        return self.new_note.id

    def on_add_import(self, problem: Optional[str], note: Note) -> str:
        if self.pre_note and current_add_dialog() and current_add_dialog() is self.add_window:
            logDebug("Importing edited note")
            self.subsearch.note_list.clear_selection()
            self.subsearch.status_bar.set_status(successes=1)
            mw.reset()
            self.block_close_cb = True  # Block media removal
            self.add_window.close()
        self.pre_note = None
        self.add_window = None
        return problem
