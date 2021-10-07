start:
	docker-compose up -d
	cd telegram-modbot && docker-compose up -d

start-dev:
# sleep command is to give some time for fastapi server to be set up before curling to set webhook
	docker-compose up -d
	cd telegram-modbot && docker-compose -f docker-compose.dev.yml up -d

build-all:
	make build-modbot

build-modbot:
	cd telegram-modbot && docker-compose build

stop-modbot:
	cd telegram-modbot && docker-compose down -v
	
restart-modbot:
	make stop-modbot
	cd telegram-modbot && docker-compose up -d
	
destroy:
	cd telegram-modbot && docker-compose down -v
	docker-compose down -v