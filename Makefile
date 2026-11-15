.PHONY: install demo run test check
install:
	python -m pip install -r requirements.txt
demo:
	python -m app.seed_demo
run:
	COOKIE_SECURE=false python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
test:
	pytest -q
check:
	python -m py_compile app/*.py
	node --check static/app.js
	pytest -q
