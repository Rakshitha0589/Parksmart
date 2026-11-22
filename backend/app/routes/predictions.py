from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.ml.best_time import recommend_best_time


router = APIRouter(
    prefix="/predictions",
    tags=["ML Predictions"]
)


BASE_DIR = Path(__file__).resolve().parents[2]
MODEL_DIR = BASE_DIR / "saved_models"


def load_model(filename):
    path = MODEL_DIR / filename

    if path.exists():
        return joblib.load(path)

    return None


# LOAD TRAINED MODELS

availability_model = load_model("availability_model.joblib")
demand_model = load_model("demand_model.joblib")
location_model = load_model("location_prediction_model.joblib")

peak_bundle = load_model("peak_hours_model.joblib")

if isinstance(peak_bundle, dict):
    peak_model = peak_bundle.get("model")
    peak_thresholds = peak_bundle.get("peak_thresholds", {})
    global_threshold = peak_bundle.get("global_threshold")
else:
    peak_model = None
    peak_thresholds = {}
    global_threshold = None


anomaly_bundle = load_model("anomaly_detection_model.joblib")

if isinstance(anomaly_bundle, dict):
    anomaly_model = anomaly_bundle.get("model")
    anomaly_features = anomaly_bundle.get("features", [])
else:
    anomaly_model = None
    anomaly_features = []


# MODEL 7: WAITING TIME
waiting_time_model = load_model("waiting_time_model.joblib")


# REQUEST MODELS

class AvailabilityRequest(BaseModel):
    SystemCodeNumber: str
    Capacity: int = Field(gt=0)
    Occupancy: int = Field(ge=0)
    Hour: int = Field(ge=0, le=23)
    Minute: int = Field(ge=0, le=59)
    DayOfWeek: int = Field(ge=0, le=6)
    Month: int = Field(ge=1, le=12)
    IsWeekend: int = Field(ge=0, le=1)


class DemandRequest(AvailabilityRequest):
    pass


class PeakHourRequest(BaseModel):
    SystemCodeNumber: str
    Hour: int = Field(ge=0, le=23)
    DayOfWeek: int = Field(ge=0, le=6)
    Month: int = Field(ge=1, le=12)
    IsWeekend: int = Field(ge=0, le=1)


class BestTimeRequest(BaseModel):
    parking_location: str
    start_time: datetime
    end_time: datetime
    step_minutes: int = Field(default=15, gt=0, le=120)


class AnomalyRequest(BaseModel):
    SystemCodeNumber: str
    Capacity: int = Field(gt=0)
    Occupancy: int = Field(ge=0)
    Hour: int = Field(ge=0, le=23)
    DayOfWeek: int = Field(ge=0, le=6)
    IsWeekend: int = Field(ge=0, le=1)


# WAITING TIME REQUEST

class WaitingTimeRequest(BaseModel):
    ParkingLocation: str
    Hour: int = Field(ge=0, le=23)
    DayOfWeek: int = Field(ge=0, le=6)
    QueueLength: int = Field(ge=0)
    AvailableSpaces: int = Field(ge=0)


# VALIDATION

def validate_occupancy(data):
    if not data.SystemCodeNumber.strip():
        raise HTTPException(
            status_code=400,
            detail="Parking location cannot be empty."
        )

    if data.Occupancy > data.Capacity:
        raise HTTPException(
            status_code=400,
            detail="Occupancy cannot exceed capacity."
        )


# HEALTH CHECK

@router.get("/health")
def prediction_health():
    return {
        "status": "success",
        "availability_model_loaded": availability_model is not None,
        "demand_model_loaded": demand_model is not None,
        "peak_hours_model_loaded": peak_model is not None,
        "best_time_model_available": availability_model is not None,
        "location_model_loaded": location_model is not None,
        "anomaly_detection_model_loaded": anomaly_model is not None,
        "waiting_time_model_loaded": waiting_time_model is not None
    }


# MODEL 1: AVAILABILITY

@router.post("/availability")
def predict_availability(data: AvailabilityRequest):

    validate_occupancy(data)

    if availability_model is None:
        raise HTTPException(
            status_code=503,
            detail="Availability model is not loaded."
        )

    try:
        input_data = pd.DataFrame([{
            "SystemCodeNumber": data.SystemCodeNumber,
            "Capacity": data.Capacity,
            "Occupancy": data.Occupancy,
            "Hour": data.Hour,
            "Minute": data.Minute,
            "DayOfWeek": data.DayOfWeek,
            "Month": data.Month,
            "IsWeekend": data.IsWeekend
        }])

        prediction = float(
            availability_model.predict(input_data)[0]
        )

        predicted_spaces = max(
            0,
            min(data.Capacity, round(prediction))
        )

        return {
            "status": "success",
            "parking_location": data.SystemCodeNumber,
            "predicted_available_spaces": predicted_spaces,
            "prediction_type": "historical model estimate",
            "message": "Not confirmed live availability."
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Availability prediction failed: {str(error)}"
        )


# MODEL 2: DEMAND PREDICTION

@router.post("/demand")
def predict_demand(data: DemandRequest):

    validate_occupancy(data)

    if demand_model is None:
        raise HTTPException(
            status_code=503,
            detail="Demand model is not loaded."
        )

    try:
        occupancy_rate = data.Occupancy / data.Capacity

        input_data = pd.DataFrame([{
            "SystemCodeNumber": data.SystemCodeNumber,
            "Capacity": data.Capacity,
            "Occupancy": data.Occupancy,
            "OccupancyRate": occupancy_rate,
            "Hour": data.Hour,
            "Minute": data.Minute,
            "DayOfWeek": data.DayOfWeek,
            "Month": data.Month,
            "IsWeekend": data.IsWeekend
        }])

        prediction = demand_model.predict(input_data)[0]

        return {
            "status": "success",
            "parking_location": data.SystemCodeNumber,
            "predicted_demand": str(prediction),
            "occupancy_rate": round(occupancy_rate, 3),
            "prediction_type": "historical model estimate"
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Demand prediction failed: {str(error)}"
        )


# MODEL 3: PEAK HOURS

@router.post("/peak-hours")
def predict_peak_hours(data: PeakHourRequest):

    if not data.SystemCodeNumber.strip():
        raise HTTPException(
            status_code=400,
            detail="Parking location cannot be empty."
        )

    if peak_model is None:
        raise HTTPException(
            status_code=503,
            detail="Peak-hour model is not loaded."
        )

    try:
        input_data = pd.DataFrame([{
            "SystemCodeNumber": data.SystemCodeNumber,
            "Hour": data.Hour,
            "DayOfWeek": data.DayOfWeek,
            "Month": data.Month,
            "IsWeekend": data.IsWeekend
        }])

        prediction = int(peak_model.predict(input_data)[0])

        threshold = peak_thresholds.get(
            data.SystemCodeNumber,
            global_threshold
        )

        return {
            "status": "success",
            "parking_location": data.SystemCodeNumber,
            "hour": data.Hour,
            "is_peak_hour": bool(prediction),
            "peak_status": "Peak" if prediction == 1 else "Non-Peak",
            "historical_occupancy_threshold": (
                float(threshold) if threshold is not None else None
            ),
            "prediction_type": "historical model estimate"
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Peak-hour prediction failed: {str(error)}"
        )


# MODEL 4: BEST PARKING TIME

@router.post("/best-time")
def predict_best_time(data: BestTimeRequest):

    if not data.parking_location.strip():
        raise HTTPException(
            status_code=400,
            detail="Parking location cannot be empty."
        )

    if data.start_time >= data.end_time:
        raise HTTPException(
            status_code=400,
            detail="End time must be after start time."
        )

    try:
        return recommend_best_time(
            parking_location=data.parking_location,
            start_time=data.start_time,
            end_time=data.end_time,
            step_minutes=data.step_minutes
        )

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error))

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Best-time prediction failed: {str(error)}"
        )


# MODEL 5: LOCATION-WISE OCCUPANCY

@router.post("/location")
def predict_location(data: AvailabilityRequest):

    validate_occupancy(data)

    if location_model is None:
        raise HTTPException(
            status_code=503,
            detail="Location prediction model is not loaded."
        )

    try:
        input_data = pd.DataFrame([{
            "SystemCodeNumber": data.SystemCodeNumber,
            "Capacity": data.Capacity,
            "Occupancy": data.Occupancy,
            "Hour": data.Hour,
            "Minute": data.Minute,
            "DayOfWeek": data.DayOfWeek,
            "Month": data.Month,
            "IsWeekend": data.IsWeekend
        }])

        prediction = float(
            location_model.predict(input_data)[0]
        )

        predicted_occupancy = max(
            0,
            min(data.Capacity, round(prediction))
        )

        predicted_available = (
            data.Capacity - predicted_occupancy
        )

        return {
            "status": "success",
            "parking_location": data.SystemCodeNumber,
            "predicted_occupancy": predicted_occupancy,
            "predicted_available_spaces": predicted_available,
            "capacity": data.Capacity,
            "prediction_type": "historical location-wise estimate",
            "message": (
                "Predicts next recorded occupancy, "
                "not actual live zone occupancy."
            )
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Location prediction failed: {str(error)}"
        )


# MODEL 6: ANOMALY DETECTION

@router.post("/anomaly")
def detect_anomaly(data: AnomalyRequest):

    validate_occupancy(data)

    if anomaly_model is None or not anomaly_features:
        raise HTTPException(
            status_code=503,
            detail="Anomaly detection model is not loaded."
        )

    try:
        available_spaces = data.Capacity - data.Occupancy
        occupancy_rate = data.Occupancy / data.Capacity

        feature_values = {
            "Capacity": data.Capacity,
            "Occupancy": data.Occupancy,
            "AvailableSpaces": available_spaces,
            "OccupancyRate": occupancy_rate,
            "Hour": data.Hour,
            "DayOfWeek": data.DayOfWeek,
            "IsWeekend": data.IsWeekend
        }

        input_data = pd.DataFrame(
            [[feature_values[feature] for feature in anomaly_features]],
            columns=anomaly_features
        )

        prediction = int(anomaly_model.predict(input_data)[0])

        is_anomaly = prediction == -1

        return {
            "status": "success",
            "parking_location": data.SystemCodeNumber,
            "is_anomaly": is_anomaly,
            "anomaly_label": (
                "Unusual Occupancy" if is_anomaly else "Normal"
            ),
            "capacity": data.Capacity,
            "occupancy": data.Occupancy,
            "available_spaces": available_spaces,
            "occupancy_rate": round(occupancy_rate, 3),
            "operator_verification_required": is_anomaly,
            "prediction_type": "anomaly pattern detection",
            "message": (
                "An unusual occupancy pattern was detected. "
                "Operator verification is required."
                if is_anomaly
                else "No unusual occupancy pattern was detected."
            ),
            "important_note": (
                "An anomaly is an unusual data pattern, "
                "not proof of a parking incident."
            )
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Anomaly detection failed: {str(error)}"
        )


# MODEL 7: WAITING-TIME PREDICTION

@router.post("/waiting-time")
def predict_waiting_time(data: WaitingTimeRequest):

    if not data.ParkingLocation.strip():
        raise HTTPException(
            status_code=400,
            detail="Parking location cannot be empty."
        )

    if waiting_time_model is None:
        raise HTTPException(
            status_code=503,
            detail="Waiting-time model is not loaded."
        )

    try:
        input_data = pd.DataFrame([{
            "ParkingLocation": data.ParkingLocation,
            "Hour": data.Hour,
            "DayOfWeek": data.DayOfWeek,
            "QueueLength": data.QueueLength,
            "AvailableSpaces": data.AvailableSpaces
        }])

        prediction = float(
            waiting_time_model.predict(input_data)[0]
        )

        predicted_waiting_time = max(0, round(prediction, 2))

        return {
            "status": "success",
            "parking_location": data.ParkingLocation,
            "predicted_waiting_time_minutes": predicted_waiting_time,
            "queue_length": data.QueueLength,
            "available_spaces": data.AvailableSpaces,
            "prediction_type": "simulated demo model estimate",
            "data_source": "SIMULATED_DEMO",
            "important_note": (
                "This waiting-time prediction is trained on simulated demo data "
                "and is not validated using real-world queue observations."
            )
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Waiting-time prediction failed: {str(error)}"
        )