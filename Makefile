all: build

build: requirements.txt
	docker build -t gunaha:latest .

run-local: build
	docker run --rm --name=gunaha -p 8000:8000 --mount "type=bind,source=$(shell pwd)/run,target=/data" -e LOG_LEVEL=debug gunaha

push: build
	docker tag gunaha:latest docker.pkg.github.com/ualbertaaltlab/gunaha/gunaha:latest
	docker push docker.pkg.github.com/ualbertaaltlab/gunaha/gunaha:latest

env: .env

.PHONY: all build env push run-local

.env:
	python -c 'import secrets; print("export SECRET_KEY=" + secrets.token_hex())' > $@

requirements.txt: poetry.lock
	poetry export -f requirements.txt --without-hashes -o $@
