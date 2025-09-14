# Copyright: Ren Tatsumoto <tatsu at autistici.org> and FileX <filex.stuff@proton.me>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import base64
import os.path
from typing import Optional
from urllib.parse import quote
import re

from anki.utils import html_to_text_line
from aqt import mw
from aqt.qt import *
from aqt.webview import AnkiWebView

from .subsearch_ajt.media import find_sound, find_image
from .common import LogDebug

logDebug = LogDebug()

WEB_DIR = os.path.join(os.path.dirname(__file__), 'web')
HTTP_REGEX = re.compile(r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))")


def get_previewer_html() -> str:
    with open(os.path.join(WEB_DIR, 'previewer.html'), encoding='utf8') as f:
        return f.read()


def encode(s_bytes):
    return base64.b64encode(s_bytes).decode("ascii")


def filetype(file: str):
    return os.path.splitext(file)[-1]


class NotePreviewer(AnkiWebView):
    """Previews a note in a Form Layout using a webview."""
    _css_relpath = f"/_addons/{mw.addonManager.addonFromModule(__name__)}/web/previewer.css"

    mw.addonManager.setWebExports(__name__, r"(img|web)/.*\.(js|css|html|png|svg)")

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self._note_media_dir: Optional[str] = None
        self.set_title("Note previewer")
        self.disable_zoom()
        self.setProperty("url", QUrl("about:blank"))
        self.setMinimumSize(200, 280)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def load_note(self, note: dict):
        rows: list[str] = []
        for field_name, field_content in note.items():
            if field_name not in ['needed_media']:
                rows.append(
                    f'<div class="name">{field_name}</div>'
                    '<div class="content">'+
                    self._create_html_row_for_field(field_content, note)+'</div>'
                )
        self.stdHtml(
            get_previewer_html().replace('<!--CONTENT-->', ''.join(rows)),
            js=[],
            css=[self._css_relpath, ]
        )

    def _create_html_row_for_field(self, field_content: str, note) -> str:
        """Creates a row for the previewer showing the current note's field."""
        markup = []
        url = []
        
        # use quote for frontend and unquoted for backend.
        # this way, front end isn't being destroyed and backend still works
        if audio_name := find_sound(field_content):
            print(note['needed_media'])
            markup.append(f"""<div class="subsearch__audio_list">
    <audio preload="auto" id="subsearch_{quote(audio_name, safe=":/%")}_player" src="{quote(audio_name if len(note['needed_media']) == 0 else note['needed_media'][0], safe=":/%")}"></audio>
    <button class="subsearch__play_button" title="Play-Button for {audio_name}" onclick="(audio=document.getElementById('subsearch_{quote(audio_name, safe=":/%")}_player')).paused ? audio.play() : (audio.currentTime = 0)"></button>
</div>
""")
            logDebug("Audio added, "+audio_name+('' if len(note["needed_media"]) == 0 else ", URL "+quote(note["needed_media"][0], safe=":/%")))

        elif image_name := find_image(field_content):
            if re.findall(HTTP_REGEX, image_name):
                markup.append(f'<div class="subsearch__image_list">'
                              f'<img alt="image:{image_name}" '
                              f'src="{image_name}"/></div>')
                logDebug("Added image in fetch mode, "+image_name)
            else:
                markup.append(f'<div class="subsearch__image_list">'
                              f'<img alt="image:{image_name}" '
                              f'src="{quote(note["needed_media"][1], safe=":/%")}"/></div>')
                logDebug("Image added, "+image_name+", URL "+quote(note["needed_media"][1], safe=":/%"))

        elif text := html_to_text_line(field_content):  # use elif to not add image or audio caption
            markup.append(f'<div class="subsearch__text_item">{text}</div>')

        return ''.join(markup)
