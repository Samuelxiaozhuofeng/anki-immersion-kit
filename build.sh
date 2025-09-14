#!/bin/bash
# Copyright: Ren Tatsumoto <tatsu at autistici.org> and FileX <filex.stuff at proton.me>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

readonly addon_name=sub2srs_search
readonly manifest=manifest.json
readonly root_dir=$(git rev-parse --show-toplevel)
readonly branch=$(git branch --show-current)
readonly zip_name=${addon_name}_${branch}.ankiaddon
read -p "Target (ankiweb/aw/OTHER): " target
read -p "Once ready to run title generation press enter:"
export root_dir branch

cd ./data
python3 ./js_obj2json.py
cd ../

git_archive() {
	if [[ $target != ankiweb && $target != aw ]]; then
		# https://addon-docs.ankiweb.net/sharing.html#sharing-outside-ankiweb
		# If you wish to distribute .ankiaddon files outside of AnkiWeb,
		# your add-on folder needs to contain a 'manifest.json' file.
		echo "Creating $manifest"
		{
			echo '{'
			echo -e '\t"package": "SubSearch",'
			echo -e '\t"name": "Sub2Srs Search",'
			echo -e "\t\"mod\": $(date -u '+%s')"
			echo '}'
		} >"$manifest"
		git archive "$branch" --format=zip --output "$zip_name" --add-file="$manifest"
	else
		git archive "$branch" --format=zip --output "$zip_name"
	fi
}

cd -- "$root_dir" || exit 1
rm -- ./"$zip_name" 2>/dev/null

git_archive

# shellcheck disable=SC2016
git submodule foreach 'git archive HEAD --prefix=$path/ --format=zip --output "$root_dir/${path}_${branch}.zip"'

zipmerge ./"$zip_name" ./*.zip
rm -- ./*.zip ./"$manifest" 2>/dev/null

echo Generation finished
