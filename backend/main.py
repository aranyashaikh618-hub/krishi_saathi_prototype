from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from predictor import predict_crop_stage

app = FastAPI(title="AgriSense API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # for hackathon/dev only — fine for now
    allow_methods=["*"],
    allow_headers=["*"],
)


# This class describes the exact JSON shape aiprediction.html sends to
# /api/predict-stage. Field names/types match what crop_stage_model.pkl
# was trained on.
class PredictionRequest(BaseModel):
    soil_moisture: float
    soil_temperature: float
    air_temperature: float
    humidity: float
    rainfall: float
    crop_age_days: float
    soil_ph: float
    crop_type: str
    soil_type: str


@app.post("/api/predict-stage")
def predict_stage(data: PredictionRequest):
    try:
        return predict_crop_stage(data.dict())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))