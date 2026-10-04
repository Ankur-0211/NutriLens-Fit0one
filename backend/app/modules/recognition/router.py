from fastapi import APIRouter, File, UploadFile, Form, HTTPException, status
from typing import Optional, List, Dict, Any
from backend.app.modules.recognition.detector import FoodDetector
from backend.app.modules.recognition.classifier import FoodClassifier

router = APIRouter(prefix="/food", tags=["recognition"])

@router.post("/detect")
async def detect_foods(image: UploadFile = File(...)):
    contents = await image.read()
    detector = FoodDetector()
    regions = detector.detect(contents)
    return {
        "model_version": detector.model_version,
        "regions": regions,
    }

@router.post("/classify")
async def classify_food(
    image: UploadFile = File(...),
    coarse_hint: Optional[str] = Form(None),
):
    contents = await image.read()
    classifier = FoodClassifier()
    predictions = classifier.classify_crop(contents, coarse_hint=coarse_hint)
    return {
        "model_version": classifier.model_version,
        "predictions": predictions,
    }
