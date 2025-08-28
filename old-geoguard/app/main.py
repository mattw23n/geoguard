# FastAPI app entrypoint for GeoGuard
from fastapi import FastAPI
from app.decision_head import classify_feature, batch_classify

app = FastAPI()

@app.get("/healthz")
def healthz():
    return {"status": "ok", "pipeline_version": "0.1.0"}

@app.post("/classify")
def classify(payload: dict):
    return classify_feature(payload)

@app.post("/batch")
def batch(payload: dict):
    return batch_classify(payload)
