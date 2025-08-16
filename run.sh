ROOT_DIR="/home/garry/documents/ppt/annual_reports"
source $ROOT_DIR/.venv/bin/activate

set -o allexport
source "$ROOT_DIR/.env"
set +o allexport

if [ ! -v 1 ]; then
	echo "No program specified."
elif [ "$1" = "main" ]; then
	"$ROOT_DIR/src/main.py" "${@:2}"
elif [ "$1" = "convert" ]; then
	"$ROOT_DIR/src/convert_format.py" "${@:2}"
elif [ "$1" = "setup" ]; then
	"$ROOT_DIR/src/setup.py" "${@:2}"
elif [ "$1" = "merge" ]; then
	export FORMAT_CSV="categories.csv"
	export FORMAT_JSON="categories.json"
	export META_END=1
	"$ROOT_DIR/src/convert_format.py"
	MERGE_JSON="/home/garry/documents/ppt/annual_reports/categories.json"
	"$ROOT_DIR/src/merge.py"

else
	"$ROOT_DIR/$1" "${@:2}"
fi
