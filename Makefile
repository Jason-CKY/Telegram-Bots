start:
	docker-compose up -d
	cd telegram-modbot && docker-compose up -d

start-dev:
	docker-compose up -d
	cd telegram-modbot && docker-compose -f docker-compose.dev.yml up -d

stop-modbot:
	cd telegram-modbot && docker-compose down -v
	
restart-modbot:
	cd telegram-modbot && docker-compose down -v
	cd telegram-modbot && docker-compose up -d
	
destroy:
	cd telegram-modbot && docker-compose down -v
	docker-compose down -v