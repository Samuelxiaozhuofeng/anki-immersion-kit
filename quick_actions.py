from __future__ import annotations

import json
from os import path
from typing import Optional

from aqt import mw, gui_hooks
from aqt.qt import QAction, qconnect, QKeySequence
from aqt.utils import tooltip, showInfo
from aqt.operations import QueryOp

from . import note_getter
from .note_importer import import_note, ImportResult
from .common import LogDebug, NameId

logDebug = LogDebug()

import re


def _window_state_path() -> str:
    return path.join(path.dirname(__file__), 'user_files', 'window_state.json')


def _load_profile_state() -> dict:
    try:
        with open(_window_state_path(), encoding='utf8') as f:
            data = json.load(f)
        return data.get(mw.pm.name, {})
    except Exception:
        return {}


def _resolve_deck_id(deck_name: Optional[str]) -> int:
    try:
        if deck_name:
            for d in mw.col.decks.all_names_and_ids():
                if d.name == deck_name:
                    return d.id
        return mw.col.decks.current()['id']
    except Exception:
        return mw.col.decks.current()['id']


def _resolve_model_id(model_name: Optional[str]) -> int:
    try:
        if model_name:
            m = mw.col.models.by_name(model_name)
            if m:
                return m['id']
        return NameId.none_type().id
    except Exception:
        return NameId.none_type().id


def _filters_from_state(state: dict) -> list:
    # extended_filters = [category, sort, [min,max], jlpt, wanikani, exact]
    return [
        state.get('category', '--'),
        state.get('sort', '--'),
        [int(state.get('min_length', 0) or 0), int(state.get('max_length', 0) or 0)],
        state.get('jlpt_level', '--'),
        state.get('wanikani_level', '--'),
        bool(state.get('exact', False)),
    ]


def _selected_text_from_web(web) -> str:
    try:
        return (web.selectedText() or '').strip()
    except Exception:
        try:
            return (web.page().selectedText() or '').strip()
        except Exception:
            return ''


def _sanitize_term(term: str) -> str:
    """Remove bracketed readings like （おお） and similar pairs, then trim.
    Supports both ASCII and fullwidth brackets common in JP text.
    """
    if not term:
        return ''
    s = term
    patterns = [
        r"\([^)]*\)",           # ( ... )
        r"（[^）]*）",             # （ ... ）
        r"\[[^\]]*\]",         # [ ... ]
        r"【[^】]*】",             # 【 ... 】
        r"〈[^〉]*〉",             # 〈 ... 〉
        r"《[^》]*》",             # 《 ... 《
        r"「[^」]*」",             # 「 ... 」
        r"『[^』]*』",             # 『 ... 』
    ]
    for pat in patterns:
        s = re.sub(pat, '', s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _open_search_with_term(term: str):
    d = getattr(mw, '_ani_main_dialog', None)
    if not d:
        from .search_window import MainDialog
        d = mw._ani_main_dialog = MainDialog(parent=mw)
    d.open_with_term(term, auto_search=True)


def _quick_import_first(term: str):
    term = _sanitize_term((term or '').strip())
    if not term:
        return tooltip('No text selected.')

    state = _load_profile_state()
    deck_id = _resolve_deck_id(state.get('to_deck'))
    model_id = _resolve_model_id(state.get('note_type'))
    filters = _filters_from_state(state)

    def _op(_c):
        return note_getter.get_for("https://apiv2.immersionkit.com/search", term, extended_filters=filters)

    def _after_fetch(res):
        if isinstance(res, Exception):
            return showInfo(f"Sub2Srs: network/request error: {res}")
        if not res:
            return tooltip('No results found.')
        first = res[0]

        def _do_import(_c2):
            return import_note(model_id=model_id, note=first, deck_id=deck_id)

        def _after_import(result: ImportResult):
            if result == ImportResult.success:
                tooltip('Imported first result.')
                mw.reset()
            elif result == ImportResult.dupe:
                tooltip('Skipped duplicate card.')
            else:
                showInfo('Import failed. Check network/media download.')

        QueryOp(parent=mw, op=_do_import, success=_after_import).with_progress('Sub2Srs: importing...').run_in_background()

    QueryOp(parent=mw, op=_op, success=_after_fetch).with_progress('Sub2Srs: searching...').run_in_background()


def init():
    def on_context_menu(web, menu):
        # Limit to reviewer webview when possible
        try:
            if getattr(mw, 'reviewer', None) and web is not mw.reviewer.web:
                return
        except Exception:
            pass

        text = _selected_text_from_web(web)
        stext = _sanitize_term(text)
        if not stext:
            return

        act_search = QAction('Sub2Srs: Search with selection', menu)
        qconnect(act_search.triggered, lambda _=False, t=stext: _open_search_with_term(t))
        menu.addAction(act_search)

        act_quick = QAction('Sub2Srs: Quick import first result', menu)
        qconnect(act_quick.triggered, lambda _=False, t=stext: _quick_import_first(t))
        menu.addAction(act_quick)

    gui_hooks.webview_will_show_context_menu.append(on_context_menu)

    # Global shortcut: Ctrl+Shift+U to search with current reviewer selection
    def _shortcut_lookup():
        rev = getattr(mw, 'reviewer', None)
        web = getattr(rev, 'web', None)
        if not web:
            return tooltip('Not in Reviewer.')
        text = _selected_text_from_web(web)
        stext = _sanitize_term(text)
        if not stext:
            return tooltip('No text selected.')
        _open_search_with_term(stext)

    if not hasattr(mw, '_subsearch_lookup_action'):
        act = QAction('Sub2Srs: Lookup selection', mw)
        act.setShortcut(QKeySequence('Ctrl+Shift+U'))
        qconnect(act.triggered, lambda _=False: _shortcut_lookup())
        mw.addAction(act)
        mw._subsearch_lookup_action = act
