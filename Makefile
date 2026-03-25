.PHONY: run dev compile docker-up docker-down

run:
	uvicorn src.market_stream.app:app --host 127.0.0.1 --port 8010

dev:
	uvicorn src.market_stream.app:app --host 127.0.0.1 --port 8010 --reload

compile:
	python3 -m compileall src

docker-up:
	docker compose up --build

docker-down:
	docker compose down
