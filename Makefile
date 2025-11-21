PYTHON ?= python3
PIP ?= $(PYTHON) -m pip

.PHONY: install dev run test lint format

install:
	$(PIP) install --no-build-isolation -r requirements.txt -r requirements-dev.txt || echo "Using existing environment"

dev:
	PYTHONPATH=. FLASK_ENV=development FLASK_APP=api.api $(PYTHON) -m flask run --host 0.0.0.0 --port 8000

run:
	PYTHONPATH=. LOG_LEVEL=${LOG_LEVEL:-INFO} gunicorn api:app --workers ${WORKERS:-2} --threads ${THREADS:-4} --timeout ${TIMEOUT:-120} --bind 0.0.0.0:${PORT:-8000}

test:
	PYTHONPATH=. pytest -q --cov=api --cov-report=term-missing

lint:
	ruff check api/api.py api/vysalytica/config.py api/vysalytica/db/__init__.py api/vysalytica/middleware.py scripts/dev_db_reset.py tests

format:
	isort api tests scripts
	black api tests scripts
