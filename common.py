# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import os
import zipfile
import urllib.request
from typing import Optional, TextIO
from typing import NamedTuple

from anki.collection import Collection

from aqt import mw, gui_hooks
from aqt.utils import tooltip, showCritical
from aqt.operations import QueryOp

from .config import config

ADDON_NAME = 'SubSearch'


class LogDebug:
    _logfile: Optional[TextIO] = None
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        gui_hooks.profile_will_close.append(self.close)

    def write(self, msg: str) -> None:
        print('SubSearch:', str(msg))
        if not config['enable_debug_log']:
            return
        if not self._logfile:
            path = os.path.join(mw.pm.base, 'subsearch_debug.log')
            print(f'SubSearch: opening log file "{path}"')
            # clear before writing to not have a large file somewhen
            open(path, 'w').close()
            self._logfile = open(path, 'a')
        self._logfile.write(str(msg) + '\n')
        self._logfile.flush()

    def __call__(self, *args, **kwargs):
        return self.write(*args, **kwargs)

    def get_contents(self):
        if not self._logfile:
            return ""
        with open(self._logfile.name, 'r') as lf:
            return lf.read()

    def close(self):
        if self._logfile and not self._logfile.closed:
            self.write("Closing debug log.")
            self._logfile = self._logfile.close()


class NameId(NamedTuple):
    name: str
    id: int

    @classmethod
    def none_type(cls) -> 'NameId':
        return cls('None (create new if needed)', -1)


def sorted_decks_and_ids(col: Collection) -> list[NameId]:
    return sorted(NameId(deck.name, deck.id) for deck in col.decks.all_names_and_ids())


def add_kakasi(callback):
    logdebug = LogDebug()
    def download_pkg(links):
        for link in links:
            pkg_name = link.split("/")[4]
            logdebug("Getting package "+pkg_name)

            try:
                content = urllib.request.urlopen(link)
            except IOError: 
                return [0, pkg_name]

            def join_zips_files(dir, match, out, pkg_name):
                with zipfile.ZipFile(dir, 'r') as zip:
                    use_out = out
                    for member in zip.namelist(): # https://stackoverflow.com/a/4917469
                        for item in match:
                            if item in member:
                                logdebug("Extracting "+member)

                                filename = os.path.basename(member)
                                # always update extract path as for files in a folder with
                                # subfolders might come after subfolders
                                if member.split(item)[1].startswith('pykakasi/'):
                                    use_out = out
                                else:
                                    use_out = os.path.join(out, os.path.dirname(member.split(item)[1]))
                                # create directory
                                if not filename and not member.split(item)[1].startswith('pykakasi/'):
                                    os.makedirs(os.path.join(out, member.split(item)[1]), exist_ok=True)
                                    continue
                                elif not filename and member.split(item)[1].startswith('pykakasi/'):
                                    continue
                                
                                source = zip.open(member)
                                if not os.path.exists(os.path.join(use_out, filename)):
                                    open(os.path.join(use_out, filename), 'x').close()
                                target = open(os.path.join(use_out, filename), 'bw')
                                
                                with source, target:
                                    if pkg_name in ["jaconv", "deprecated", "pykakasi"]:  # import updated for local use
                                        target.write(source.read().replace(b"\nimport jaconv", b"\nfrom .. import jaconv").replace(b'from deprecated', b'from ..deprecated').replace(b"\nimport wrapt", b"\nfrom .. import wrapt"))
                                    else:
                                        target.write(source.read())

                                continue

            open(os.path.join(os.path.dirname(__file__), pkg_name+'.zip'), 'b+w').write(content.read())
            os.makedirs(os.path.join(os.path.dirname(__file__), os.path.join(pkg_name, "src") if pkg_name == "pykakasi" else os.path.join('pykakasi', pkg_name)), exist_ok=True)
            join_zips_files(os.path.join(os.path.dirname(__file__), pkg_name+'.zip'), [f"/{pkg_name}/" if pkg_name != "pykakasi" else '/src/', "COPYING", "LICENSE", "kakasidict.py"], os.path.join(os.path.dirname(__file__), os.path.join(pkg_name, "src") if pkg_name == "pykakasi" else os.path.join('pykakasi', pkg_name)), pkg_name)
            os.remove(os.path.join(os.path.dirname(__file__), pkg_name+'.zip'))
            
        return [1, None]

    def on_finish(result: dict):
        if result[0]:
            logdebug("Generating kakasi's dictionaries")
            # from pykakasi/setup.py
            from .pykakasi.src.kakasidict import Genkanwadict
            kanwa = Genkanwadict()
            kanwa.generate_dictionaries(os.path.join(os.path.dirname(__file__), "pykakasi", "src", "data"))

            logdebug("Successfully added pykakasi and it's subdependencies")
            tooltip("Successfully added pykakasi")
            return callback(1)
        logdebug(f"Adding {result[1]} failed. Cause will most probably be disconnected internet.")
        showCritical(f"Unable to add dependency {result[1] if result[1] == 'pykakasi' else f'of pykakasi, {result[1]},'} for SubSearch. Pykakasi is used for Jlab formatting.\nIf you want to use the Jlab Format, please check your internet connection and try again.")
        callback(0)

    links = ["https://codeberg.org/miurahr/pykakasi/archive/releases/2.x.zip", "https://github.com/ikegami-yukino/jaconv/archive/refs/heads/master.zip", "https://github.com/tantale/deprecated/archive/refs/heads/master.zip", "https://github.com/GrahamDumpleton/wrapt/archive/refs/heads/master.zip"]
    QueryOp(parent=mw, op=lambda c: download_pkg(links), success=on_finish).with_progress("Adding pykakasi to SubSearch...").run_in_background()
