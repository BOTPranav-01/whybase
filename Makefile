up:
	docker compose up --build
seed:
	python -m backend.whybase.seed.load
test:
	python -m pytest -q
arena:
	python -m backend.whybase.cli arena
loadtest:
	python -c "from backend.whybase.loadtest import run; print(run())"
dev:
	uvicorn backend.whybase.main:app --reload
