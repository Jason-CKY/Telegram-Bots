MODBOT_VERSION ?= 1.5

start-prod:
	docker-compose up -d
	cd telegram-modbot && docker-compose pull modbot
	cd telegram-modbot && docker-compose up -d

start-modbot-dev:
	docker-compose -f docker-compose.dev.yml up -d
	cd telegram-modbot && docker-compose -f docker-compose.dev.yml up --build -d

start-reminderbot-dev:
	docker-compose -f docker-compose.dev.yml up -d
	cd telegram-reminderbot && docker-compose -f docker-compose.dev.yml up --build -d

build-all:
	make build-modbot

build-modbot:
	cd telegram-modbot && docker build --tag jasoncky96/telegram-modbot:latest -f ./compose/Dockerfile .

build-reminderbot:
	cd telegram-reminderbot && docker build --tag jasoncky96/telegram-reminderbot:latest -f ./compose/Dockerfile .

deploy-modbot-image:
	cd telegram-modbot && docker buildx build --push --tag jasoncky96/telegram-modbot:$(MODBOT_VERSION) --file ./compose/Dockerfile --platform linux/arm/v7,linux/arm64/v8,linux/amd64 .
	cd telegram-modbot && docker buildx build --push --tag jasoncky96/telegram-modbot:latest --file ./compose/Dockerfile --platform linux/arm/v7,linux/arm64/v8,linux/amd64 .

deploy-reminderbot-image:
	cd telegram-reminderbot && docker buildx build --push --tag jasoncky96/telegram-reminderbot:$(MODBOT_VERSION) --file ./compose/Dockerfile --platform linux/arm/v7,linux/arm64/v8,linux/amd64 .
	cd telegram-reminderbot && docker buildx build --push --tag jasoncky96/telegram-reminderbot:latest --file ./compose/Dockerfile --platform linux/arm/v7,linux/arm64/v8,linux/amd64 .

stop-all:
	make stop-modbot
	make stop-reminderbot
	docker-compose down

stop-modbot:
	cd telegram-modbot && docker-compose down

stop-reminderbot:
	cd telegram-reminderbot && docker-compose down
	
destroy-all:
	cd telegram-modbot && docker-compose down -v
	cd telegram-reminderbot && docker-compose down -v
	docker-compose down -v

destroy-modbot:
	cd telegram-modbot && docker-compose down -v
	docker-compose down -v

destroy-reminderbot:
	cd telegram-reminderbot && docker-compose down -v
	docker-compose down -v