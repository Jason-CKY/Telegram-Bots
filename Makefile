MODBOT_VERSION ?= 1.9
REMINDERBOT_VERSION ?= 1.12
BACKUP_DIR ?= ~/backup
REMINDERBOT_BACKUP_FILE ?= reminderbot-backup.tar
MODBOT_BACKUP_FILE ?= modbot-backup.tar

format: 
	yapf -i -r -p telegram-reminderbot telegram-modbot

backup-all: backup-reminderbot backup-modbot

backup-reminderbot:
	docker stop telegram-reminderbot_reminderbot_1 telegram-reminderbot_db_1
	docker run --rm --volumes-from telegram-reminderbot_db_1 -v $(BACKUP_DIR):/backup ubuntu bash -c "cd /data/db && tar cvf /backup/$(REMINDERBOT_BACKUP_FILE) ."
	docker start telegram-reminderbot_reminderbot_1 telegram-reminderbot_db_1

backup-modbot:
	docker stop telegram-modbot_modbot_1 telegram-modbot_db_1
	docker run --rm --volumes-from telegram-modbot_db_1 -v $(BACKUP_DIR):/backup ubuntu bash -c "cd /data/db && tar cvf /backup/$(MODBOT_BACKUP_FILE) ."
	docker start telegram-modbot_modbot_1 telegram-modbot_db_1

restore-backup-all: restore-backup-reminderbot restore-backup-modbot

restore-backup-reminderbot:
	ls $(BACKUP_DIR) | grep reminderbot-backup.tar
	docker volume create telegram-reminderbot_reminderbot-db
	docker run --rm -v telegram-reminderbot_reminderbot-db:/recover -v $(BACKUP_DIR):/backup ubuntu bash -c "cd /recover && tar xvf /backup/reminderbot-backup.tar"

restore-backup-modbot:
	ls $(BACKUP_DIR) | grep modbot-backup.tar
	docker volume create telegram-modbot_modbot-db
	docker run --rm -v telegram-modbot_modbot-db:/recover -v $(BACKUP_DIR):/backup ubuntu bash -c "cd /recover && tar xvf /backup/modbot-backup.tar"

start-prod: start-modbot-prod start-reminderbot-prod

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

stop-all: stop-modbot stop-reminderbot
	docker-compose down

stop-modbot:
	cd telegram-modbot && docker-compose down

stop-reminderbot:
	cd telegram-reminderbot && docker-compose down
	
destroy:
	cd telegram-modbot && docker-compose down -v
	cd telegram-reminderbot && docker-compose down -v
	docker-compose down -v
	-docker volume rm telegram-modbot_modbot-db
	-docker volume rm telegram-reminderbot_reminderbot-db
