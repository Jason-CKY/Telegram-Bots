start:
	docker-compose up -d
	cd telegram-modbot && docker-compose up -d

stop-modbot:
	cd telegram-modbot && docker-compose down -v
	
destroy:
	cd telegram-modbot && docker-compose down -v
	docker-compose down -v