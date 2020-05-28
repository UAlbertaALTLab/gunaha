all: .env

.env:
	python -c 'import secrets; print("export SECRET_KEY=" + secrets.token_hex())' > $@
