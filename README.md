# ngrok-nginx-docker

Want to expose your web server to a public URL via ngork but afraid of the security concerns of forwarding your port to ngrok? Secure the connection by encapsulating the ngrok process in a docker container!

This repo is a way of containerizing a ngrok container that will route the ngrok URL to another nginx container. You can then configure nginx as a reverse proxy to route to other web services in the same docker network.

## Quick Start

```bash
docker-compose up
```

The generated ngrok URL will be shown on `localhost:4040`. Alternatively, you can curl `localhost:4040/api/tunnels` to get the list of information of the ngrok tunnels.
Run `curl localhost:4040/api/tunnels |  jq '[.tunnels | to_entries[] | {"value": .value.public_url}] | map(.value) | sort_by(length) | .[1]'` to return the https link, assuming you run the docker-compose file as is.

## Extensions

You can put any ngrok command into the `command` field in the docker-compose file.
