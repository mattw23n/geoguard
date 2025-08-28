setup:		## install deps
	pip install -U pip
	pip install -r requirements.txt

dev:		## run FastAPI + UI (local)
	uvicorn app.main:app --reload --port 8000

ui:		## run Streamlit UI
	streamlit run ui/streamlit_app.py

indices:
	python scripts/build_indices.py --regs data/regulations --out .cache/indices

train-router:
	python scripts/train_router.py --in data/synthetic.csv --out models/router

batch:
	python scripts/generate_results.py

test:
	pytest tests/

clean:
	rm -rf __pycache__ .pytest_cache audit/ out/
