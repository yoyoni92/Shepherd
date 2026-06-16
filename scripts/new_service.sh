#!/usr/bin/env bash
# Scaffold a new Python service from templates/python-service.
set -euo pipefail

NAME="${1:?usage: scripts/new_service.sh <service-name>}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/services/$NAME"

if [ -e "$DEST" ]; then
  echo "already exists: $DEST" >&2
  exit 1
fi

mkdir -p "$ROOT/services"
cp -r "$ROOT/templates/python-service" "$DEST"

# render __NAME__ token in file contents
find "$DEST" -type f -print0 | xargs -0 perl -i -pe "s/__NAME__/$NAME/g"

# strip .tmpl suffixes
find "$DEST" -type f -name '*.tmpl' | while read -r f; do
  mv "$f" "${f%.tmpl}"
done

echo "created service: services/$NAME"
echo "next: make install SVC=services/$NAME && make test SVC=services/$NAME"
