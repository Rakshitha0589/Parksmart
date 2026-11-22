
from datetime import datetime, timezone
from uuid import uuid4
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.db_models import ParkingSlot, Booking

router = APIRouter(
    prefix="/api/parking",
    tags=["Parking Database"],
)


class BookingCreate(BaseModel):
    area: str
    slot_number: int
    customer_name: str = Field(min_length=1, max_length=120)
    vehicle_type: str
    vehicle_number: str = Field(min_length=1, max_length=30)


def booking_response(booking):
    slot = booking.slot

    return {
        "bookingId": booking.booking_id,
        "customerName": booking.customer_name,
        "vehicle": booking.vehicle_type,
        "vehicleNumber": booking.vehicle_number,
        "area": slot.area,
        "number": slot.slot_number,
        "status": booking.status,
        "bookedAt": (
            booking.booked_at.isoformat()
            if booking.booked_at else None
        ),
        "enteredAt": (
            booking.entry_time.isoformat()
            if booking.entry_time else None
        ),
        "exitedAt": (
            booking.exit_time.isoformat()
            if booking.exit_time else None
        ),
    }


# CREATE BOOKING
@router.post("/bookings")
def create_booking(
    data: BookingCreate,
    db: Session = Depends(get_db),
):
    normalized_number = re.sub(
        r"\s+", "", data.vehicle_number
    ).upper()

    if data.area not in ["Parking A", "Parking B", "Parking C"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid parking area.",
        )

    if data.vehicle_type not in ["Car", "Bike"]:
        raise HTTPException(
            status_code=400,
            detail="Vehicle type must be Car or Bike.",
        )

    slot = (
        db.query(ParkingSlot)
        .filter(
            ParkingSlot.area == data.area,
            ParkingSlot.slot_number == data.slot_number,
        )
        .with_for_update()
        .first()
    )

    if not slot:
        raise HTTPException(
            status_code=404,
            detail="Parking slot not found.",
        )

    if slot.status != "available":
        raise HTTPException(
            status_code=409,
            detail="Parking slot is not available.",
        )

    duplicate = (
        db.query(Booking)
        .filter(
            Booking.vehicle_number == normalized_number,
            Booking.status.in_(["booked", "occupied"]),
        )
        .first()
    )

    if duplicate:
        raise HTTPException(
            status_code=409,
            detail="This vehicle already has an active booking.",
        )

    booking = Booking(
        booking_id=f"BK-{uuid4().hex[:12].upper()}",
        slot_id=slot.id,
        customer_name=data.customer_name.strip(),
        vehicle_type=data.vehicle_type,
        vehicle_number=normalized_number,
        status="booked",
        booked_at=datetime.now(timezone.utc),
    )

    slot.status = "booked"

    try:
        db.add(booking)
        db.commit()
        db.refresh(booking)
    except Exception:
        db.rollback()
        raise

    return booking_response(booking)


# VIEW ACTIVE BOOKINGS
@router.get("/bookings")
def get_bookings(db: Session = Depends(get_db)):
    bookings = (
        db.query(Booking)
        .filter(Booking.status.in_(["booked", "occupied"]))
        .order_by(Booking.booked_at.desc())
        .all()
    )

    return [booking_response(b) for b in bookings]


# VERIFY QR BOOKING
@router.get("/bookings/verify/{booking_id}")
def verify_booking(
    booking_id: str,
    db: Session = Depends(get_db),
):
    booking = (
        db.query(Booking)
        .filter(
            Booking.booking_id == booking_id,
            Booking.status.in_(["booked", "occupied"]),
        )
        .first()
    )

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Active booking not found.",
        )

    return {
        "verified": True,
        "booking": booking_response(booking),
    }


# CONFIRM VEHICLE ENTRY
@router.post("/bookings/{booking_id}/entry")
def confirm_entry(
    booking_id: str,
    db: Session = Depends(get_db),
):
    booking = (
        db.query(Booking)
        .filter(Booking.booking_id == booking_id)
        .with_for_update()
        .first()
    )

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found.",
        )

    if booking.status != "booked":
        raise HTTPException(
            status_code=409,
            detail="Vehicle entry cannot be confirmed for this booking.",
        )

    entry_time = datetime.now(timezone.utc)

    booking.status = "occupied"
    booking.entry_time = entry_time
    booking.slot.status = "occupied"

    db.commit()
    db.refresh(booking)

    return booking_response(booking)


# CONFIRM VEHICLE EXIT
@router.post("/bookings/{booking_id}/exit")
def confirm_exit(
    booking_id: str,
    db: Session = Depends(get_db),
):
    booking = (
        db.query(Booking)
        .filter(Booking.booking_id == booking_id)
        .with_for_update()
        .first()
    )

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found.",
        )

    if booking.status != "occupied":
        raise HTTPException(
            status_code=409,
            detail="Vehicle must enter before it can exit.",
        )

    if not booking.entry_time:
        raise HTTPException(
            status_code=409,
            detail="Vehicle entry time is missing.",
        )

    exit_time = datetime.now(timezone.utc)

    booking.status = "completed"
    booking.exit_time = exit_time
    booking.slot.status = "available"

    db.commit()
    db.refresh(booking)

    return booking_response(booking)


# PARKING HISTORY
@router.get("/history")
def get_parking_history(
    db: Session = Depends(get_db),
):
    records = (
        db.query(Booking)
        .filter(Booking.status == "completed")
        .order_by(Booking.exit_time.desc())
        .all()
    )

    return [booking_response(b) for b in records]


# PARKING SLOT AVAILABILITY
@router.get("/slots")
def get_parking_slots(
    db: Session = Depends(get_db),
):
    slots = (
        db.query(ParkingSlot)
        .order_by(
            ParkingSlot.area,
            ParkingSlot.slot_number,
        )
        .all()
    )

    return [
        {
            "id": slot.id,
            "area": slot.area,
            "number": slot.slot_number,
            "status": slot.status,
        }
        for slot in slots
    ]
