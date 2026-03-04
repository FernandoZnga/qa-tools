.PHONY: up down logs logs-worker shell makemigrations migrate

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f web

logs-worker:
	docker compose logs -f worker

shell:
	docker compose exec web python manage.py shell

makemigrations:
	docker compose exec web python manage.py makemigrations

migrate:
	docker compose exec web python manage.py migrate
