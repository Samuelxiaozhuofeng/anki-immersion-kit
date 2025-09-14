# Copyright: (C) 2021 Ren Tatsumoto <tatsu at autistici.org> and 2023 FileX <filex.stuff@proton.me>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html


ADDON_SERIES = 'Sub2Srs Search'
DIALOG_NAME = 'About'
SOURCE_LINK = 'https://codeberg.org/FileX/SubSearch'
FORUM_LINK = 'https://forums.ankiweb.net/t/sub2srs-search-official-thread/38034'
ANKI_LINK = 'https://ankiweb.net/shared/info/717309388'
CROPRO_LINK = 'https://github.com/Ajatt-Tools/cropro'

BUTTON_HEIGHT = 32
ICON_SIDE_LEN = 18

STYLES = '''
<style>
a { color: SteelBlue; }
h2 { text-align: center; }
body { margin: 0 4px 0; }
</style>
'''

ABOUT_MSG = f'''
{STYLES}
<h2>Sub2Srs Search</h2>
<p>
    Thanks for using the addon!<br><br>

    If you need some help, maybe take a look at <a href="{SOURCE_LINK}/src/branch/main/README.md">this.</a><br><br>

    On top, here are some useful links for you:
    
    <br><br>- <a href="{SOURCE_LINK}">Source Code</a>
    <br>- <a href="{SOURCE_LINK}/issues/new">Open a new issue</a>
    <br>- <a href="{FORUM_LINK}">Addon's Anki Forum Page</a>
    <br>- <a href="{ANKI_LINK}">Anki Addons Page</a>
    
    <br><br>This addon is based on <a href="{CROPRO_LINK}">CroPro</a>
</p>
'''
