MODBOT_VERSION ?= 1.9
REMINDERBOT_VERSION ?= 1.12
BACKUP_DIR ?= ~/backup

format: 
	yapf -i -r -p telegram-reminderbot telegram-modbot

backup-all: backup-reminderbot backup-modbot

backup-reminderbot:
	docker stop telegram-reminderbot-reminderbot-1
	docker run --rm --volumes-from telegram-reminderbot-db-1 -v $(BACKUP_DIR):/backup ubuntu bash -c "cd /data/db && tar cvf /backup/reminderbot-backup.tar ."
	docker start telegram-reminderbot-reminderbot-1

backup-modbot:
	docker stop telegram-modbot-modbot-1
	docker run --rm --volumes-from telegram-modbot-db-1 -v $(BACKUP_DIR):/backup ubuntu bash -c "cd /data/db && tar cvf /backup/modbot-backup.tar ."
	docker start telegram-modbot-modbot-1

restore-backup-all: restore-backup-reminderbot restore-backup-modbot

restore-backup-reminderbot:
	ls ~/backup | grep reminderbot-backup.tar
	docker volume rm telegram-reminderbot_reminderbot-db
	docker volume create telegram-reminderbot_reminderbot-db
	docker run --rm -v telegram-reminderbot_reminderbot-db:/recover -v $(BACKUP_DIR):/backup ubuntu bash -c "cd /recover && tar xvf /backup/reminderbot-backup.tar"

restore-backup-modbot:
	ls ~/backup | grep modbot-backup.tar
	docker volume rm telegram-modbot_modbot-db
	docker volume create telegram-modbot_modbot-db
	docker run --rm -v telegram-modbot_modbot-db:/recover -v ~/backup:/backup ubuntu bash -c "cd /recover && tar xvf /backup/modbot-backup.tar"

start-prod:
	make start-modbot-prod start-reminderbot-prod

start-modbot-prod:
	docker-compose up -d
	cd telegram-modbot && docker-compose pull modbot
	cd telegram-modbot && docker-compose up -d

start-reminderbot-prod:
	docker-compose up -d
	cd telegram-reminderbot && docker-compose pull reminderbot
	cd telegram-reminderbot && docker-compose up -d
	
start-modbot-dev:
	docker-compose -f docker-compose.dev.yml up -d
	cd telegram-modbot && docker-compose -f docker-compose.dev.yml up --build -d

start-reminderbot-dev:
	docker-compose -f docker-compose.dev.yml up -d
	cd telegram-reminderbot && docker-compose -f docker-compose.dev.yml up --build -d

build-modbot:
	cd telegram-modbot && docker build --tag jasoncky96/telegram-modbot:latest -f ./compose/Dockerfile .

build-reminderbot:
	cd telegram-reminderbot && docker build --tag jasoncky96/telegram-reminderbot:latest -f ./compose/Dockerfile .

deploy-modbot-image:
	cd telegram-modbot && docker buildx build --push --tag jasoncky96/telegram-modbot:$(MODBOT_VERSION) --file ./compose/Dockerfile --platform linux/arm/v7,linux/arm64/v8,linux/amd64 .
	cd telegram-modbot && docker buildx build --push --tag jasoncky96/telegram-modbot:latest --file ./compose/Dockerfile --platform linux/arm/v7,linux/arm64/v8,linux/amd64 .

deploy-reminderbot-image:
	cd telegram-reminderbot && docker buildx build --push --tag jasoncky96/telegram-reminderbot:$(REMINDERBOT_VERSION) --file ./compose/Dockerfile --platform linux/arm/v7,linux/arm64/v8,linux/amd64 .
	cd telegram-reminderbot && docker buildx build --push --tag jasoncky96/telegram-reminderbot:latest --file ./compose/Dockerfile --platform linux/arm/v7,linux/arm64/v8,linux/amd64 .

stop-all:
	make stop-modbot
	make stop-reminderbot
	docker-compose down

stop-modbot:
	cd telegram-modbot && docker-compose down

stop-reminderbot:
	cd telegram-reminderbot && docker-compose down
	
destroy:
	cd telegram-modbot && docker-compose down -v
	cd telegram-reminderbot && docker-compose down -v
	docker-compose down -v