#!/usr/bin/env bash
set -e

# Environment variables needed: NGROK(name of ngrok container), $BOTID (id of telegram bot)
# Set telegram webhook to public_url
export PUBLIC_URL=$(curl $NGROK:4040/api/tunnels | jq '[.tunnels | to_entries[] | {"value": .value.public_url}] | map(.value) | sort_by(length) | .[1]' | cut -d '"' -f2)
echo "fastapi server public url: $PUBLIC_URL"

curl -X POST -H "Content-Type: application/json" -d "{\"url\": \"$PUBLIC_URL/modbot/$BOT_TOKEN\"}" https://api.telegram.org/bot$BOT_TOKEN/setWebhook

exec "$@"