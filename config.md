## SubSearch

**Anki needs to be restarted after changing the config.**

### List of options:

- `notes_per_page` | how many search result to display on one page
- `enable_debug_log` | print debug information to `stdout` and to a log file.<br/>
Location: `~/.local/share/Anki2/subsearch_debug.log` (GNU systems) or `%APPDATA%/Anki2/subsearch_debug.log` (Windows).
- `hidden_fields` | contents of fields that contain these keywords won't be shown.
- `skip_duplicates` | Skips cards, which are already existent in the collection
- `jlab_format` | Formats cards in a way, so they are compatible to Jlab's Systems and thus can be used with them
- `import_source_info` | If enabled, adds a field regarding name, episode or similar
- `preview_on_right_side` | Regarding the note preview in the search window
- `show_extended_filters` | Shows the big list of filters on top of the search window. Can also be controlled with the arrow on the left of the search bar
- `fetch_anki_card_media` | If enabled, the the media content shown on cards will be loaded from the internet, instead of from local storage.<br/>
Positive: Saves storage for you and anki.<br/>
Negative: Card reviewing will only work if you have an internet connection.
- `show_help_buttons` | Hides or shows all those help buttons in the windows of SubSearch
- `call_add_cards_hook` | Calls the `add_cards_did_add_note` hook as soon as a note is imported through the main search window. <br/>
For addon evaluation purposes.
