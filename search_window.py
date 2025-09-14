# TODO:
# - Add full support for Hiragana and Romaji conversion
# - Add debug log open button
# - Replace menu entry with expandable one in tools
#   menu_for_helper = mw.form.menuTools.addMenu("FSRS4Anki Helper")
#   menu_for_helper.addAction(menu_auto_reschedule)
#   menu_for_helper.addAction(menu_auto_reschedule_after_review)
#   menu_for_helper.addAction(menu_auto_disperse)
#   menu_for_helper.addAction(menu_load_balance)
#   menu_for_free_days = menu_for_helper.addMenu(
#       "No Anki on Free Days (requires Load Balancing)"
#   )
# menu_for_helper.addSeparator()
# - Check for comp of editing the sound:URL tag and the playback of the correct audio
# - add Listening part to templ
# - play button playing once and then is unresponsive until stopped
# - add option to switch all cards between online and offline
# - fix linux left pref arrow not correctly displaying
# - fix if image really not found, show error in tile and be careful with download of it
# - fit default config
# - if playing around with config while cached window existing (esp. Displ. Notes), it gets mashed up

import json
from collections import defaultdict
from os import path, mkdir
from math import ceil

from aqt import mw, gui_hooks
from aqt.qt import *
from aqt.utils import disable_help_button, restoreGeom, saveGeom, showInfo, openLink, tooltip, ask_user, show_critical
import urllib.error as urlerror
from aqt.operations import QueryOp

from .config import config
from .common import ADDON_NAME, LogDebug, add_kakasi, sorted_decks_and_ids, NameId
from .subsearch_ajt.about_menu import menu_root_entry
from .subsearch_ajt.consts import SOURCE_LINK
from .note_importer import import_note, ImportResult
from .widgets import SearchResultLabel, DeckCombo, ComboBox, SpinBox, StatusBar, NoteList, ItemBox, WIDGET_HEIGHT
from .edit_window import AddDialogLauncher
from . import note_getter

logDebug = LogDebug()


class MainDialogUI(QDialog):
    name = "subsearch_dialog"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_bar = StatusBar()
        self.search_result_label = SearchResultLabel()
        self.current_profile_deck_combo = DeckCombo()
        self.exact = QCheckBox("Exact Matches")
        self.jlpt_level = [QLabel('JLPT'), ComboBox()]
        self.wanikani_level = [QLabel('WaniKani'), ComboBox()]
        self.category = [QLabel('Category'), ComboBox()]
        self.sort = [QLabel('Sort by'), ComboBox()]
        self.min_length = [QLabel('Minimal Length:'), SpinBox(0, 200, 1, 0)]
        self.max_length = [QLabel('Maximal Length:'), SpinBox(0, 500, 1, 0)]
        self.edit_button = QPushButton('Edit')
        self.import_button = QPushButton('Import')
        self.filter_collapse = QPushButton('🞁')
        self.search_term_edit = QLineEdit()
        self.search_button = QPushButton('Search')
        if config['show_help_buttons']:
            self.help_button = QPushButton('Help')
        self.page_prev = QPushButton('🞀')
        self.note_list = NoteList()
        self.page_skip = QPushButton('🞂')
        self.note_type_selection_combo = ComboBox()
        self.note_fields = QLabel(wordWrap=True)
        self.init_ui()

    def init_ui(self):
        self.search_term_edit.setPlaceholderText('Search Term')
        self.setLayout(self.make_main_layout())
        self.setWindowTitle(ADDON_NAME)
        self.set_default_sizes()

    def make_filter_row(self) -> QLayout:
        filter_row = QHBoxLayout()
        self.filter_collapse.setFixedWidth(40)
        self.filter_collapse.setDefault(False)
        filter_row.addWidget(self.filter_collapse)
        filter_row.addWidget(self.search_term_edit)
        self.search_button.setDefault(True)
        filter_row.addWidget(self.search_button)
        if config['show_help_buttons']:
            filter_row.addWidget(self.help_button)
        return filter_row

    def make_main_layout(self) -> QLayout:
        main_vbox = QVBoxLayout()
        main_vbox.addLayout(self.make_filter_row())
        main_vbox.addLayout(self.make_preferences_row())
        main_vbox.addLayout(self.make_preferences_row2())
        main_vbox.addWidget(self.search_result_label)
        main_vbox.addLayout(self.make_note_list())
        main_vbox.addLayout(self.status_bar)
        main_vbox.addLayout(self.make_input_row())
        main_vbox.addLayout(self.make_note_field_label())
        return main_vbox

    def make_preferences_row(self) -> QLayout:
        pref_row = QHBoxLayout()
        pref_row.addWidget(self.exact)
        pref_row.addWidget(self.jlpt_level[0])
        pref_row.addWidget(self.jlpt_level[1])
        pref_row.addWidget(self.wanikani_level[0])
        pref_row.addWidget(self.wanikani_level[1])
        pref_row.addWidget(self.category[0])
        pref_row.addWidget(self.category[1])
        pref_row.addWidget(self.sort[0])
        pref_row.addWidget(self.sort[1])
        pref_row.setStretchFactor(pref_row, 1)
        return pref_row

    def make_preferences_row2(self):
        pref_row2 = QHBoxLayout()
        pref_row2.addWidget(self.min_length[0])
        pref_row2.addWidget(self.min_length[1])
        pref_row2.addWidget(self.max_length[0])
        pref_row2.addWidget(self.max_length[1])
        pref_row2.setStretchFactor(pref_row2, 1)
        return pref_row2

    def make_note_list(self):
        note_row = QHBoxLayout()
        self.page_prev.setFixedWidth(17)
        self.page_prev.setFixedHeight(45)
        self.page_prev.setEnabled(False)
        self.page_prev.setToolTip("Previous Page")
        self.page_skip.setFixedWidth(17)
        self.page_skip.setFixedHeight(45)
        self.page_skip.setEnabled(False)
        self.page_skip.setToolTip("Next Page")
        note_row.addWidget(self.page_prev)
        note_row.addWidget(self.note_list)
        note_row.addWidget(self.page_skip)
        note_row.setStretch(1, 1)
        return note_row

    def set_default_sizes(self):
        combo_min_width = 120
        self.setMinimumSize(680, 500)

        all_combos = [self.current_profile_deck_combo,
                      self.note_type_selection_combo,
                      self.jlpt_level[1],
                      self.sort[1],
                      self.wanikani_level[1],
                      self.category[1]]

        all_widgets = [self.exact,
                       self.edit_button,
                       self.import_button,
                       self.filter_collapse,
                       self.search_button,
                       self.search_term_edit]
        if config['show_help_buttons']:
            all_widgets.append(self.help_button)

        for w in all_widgets:
            w.setMinimumHeight(WIDGET_HEIGHT)
        for combo in all_combos:
            combo.setMinimumWidth(combo_min_width)
            combo.setSizePolicy(QSizePolicy.Policy.Expanding,
                                QSizePolicy.Policy.Expanding)

    def make_input_row(self) -> QLayout:
        import_row = QHBoxLayout()
        import_row.addWidget(QLabel('Into Deck'))
        import_row.addWidget(self.current_profile_deck_combo)
        import_row.addWidget(QLabel('Map to Note Type'))
        import_row.addWidget(self.note_type_selection_combo)
        import_row.addWidget(self.edit_button)
        import_row.addWidget(self.import_button)
        import_row.setStretchFactor(import_row, 1)
        return import_row

    def make_note_field_label(self) -> QLayout:
        note_field_box = QHBoxLayout()
        self.note_fields.hide()
        self.note_fields.setStyleSheet('QLabel { color: red; }')
        note_field_box.addWidget(self.note_fields)
        note_field_box.setStretch(0, 1)
        return note_field_box


#############################################################################
# UI logic
#############################################################################


class WindowState:
    def __init__(self, window: MainDialogUI):
        self._window = window
        self._json_filepath = path.join(path.dirname(
            __file__), 'user_files', 'window_state.json')
        self._map = {
            "to_deck": self._window.current_profile_deck_combo,
            "note_type": self._window.note_type_selection_combo,
            "exact": self._window.exact,
            'jlpt_level': self._window.jlpt_level[1],
            'wanikani_level': self._window.wanikani_level[1],
            'category': self._window.category[1],
            'sort': self._window.sort[1],
            'min_length': self._window.min_length[1],
            'max_length': self._window.max_length[1]
        }

        self._state = defaultdict(dict)

    def save(self):
        for key, widget in self._map.items():
            try:
                self._state[mw.pm.name][key] = widget.currentText()
            except AttributeError:
                try:
                    self._state[mw.pm.name][key] = widget.value()
                except AttributeError:
                    self._state[mw.pm.name][key] = widget.isChecked()
        if not path.exists(self._json_filepath):
            mkdir(path.dirname(self._json_filepath))
        with open(self._json_filepath, 'w', encoding='utf8') as of:
            json.dump(self._state, of, indent=4, ensure_ascii=False)
        saveGeom(self._window, self._window.name)
        logDebug('Saved window state.')

    def _load(self) -> bool:
        if self._state:
            return True
        elif path.isfile(self._json_filepath):
            with open(self._json_filepath, encoding='utf8') as f:
                self._state.update(json.load(f))
            return True
        else:
            return False

    def restore(self):
        if self._load() and (profile_settings := self._state.get(mw.pm.name)):
            for key, widget in self._map.items():
                if profile_settings[key]:
                    try:
                        if (value := profile_settings[key]) in widget.all_items():
                            widget.setCurrentText(value)
                    except AttributeError:
                        try:
                            widget.setValue(value)
                        except AttributeError:
                            widget.setChecked(value)
        restoreGeom(self._window, self._window.name, adjustSize=True)


class MainDialog(MainDialogUI):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.window_state = WindowState(self)
        self._add_window_mgr = AddDialogLauncher(self)
        self.search_block = False
        self.page = 0
        self.connect_elements()
        disable_help_button(self)

    def connect_elements(self):
        qconnect(self.edit_button.clicked, self.new_edit_win)
        qconnect(self.import_button.clicked, self.start_import)
        qconnect(self.search_button.clicked, self.update_notes_list)
        qconnect(self.search_term_edit.editingFinished, self.update_notes_list)
        qconnect(self.filter_collapse.clicked, self.toggle_filter_rows)
        if config['show_help_buttons']:
            qconnect(self.help_button.clicked, lambda: openLink(
                f"{SOURCE_LINK}/src/branch/main/README.md#screenshots---how-to-use"))
        qconnect(self.page_prev.clicked, lambda: self.change_page(False))
        qconnect(self.page_skip.clicked, lambda: self.change_page())
        qconnect(self.note_type_selection_combo.currentTextChanged,
                 self.update_note_fields)

    def show(self):
        if config["jlab_format"] and not path.exists(path.join(path.dirname(__file__), 'pykakasi', 'src', '__init__.py')):
            logDebug("Pykakasi not found, asking for add...")
            ask_user("Sub2Srs Search:\n\nFor Jlab Format required pykakasi not found. Do you want to download it now?",
                     lambda yes: add_kakasi(note_getter.import_kakasi) if yes else 0)
        super().show()

        # TODO Remove
        def check_for_differing_model(model):
            if model.name.startswith('SubCard-JlabConverted'):
                model = mw.col.models.get(model.id)
                if 'Jlab-ListeningBack' not in mw.col.models.field_names(model):
                    mw.col.models.add_field(
                        model, mw.col.models.new_field('Jlab-ListeningBack'))
                    model['qfmt'] += '<script>if ((audio=document.getElementsByClassName("subsearch__fetch")).length > 0) { audio[0].nextElementSibling.setAttribute("onclick", `document.getElementById("${audio[0].id}").play()`); audio[0].autoplay = true }</script>'
                    model['qfmt'] = model['qfmt'].replace('<p style="font-size:50%;color=#C4C4C4">Hover / tap on kanji to show furigana<p>',
                                                          '<p style="font-size:50%;color=#C4C4C4">Hover / tap on kanji to show furigana</p>')
                    model['afmt'] += '<script>if ((audio=document.getElementsByClassName("subsearch__fetch")).length > 0) { audio[0].nextElementSibling.setAttribute("onclick", `document.getElementById("${audio[0].id}").play()`); audio[0].autoplay = true }</script>'
                    logDebug(f"Updated {model.name} for 1.1")

        QueryOp(
            parent=self,
            op=lambda col: map(check_for_differing_model,
                               col.models.all_names_and_ids()),
            success=lambda r: 0
        ).run_in_background()
        self.populate_ui()
        self.search_term_edit.setFocus()

    def populate_ui(self):
        self.status_bar.hide()
        if not config['show_extended_filters']:
            self.toggle_filter_rows(True)
        self.populate_note_type_selection_combo()
        self.populate_selection_boxes()
        self.populate_current_profile_decks()
        self.window_state.restore()
        self.update_note_fields()

    def populate_note_type_selection_combo(self):
        self.note_type_selection_combo.clear()
        self.note_type_selection_combo.addItem(*NameId.none_type())
        for note_type in mw.col.models.all_names_and_ids():
            self.note_type_selection_combo.addItem(
                note_type.name, note_type.id)

    def populate_selection_boxes(self):
        self.jlpt_level[1].clear()
        self.sort[1].clear()
        self.wanikani_level[1].clear()
        self.category[1].clear()

        self.jlpt_level[1].addItems(["--", 'N5', 'N4', 'N3', 'N2', 'N1'])
        self.sort[1].addItems(['--', 'Shortness', 'Longness'])
        self.wanikani_level[1].addItem("--")
        self.wanikani_level[1].addItems(
            ['Level '+str(lvl+1) for lvl in range(60)])
        self.category[1].addItems(
            ['--', 'Anime', 'Drama', 'Games', 'Literature'])

    def populate_current_profile_decks(self):
        logDebug("Populating current profile decks...")
        self.current_profile_deck_combo.set_decks(sorted_decks_and_ids(mw.col))

    def toggle_filter_rows(self, no_config_overwrite=False):
        filter_widgets = (
            self.exact,
            self.jlpt_level[0], self.jlpt_level[1],
            self.wanikani_level[0], self.wanikani_level[1],
            self.category[0], self.category[1],
            self.sort[0], self.sort[1],
            self.min_length[0], self.min_length[1],
            self.max_length[0], self.max_length[1]
        )

        if not no_config_overwrite and config['show_extended_filters'] or no_config_overwrite and not config['show_extended_filters']:
            for widget in filter_widgets:
                widget.hide()

        else:
            for widget in filter_widgets:
                widget.show()

        if not no_config_overwrite:
            config['show_extended_filters'] = not config['show_extended_filters']
            config.write_config()

        self.filter_collapse.setToolTip(
            f'{"Hide" if config["show_extended_filters"] else "Show"} extended filters')
        self.filter_collapse.setText(
            '🞁' if config['show_extended_filters'] else '🞃')

    def update_note_fields(self):
        if self.note_type_selection_combo.currentData() != NameId.none_type().id and self.note_type_selection_combo.currentData() is not None:
            fields = mw.col.models.field_names(mw.col.models.get(
                self.note_type_selection_combo.currentData()))
            needed_fields = ['Audio', 'Expression',
                             'ID', 'Reading', 'English', 'Image']
            if config['import_source_info']:
                needed_fields.append('source_info')
            if config['jlab_format']:
                needed_fields += ['Jlab-Kanji', 'Jlab-KanjiSpaced', 'Jlab-Hiragana', 'Jlab-KanjiCloze', 'Jlab-Lemma', 'Jlab-HiraganaCloze', 'Jlab-Translation',
                                  'Jlab-DictionaryLookup', 'Jlab-Metadata', 'Jlab-Remarks', 'Other-Front', 'Jlab-ListeningFront', 'Jlab-ClozeFront', 'Jlab-ClozeBack']

            missing_fields = []
            for field in needed_fields:
                if field not in fields:
                    missing_fields.append(field)

            if missing_fields:
                self.note_fields.setText(
                    f"Note Type is missing fields:\n{', '.join(missing_fields)}. (Check preview if image is needed)")
                return self.note_fields.show()

        self.note_fields.hide()

    def update_notes_list(self):
        self.search_term_edit.setFocus()
        self.search_result_label.hide()
        if not self.search_term_edit.text():
            return

        # measure against double search
        if self.search_block:
            return
        self.search_block = True

        self.search_result_label.set_count(custom_text="Loading...")

        def on_load_finished(notes: list[dict]):
            if isinstance(notes, Exception):
                self.search_result_label.set_count(custom_text="Connection failed.")
                self.search_block = False
                # Build a more helpful message depending on error type
                if isinstance(notes, urlerror.HTTPError):
                    msg = f"Immersion Kit API error {notes.code}: {getattr(notes, 'reason', '') or 'HTTP error'}."
                elif isinstance(notes, urlerror.URLError):
                    msg = f"Network error: {getattr(notes, 'reason', '')}."
                else:
                    msg = f"Unexpected error: {notes}."
                msg += "\nTry unsetting min./max. length, check connection, or try again later."
                return showInfo(msg)

            limited_notes = notes[:config['notes_per_page']]

            self.note_list.set_notes(
                limited_notes,
                hide_fields=config['hidden_fields'],
                previewer=config['preview_on_right_side']
            )

            self.search_result_label.set_count(len(notes), config['notes_per_page'], len(limited_notes))
            self.page_prev.setEnabled(False)
            if len(notes) > config['notes_per_page']:
                self.page_skip.setEnabled(True)
            self.page = 1

            self.search_block = False

        QueryOp(
            parent=self,
            op=lambda c: note_getter.get_for("https://apiv2.immersionkit.com/search", self.search_term_edit.text(),
                                             extended_filters=[self.category[1].currentText(), self.sort[1].currentText(),
                                             [self.min_length[1].value(), self.max_length[1].value(
                                             )], self.jlpt_level[1].currentText(),
                self.wanikani_level[1].currentText(), self.exact.isChecked()]),
            success=on_load_finished,
        ).with_progress("Searching for cards...").run_in_background()

    def change_page(self, is_skip_page=True):
        # if the current page is 2 and npp 100, x:y = 100:200. If setting the npp to 50, x:y changes to 50:100.
        # We need the new page now. This however is based on the x:y. So we need to calculate the CURRENT x:y by npp, as easy as recalculating. (Easier said than done)
        # So, now we got the problem: recalculating the page based on x:y which is based on the page is impossible.
        # New example: We got the page 2, npp 100, x:y = 100:200. New setting: 200.
        # We transfer the page to the new setting and need to check we are not above limits.
        # To do this, we take the page, 2, the current x:y based on the new setting, 200:400, and ceil((all := 300)/200) = 2  ~~-> x:y = allp voilà we got the page.~~
        # Wait a sec, we got what we need. Just the check for upwards off-limit is missing.... why am i even doing this?
        # found out I managed to get the if else the exact same without noticing it

        # always the same... just can't get it right
        # page  | 1     | 2       | 3       | ...
        # x=100 | 0:100 | 100:200 | 200:300 | ...
        #       | [(page-1)*x] : [page*x]
        # x=100 | [(1-1)*100=0] : [1*100=100] | [(2-1)*100=100] : [2*100=200] ✔️ (Now it just gotta work)

        # First setting the page, afterwards it's the same for upward and downward
        cur_notes_len = len(note_getter.cur_note_list)

        if cur_notes_len <= (self.page-(0 if is_skip_page else 2))*config['notes_per_page']:  # note: before page set
            # set the last page based on the above example
            self.page = ceil(cur_notes_len/config['notes_per_page'])
        elif (self.page-(0 if is_skip_page else 2))*config['notes_per_page'] < 0:
            self.page = 1
        elif is_skip_page: 
            self.page += 1
        else:
            self.page -= 1

        page_start = (self.page-1)*config['notes_per_page']
        page_end = self.page*config['notes_per_page']
        
        logDebug(f"Page switch {self.page-(1 if is_skip_page else -1)} -> {self.page} ({page_start}:{page_end} in {cur_notes_len})")

        limited_notes = note_getter.cur_note_list[page_start : page_end]
        self.note_list.set_notes(
            limited_notes,
            hide_fields=config['hidden_fields'],
            previewer=config['preview_on_right_side']
        )
        self.search_result_label.set_count(
            cur_notes_len, config['notes_per_page'], len(limited_notes), self.page)

        self.page_prev.setEnabled(page_start > 0)
        self.page_skip.setEnabled(cur_notes_len-1 > page_end) # note: aims for the next page's start
        
        self.note_list.clear_selection()  # try to clear, seems not to work though
  

    def start_import(self):
        def _execute_import(self):
            logDebug('Beginning Import')

            # Get selected notes
            notes = self.note_list.selected_notes()
            logDebug(f'Importing {len(notes)} notes')

            results = []
            for note in notes:
                result = import_note(
                    model_id=self.note_type_selection_combo.currentData(),
                    note=note,
                    deck_id=self.current_profile_deck_combo.currentData()
                )
                results.append(result)

        def _finish_import(self):
            # Clear the selection here to be able to run in background
            self.note_list.clear_selection()
            self.status_bar.set_status(successes=results.count(ImportResult.success),
                                    dupes=results.count(ImportResult.dupe), 
                                    fails=results.count(ImportResult.fail))
            mw.reset()


        if len(self.note_list.selected_notes()) < 1:
            return self.status_bar.set_status(custom_text="No notes selected.")

        results = []

        QueryOp(
            parent=self,
            op=lambda c: _execute_import(self),
            success=lambda c: QTimer.singleShot(0, lambda: _finish_import(self)),
        ).with_progress("Importing...").run_in_background()
        

    def new_edit_win(self):
        if len(selected_notes := self.note_list.selected_notes()) > 0:
            self.status_bar.set_status(custom_text="Loading...")
            self._add_window_mgr.create_window(selected_notes[-1])
        else:
            self.status_bar.set_status(custom_text="No notes selected.")

    def done(self, result_code: int):
        self.window_state.save()
        return super().done(result_code)

######################################################################
# Entry point
######################################################################


def init():
    # init dialog
    d = mw._ani_main_dialog = MainDialog(parent=mw)
    # get AJT menu
    root_menu = menu_root_entry()
    # create a new menu item
    action = QAction('Search for Sub2Srs Cards...', root_menu)
    # set it to call show function when it's clicked
    qconnect(action.triggered, d.show)

    def on_finish(result):
        if result:
            showInfo(f"Successfully updated {0 if result == True else len(list(result))} notes. Jlab now works for them.")
        else:
            show_critical(
                "Not able to update. Please check if Kakasi is installed by opening the SubSearch window.")
    # and add it to the tools menu
    root_menu.addActions([action])
    # react to anki's state changes
    gui_hooks.profile_will_close.append(d.close)

    # check for not 1.2 converted cards
    def check_12(col):
        for model in col.models.all_names_and_ids():
            if model.name.startswith('SubCard-JlabConverted'):
                models_notes = col.models.nids(model.id)
                if len(models_notes) > 0:
                    example_note = col.get_note(models_notes[0])
                    if not example_note['Jlab-ListeningFront'].strip():
                        return 1
    gui_hooks.main_window_did_init.append(lambda: QueryOp(parent=mw, op=check_12, success=lambda r: 
        ask_user("Sub2Srs Search:\n\nPlease update your cards for Jlab Compatibility.\nThis is required for Jlab to work and will need kakasi added to SubSearch.\n\nIf you want to do this afterwards, you have gotten a new option 'Update Jlab cards...' in the menu.",
                lambda yes: QueryOp(parent=mw,
                op=note_getter.update_jlab_cards,
                success=on_finish).with_progress("Updating Jlab formatting...").run_in_background() if yes else 0) if r else 0).run_in_background())

    # check for kakasi
    if config["jlab_format"] and not path.exists(path.join(path.dirname(__file__), 'pykakasi', 'src', '__init__.py')):
        logDebug("Pykakasi not found, asking for add...")
        gui_hooks.main_window_did_init.append(lambda: ask_user("Sub2Srs Search:\n\nFor Jlab Format required pykakasi not found. Do you want to download it now?",
                                                               lambda yes: add_kakasi(note_getter.import_kakasi) if yes else 0))
    elif config["jlab_format"]:
        note_getter.import_kakasi(1)
