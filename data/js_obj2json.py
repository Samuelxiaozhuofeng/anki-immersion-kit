# _next/static/chunks/ srch

import re
import json

def js_obj2json(js_text):
    js_text = js_text.strip()
    if js_text.startswith('var d ='):
        js_text = js_text[js_text.index('=') + 1:].strip()
    # Keys
    js_text = re.sub(r'\'(\S+)\':', r'\1:', js_text)
    js_text = re.sub(r'(\S+):', r'"\1":', js_text)
    # Values
    js_text = re.sub(r"(:\s?)'(.*?)',", r'\1"\2",', js_text)
    js_text = re.sub(r'\\\'', "'", js_text)
    # Arrays
    js_text = re.sub(r'(\[[\s\S]*?\])', lambda x: convert_array_strings(x.group(0)), js_text)
    # Extra comma
    js_text = re.sub(r',(\s*[}\]])', r'\1', js_text)
    return js_text

def convert_array_strings(arr_str):
    elements = arr_str[1:-1].split(',')

    elements = [re.sub(r"'([^']+)'", r'"\1"', element.strip()) for element in elements]

    # Rebuild the array with the modified elements
    return f"[{', '.join(elements)}]"

with open(".ignore.txt", "r", encoding="utf-8") as out:
    js_content = out.read()

json_text = js_obj2json(js_content)

try:
    data = json.loads(json_text)
except Exception as e:
    print("Failed to parse JSON after conversion.")
    print(e)
    exit(1)

slug_to_title = {slug: entry["title"] for slug, entry in data.items() if "title" in entry}

output_filename = "titles.json"
with open(output_filename, "w", encoding="utf-8") as out:
    json.dump(slug_to_title, out, indent=4, ensure_ascii=False)

print("Title generation finished")
