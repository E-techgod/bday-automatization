#!/bin/sh
set -e

TOKEN_PATH="${GOOGLE_OAUTH_TOKEN_FILE:-/tmp/quiron-token.json}"

rm -f "$TOKEN_PATH"
umask 077
cat /run/secrets/oauth-token/token.json > "$TOKEN_PATH"

test -w "$TOKEN_PATH"

exec python run.py
