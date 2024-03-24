dev:
	poetry run uvicorn soundscapes.soundscapes:app --reload

start:
	poetry run uvicorn soundscapes.soundscapes:app