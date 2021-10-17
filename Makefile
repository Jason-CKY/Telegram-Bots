MODBOT_VERSION ?= 1.5

start:
	docker-compose up -d
	cd telegram-modbot && docker-compose pull modbot
	cd telegram-modbot && docker-compose up -d

start-dev:
	docker-compose -f docker-compose.dev.yml up -d
	cd telegram-modbot && docker-compose -f docker-compose.dev.yml up --build -d

start-reminderbot:
	docker-compose -f docker-compose.dev.yml up -d
	cd telegram-reminderbot && docker-compose -f docker-compose.dev.yml up --build -d

build-all:
	make build-modbot

build-modbot:
	cd telegram-modbot && docker build --tag jasoncky96/telegram-modbot:latest -f ./compose/Dockerfile .

deploy-modbot-image:
	cd telegram-modbot && docker buildx build --push --tag jasoncky96/telegram-modbot:$(MODBOT_VERSION) --file ./compose/Dockerfile --platform linux/arm/v7,linux/arm64/v8,linux/amd64 .
	cd telegram-modbot && docker buildx build --push --tag jasoncky96/telegram-modbot:latest --file ./compose/Dockerfile --platform linux/arm/v7,linux/arm64/v8,linux/amd64 .

stop-all:
	make stop-modbot
	docker-compose down

stop-modbot:
	cd telegram-modbot && docker-compose down
	
restart-modbot:
	make stop-modbot
	cd telegram-modbot && docker-compose up -d

restart-modbot-dev:
	make stop-modbot
	cd telegram-modbot && docker-compose -f docker-compose.dev.yml up -d
	
destroy:
	cd telegram-modbot && docker-compose down -v
	cd telegram-reminderbot && docker-compose down -v
	docker-compose down -v