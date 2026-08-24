#!/bin/sh
set -e

cp /run/secrets/oauth-token/token.json /tmp/quiron-token.json
chmod 600 /tmp/quiron-token.json

exec python run.py
