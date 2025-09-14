# Copyright: Ren Tatsumoto <tatsu at autistici.org> and FileX <filex.stuff@proton.me>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from collections.abc import Iterable
from enum import Enum, auto
from typing import NamedTuple
from urllib import request, parse

from anki.models import NoteType
from anki.notes import Note
from anki.utils import join_fields
from aqt import gui_hooks
from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo, show_info

from .common import NameId
from .config import config


class ImportResult(Enum):
    success = auto()
    dupe = auto()
    fail = auto()


class FileInfo(NamedTuple):
    name: str
    path: str


def files_in_note(note: Note) -> Iterable[FileInfo]:
    """
    Returns FileInfo for every file referenced by other_note.
    Skips missing files.
    """
    for file_ref in note.col.media.files_in_str(note.mid, join_fields(note.fields)):
        if os.path.exists(file_path := os.path.join(note.col.media.dir(), file_ref)):
            yield FileInfo(file_ref, file_path)


def download_media_files(fetched_note: dict) -> bool:
    print(fetched_note['needed_media'])
    for url in fetched_note['needed_media']:
        try:
            content = request.urlopen(parse.quote(url, safe=':/%'))
        except IOError:
            showInfo("You need an active internet connection to import a card.")
            return False

        if os.path.exists(os.path.join(mw.col.media.dir(), url.split('/')[-1])):
            show_info(url.split('.')[-1] + " already exists. Please make sure it is correct")
        else: 
            open(os.path.join(mw.col.media.dir(), url.split('/')[-1]), 'b+w').write(content.read())

    return True


def remove_media_files(new_note: Note):
    """
    If the user pressed the Edit button, but then canceled the import operation,
    the collection will contain unused files that need to be trashed.
    But if the same file(s) are referenced by another note, they shouldn't be trashed.
    """
    assert (new_note.col == mw.col.weakref())
    new_note.col.media.trash_files([
        file.name
        for file in files_in_note(new_note)
        if not new_note.col.find_cards(file.name)
    ])


def get_matching_model(model_id: int, note: dict) -> NoteType:
    if model_id != NameId.none_type().id:
        # use existing note type (even if its name or fields are different)
        return mw.col.models.get(model_id)
    else:
        # find a model which has the required fields, else create a new one
        models = mw.col.models.all()

        # remove keys important for backend or unwanted
        note_keys = list(note.keys())
        note_keys.remove('needed_media')
        if not config['import_source_info']:
            note_keys.remove('source_info')

        matching_model = None

        # match for field names, regardless of order
        for model in models:
            if sorted(mw.col.models.field_names(model)) == sorted(note_keys):
                matching_model = model
                break

        if not matching_model:
            # create new model with Jlab template
            matching_model = mw.col.models.new('SubCard-JlabConverted' if config['jlab_format'] else 'SubCard')
            for key in note_keys:
                mw.col.models.add_field(matching_model, mw.col.models.new_field(key))

            #           jlab format?
            # SubSearch -- SubCard-JlabConverted -- Jlab-ListeningCard -- Normal Fields + Jlab Fields
            #           |- SubCard -- SubCard-Front-Back -- Normal Fields

            matching_model['css'] = '''.card {
 font-family: arial;
 font-size: 20px;
 max-width: 800px;
 text-align: center;
 margin-left: auto;
 margin-right: auto;
 color: black;
 background-color: white;
}
.kanjipopup {
 font-family: arial;
 font-size: 20px;
 text-align: center;
 color: black;
 background-color: white;
}
.kanjipopup ruby rt { visibility: hidden; }
.kanjipopup ruby:active rt { visibility: visible; }
.kanjipopup ruby:hover rt { visibility: visible; }'''

            mm_template = mw.col.models.new_template('Jlab-ListeningCard' if config['jlab_format'] else 'SubCard-Front-Back')
            mm_template['qfmt'] = ('{{Audio}}<br>'
                                   f'{"{{Image}}<br><br>" if "Image" in note_keys else ""}'
                                   '<div class="kanjipopup help expression-field">{{furigana:Reading}}</div>'
                                   '<p style="font-size:50%;color=#C4C4C4">Hover / tap on kanji to show furigana</p>'
                                   '<script>if ((audio=document.getElementsByClassName("subsearch__fetch")).length > 0) { audio[0].nextElementSibling.setAttribute("onclick", `document.getElementById("${audio[0].id}").play()`); audio[0].autoplay = true }</script>')
            mm_template['afmt'] = (('{{Jlab-Remarks}}<br><br>' if config['jlab_format'] else '') +
                                   '<div class="kanjipopup expression-field">{{furigana:Reading}}</div>'
                                   '<div class=help>{{furigana:Jlab-KanjiCloze}}</div><br>' if config['jlab_format'] else ''
                                   '<font color = #C4C4C4>Translation:</font> {{English}}<br>'
                                   '<script>if ((audio=document.getElementsByClassName("subsearch__fetch")).length > 0) { audio[0].nextElementSibling.setAttribute("onclick", `document.getElementById("${audio[0].id}").play()`); audio[0].autoplay = true }</script>')

            mw.col.models.add_template(matching_model, mm_template)
            matching_model['id'] = 0

            mw.col.models.add_dict(matching_model)
        return matching_model


def import_note(model_id: int, note: dict, deck_id: int) -> ImportResult:
    matching_model = get_matching_model(model_id, note)
    new_note = Note(mw.col, matching_model)
    new_note.note_type()['did'] = deck_id
    
    for key in new_note.keys():
        if key != 'source_info' or config['import_source_info']:
            try:
                new_note[key] = note[key]
            except KeyError:
                pass

    # check if note is dupe of existing one
    if config['skip_duplicates'] and new_note.dupeOrEmpty():
        return ImportResult.dupe

    if not download_media_files(note):
        return ImportResult.fail
    
    mw.col.addNote(new_note)  # new_note has changed its id

    if config['call_add_cards_hook']:
        gui_hooks.add_cards_did_add_note(new_note)

    return ImportResult.success
