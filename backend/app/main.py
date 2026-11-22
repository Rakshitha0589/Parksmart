from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.predictions import router as predictions_router

app = FastAPI(
    title="Smart Parking Management System",
    description="Smart Parking with Automatic Predictions",
    version="2.0.0",
)

# CORS CONFIGURATION
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:5176",
        "http://127.0.0.1:5176",
        "http://localhost:5177",
        "http://127.0.0.1:5177",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ROOT ENDPOINT
@app.get("/")
def home():
    return {
        "status": "success",
        "message": "Smart Parking Backend is running!",
    }


# HEALTH CHECK
@app.get("/health")
def health_check():
    return {
        "status": "success",
        "backend": "online",
    }


# PARKING STATUS
@app.get("/api/parking/status")
def parking_status():
    total_slots = 300
    occupied_slots = 0
    booked_slots = 0
    available_slots = total_slots - occupied_slots - booked_slots

    return {
        "status": "success",
        "total_slots": total_slots,
        "occupied_slots": occupied_slots,
        "booked_slots": booked_slots,
        "available_slots": available_slots,
        "occupancy_rate": 0,
    }


# ML PREDICTION ROUTES
app.include_router(
    predictions_router,
    prefix="/api",
)


# STARTUP MESSAGE
@app.get("/api/system")
def system_status():
    return {
        "system": "ParkSmart AI",
        "status": "running",
        "version": "2.0.0",
    }