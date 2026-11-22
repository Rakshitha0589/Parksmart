from app.main import app
from app.booking_routes import router as booking_router

# Register PostgreSQL parking and booking APIs
app.include_router(booking_router)

print("ParkSmart PostgreSQL routes registered successfully!")