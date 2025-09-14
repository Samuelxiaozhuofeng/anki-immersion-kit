import json
from urllib import request, parse, error
import re
import os

from aqt import mw
from aqt.utils import tooltip

space_pattern = re.compile(r'\s+')
multi_space_pattern = re.compile(r'\s\s+')

kakasi = False
# Is being called upon anki startup from searchwindows init
def import_kakasi(r):
    if r and config["jlab_format"]:
        from .pykakasi import src as pykakasi
        global kakasi
        kakasi = pykakasi.Kakasi()

from .common import LogDebug
from .config import config

logDebug = LogDebug()

cur_note_list = []


def get_for(url, term: str, *, extended_filters: list[str, str, list[int, int], str, str, bool]) -> list[dict] or IOError:
    """extended_filters = [category (0), sort (1), length_border (2), jlpt (3), wanikani (4), exact_match (5)]"""
    # build URL out of secured values
    if term: 
        term = parse.quote(term)
    if extended_filters[0]: 
        category = extended_filters[0].lower()
    if extended_filters[1]: 
        if extended_filters[1] == 'Shortness':
            sort = "sentence_length:asc"
        elif extended_filters[1] == "Longness":
            sort = "sentence_length:desc"
    if extended_filters[2]:
        min_len = str(extended_filters[2][0])
        max_len = str(extended_filters[2][1])
    if extended_filters[3] and extended_filters[3] != "--": 
        jlpt = extended_filters[3][1:]
    if extended_filters[4] and extended_filters[4] != "--": 
        wanikani = extended_filters[4][6:]
        
    # q: String (Search term)
    # index:
    # exactMatch: small boolean
    # limit: Number
    # sort: sentence_length:asc|desc 
    encoded_url = (f'{url}?q={term}{"" if extended_filters[0] == "--" else ("&category=" + category)}'
                   f'{"" if extended_filters[1] == "--" else ("&sort=" + sort)}'
                   f'{"" if not extended_filters[2][0] else ("&min_length=" + min_len)}{"" if not extended_filters[2][1] else ("&max_length=" + max_len)}'
                   f'{"" if extended_filters[3] == "--" else ("&jlpt=" + jlpt)}{"" if extended_filters[4] == "--" else ("&wk=" + wanikani)}'
                   f'&exactMatch={str(extended_filters[5]).lower()}')

    logDebug(f'Getting card data for - {term}, {extended_filters[0]}, {extended_filters[1]}, {extended_filters[2]}, '
             f'{extended_filters[3]}, {extended_filters[4]}, {extended_filters[5]} ({encoded_url})')
    try:
        req = request.Request(
            encoded_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) AnkiAddon/1.0 Safari/537.36",
                "Accept": "application/json",
            },
        )
        with request.urlopen(req, timeout=10) as resp:
            response = resp.read()
        result = json.loads(response)
    except error.HTTPError as err:
        logDebug(f"HTTPError while fetching data: {err.code} {getattr(err, 'reason', '')}")
        return err
    except error.URLError as err:
        logDebug(f"URLError while fetching data: {getattr(err, 'reason', err)}")
        return err
    except IOError as err:
        logDebug(f"IOError while fetching data: {err}")
        return err
    except Exception as err:
        logDebug(f"Unexpected error while fetching data: {err}")
        return err

    global cur_note_list
    cur_note_list = []

    logDebug('Formatting fetched card data')

    # build up note dict. Simplified and no note, so it is easier to handle and not as big as a note
    for card in result['examples']:
        new_note = {
            'Expression': card['sentence'],
            'ID': card['id'],
            'Reading': card['sentence_with_furigana'],
            'English': card['translation'],
            'source_info': f'{card["title"]}',
            'needed_media': []
        }

        card_category = next((prop for prop, details in result['deck_count'].items() if card['title'] in details), None)
        with open(os.path.join(os.path.dirname(__file__), "data", "titles.json"), 
                "r", 
                encoding="utf-8") as out:
            real_title = json.loads(out.read())
            
            if not card["title"] in real_title:
                tooltip("The database seems outdated. Please report this to the developer.\n(Title for "+card["title"]+" is missing)")
                continue
            real_title = real_title[card['title']]

        media_base_path = f"https://us-southeast-1.linodeobjects.com/immersionkit/media/{card_category}/{real_title}/media/"

        # UI and functionality combination
        if config['fetch_anki_card_media']:
            new_note["Audio"] = f'''<audio id="subsearch_{card["id"].replace('"', "'") +"."+ card["sound"].split(".")[-1]}_player" class="subsearch__fetch" src="{media_base_path + card["sound"]}"></audio>
[sound:{media_base_path + card["sound"]}]'''
        else:
            new_note['Audio'] = f'[sound:{card["sound"]}]'
            new_note['needed_media'].append(media_base_path+card['sound'])

        # if card has no image don't add one
        # also replace " with ' against image destruction
        if 'image' in card and config['fetch_anki_card_media']:
            new_note['Image'] = '<img src="'+media_base_path + card["image"]+'"/>'
        elif 'image' in card:
            new_note['Image'] = '<img src="'+card["image"] +'"/>'
            new_note['needed_media'].append(media_base_path +card['image'])

        if config['jlab_format'] and kakasi:
            kakasi_conv = kakasi.convert(card['sentence'])
            # jlab takes the cloze position by splitting the string at spaces
            # "  " = wanted_position + 1, if you say it programmatically
            new_note['Jlab-Kanji'] = re.sub(multi_space_pattern, ' ', card['sentence'])
            new_note['Jlab-KanjiSpaced'] = re.sub(multi_space_pattern, ' ', " ".join(''.join(e for e in word["orig"] if e.isalnum() or e in ['[',']']) for word in kakasi_conv).replace("]", " ]"))
            new_note['Jlab-Hiragana'] = re.sub(multi_space_pattern, ' ', " ".join(''.join(e for e in word["hira"] if e.isalnum() or e in ['[',']']) for word in kakasi_conv).replace("]", " ]"))
            new_note['Jlab-KanjiCloze'] = new_note["Jlab-KanjiSpaced"]
            # try replacing the searched word with it's deinflected form provided by the api
            # not yet got any better method for this
            new_note['Jlab-Lemma'] = new_note["Jlab-KanjiSpaced"] if len(result["dictionary"]) == 0 or len(result["dictionary"][0]) == 0 or result["dictionary"][0][0]["headword"] == parse.unquote(term) else new_note["Jlab-KanjiSpaced"].replace(card["word_list"][card["word_index"][0]], result["dictionary"][0][0]['headword'])
            new_note['Jlab-HiraganaCloze'] = new_note["Jlab-Hiragana"]
            new_note['Jlab-Translation'] = card['translation']
            new_note['Jlab-DictionaryLookup'] = ''
            new_note['Jlab-Metadata'] = ''
            new_note['Jlab-Remarks'] = ''
            new_note['Other-Front'] = new_note["Jlab-KanjiCloze"]
            # surprise, jlab is not needed.. (wasted a lot of hours on this). Jlab needs only the hiragana cloze and kanji matching each other
            # shown roumaji are converted by them and displayed
            new_note['Jlab-ListeningFront'] = re.sub(multi_space_pattern, ' ', " ".join(''.join(e for e in word["hepburn"] if e.isalnum() or e in ['[',']']) for word in kakasi_conv).replace("]", " ]"))
            new_note['Jlab-ListeningBack'] = new_note['Jlab-ListeningFront']
            new_note['Jlab-ClozeFront'] = new_note['Jlab-ListeningFront']
            new_note['Jlab-ClozeBack'] = new_note['Jlab-ListeningFront']

        cur_note_list.append(new_note)

    return cur_note_list
