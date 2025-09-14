# Copyright: Ren Tatsumoto <tatsu at autistici.org> and FileX <filex.stuff@proton.me>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import re

SOUND_TAG_REGEX = re.compile(r'\[sound:([^\[\]]+?\.[^\[\]]+?)]')
IMAGE_TAG_REGEX = re.compile(r'<img [^<>]*src="([^"]+)"[^<>]*>')
# everything except names containing " is acceptable as image name


def unquote_filename(filename: list[str]) -> str:
    import urllib.parse

    return '' if not filename else urllib.parse.unquote(filename[0])


def find_sound(html: str) -> str:
    """Return the audio file referenced in html."""
    return unquote_filename(re.findall(SOUND_TAG_REGEX, html))


def find_image(html: str) -> str:
    """Return the image referenced in html."""
    return unquote_filename(re.findall(IMAGE_TAG_REGEX, html))


def find_all_media(html: str) -> list[str]:
    """Return a list of image and audio files referenced in html."""
    return [find_image(html), find_sound(html)]
