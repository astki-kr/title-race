#!/bin/sh
# Bump the app version so installed home-screen copies notice the update.
# Keeps APP_VERSION in index.html and version.json in lockstep.
#   ./bump.sh && git commit -am "..." && git push
set -e
V=$(date +%Y.%m.%d.%H%M)
sed -i '' "s/^const APP_VERSION = \"[^\"]*\";/const APP_VERSION = \"$V\";/" index.html
printf '{ "version": "%s" }\n' "$V" > version.json
grep -q "const APP_VERSION = \"$V\";" index.html || { echo "FAILED to stamp index.html"; exit 1; }
echo "bumped to $V"
