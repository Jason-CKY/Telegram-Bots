# Telegram bots exposed using ngrok and nginx reverse proxy

Telegram bots written in FastAPI servers, with a nginx reverse proxy that is connected to a public URL via ngrok. Everything is dockerized for ease of deployment. The modular bots' docker-compose files rely on the docker network created by this nginx-ngrok proxy to run, so you need to start the bot using the Make commands from this root directory.

## Quick Start

```bash
make start-prod
```

## Start in development mode

Starting moderation bot in dev mode:

```bash
make start-modbot-dev
```

## List of telegram bots

- telegram-modbot
