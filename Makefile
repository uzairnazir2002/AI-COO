.PHONY: backend-test backend-lint frontend-lint frontend-build precommit smoke verify-runtime check

backend-test:
	cd backend && ..\.venv\Scripts\python.exe -m pytest app/tests -q

backend-lint:
	cd backend && ..\.venv\Scripts\python.exe -m ruff check app

frontend-lint:
	cd frontend && npm run lint

frontend-build:
	cd frontend && npm run build

precommit:
	pre-commit run --all-files

smoke:
	..\.venv\Scripts\python.exe scripts/smoke_mvp.py --base-url http://localhost:8000/api/v1

verify-runtime:
	.\.venv\Scripts\python.exe scripts/verify_runtime.py --api-base-url http://localhost:8000/api/v1 --frontend-base-url http://localhost:3000

check: backend-test frontend-lint frontend-build
