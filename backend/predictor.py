"""
Loads the trained crop-growth-stage pipeline (crop_stage_model.pkl) and
turns a raw prediction into the response shape the frontend expects:
predicted_stage, confidence_score, status, status_note, suggestions.

The pipeline itself (ColumnTransformer + SVC) is treated as a black box —
we don't retrain or touch it here, only call it correctly.
"""

import os
import joblib
import numpy as np
import pandas as pd

MODEL_PATH = os.path.join(os.path.dirname(__file__), "crop_stage_model.pkl")
_model = joblib.load(MODEL_PATH)
_classifier = _model.named_steps["classifier"]

# Order matters: must match the column names the ColumnTransformer was fit on.
FEATURE_ORDER = [
    "soil_moisture",
    "soil_temperature",
    "air_temperature",
    "humidity",
    "rainfall",
    "crop_age_days",
    "soil_ph",
    "crop_type",
    "soil_type",
]

STAGE_SUGGESTIONS = {
    "Sowing / Germination": [
        "Keep soil consistently moist but not waterlogged for even germination.",
        "Favor light, frequent watering over one heavy irrigation right after sowing.",
        "Watch for surface crusting, which can block seedling emergence.",
    ],
    "Vegetative": [
        "This phase drives leaf and root growth — make sure nitrogen levels are adequate.",
        "Irrigation demand rises as leaf area increases; monitor soil moisture more closely.",
        "Scout for early pest and weed pressure while the crop canopy is still developing.",
    ],
    "Flowering / Reproductive": [
        "Avoid water stress now — moisture shortage during flowering can cut final yield.",
        "Ease off heavy nitrogen top-dressing; potassium and phosphorus matter more here.",
        "Check for pollinator activity and unusual flower or bud drop.",
    ],
    "Maturity / Harvesting": [
        "Start reducing irrigation to help the crop dry down ahead of harvest.",
        "Track grain or fruit moisture regularly to time the harvest window.",
        "Line up labor and equipment based on the short-range weather forecast.",
    ],
}


def _confidence_from_decision(decision_scores: np.ndarray) -> np.ndarray:
    """
    This SVC was trained with probability=False, so predict_proba isn't
    available (retraining with probability=True wasn't an option here,
    since we only have the finished pipeline, not the training data).
    We convert the one-vs-rest decision_function margins into a
    softmax-based pseudo-confidence. This is fine for ranking / display
    purposes, but it is NOT a calibrated probability — worth knowing if
    this number is ever used for anything more than showing the user
    "how sure" the model looked.
    """
    scores = np.atleast_2d(decision_scores)
    exp = np.exp(scores - scores.max(axis=1, keepdims=True))
    return exp / exp.sum(axis=1, keepdims=True)


def _soil_moisture_status(soil_moisture: float) -> tuple[str, str]:
    if soil_moisture < 25:
        return "Needs Irrigation", "Soil moisture is on the low side for healthy growth."
    if soil_moisture > 75:
        return "Waterlogged Risk", "Soil moisture is quite high — check drainage."
    return "Healthy", "Soil moisture looks within a normal range."


def predict_crop_stage(payload: dict) -> dict:
    """
    payload keys must match FEATURE_ORDER (see PredictionRequest in main.py).
    Raises ValueError if a field is missing or an unusable value slips through.
    """
    try:
        row = pd.DataFrame([{k: payload[k] for k in FEATURE_ORDER}])
    except KeyError as missing:
        raise ValueError(f"Missing field for prediction: {missing}")

    predicted_stage = _model.predict(row)[0]

    confidence_score = None
    try:
        decision = _model.decision_function(row)
        confidence_matrix = _confidence_from_decision(decision)
        classes = list(_classifier.classes_)
        class_index = classes.index(predicted_stage)
        confidence_score = round(float(confidence_matrix[0][class_index]) * 100, 1)
    except Exception:
        # Don't fail the whole request just because confidence couldn't be computed.
        pass

    status, status_note = _soil_moisture_status(payload["soil_moisture"])

    suggestions = list(STAGE_SUGGESTIONS.get(predicted_stage, []))
    if payload["soil_ph"] < 5.5 or payload["soil_ph"] > 8.0:
        suggestions.append("Soil pH is outside the typical 5.5–8.0 range — consider a soil test.")

    return {
        "predicted_stage": predicted_stage,
        "confidence_score": confidence_score,
        "status": status,
        "status_note": status_note,
        "suggestions": suggestions,
    }