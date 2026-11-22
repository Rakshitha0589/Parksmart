
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class ParkingSlot(Base):
    __tablename__ = "parking_slots"

    __table_args__ = (
        UniqueConstraint(
            "area",
            "slot_number",
            name="uq_parking_area_slot",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    area = Column(String(50), nullable=False)
    slot_number = Column(Integer, nullable=False)

    status = Column(
        String(20),
        nullable=False,
        default="available",
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    bookings = relationship(
        "Booking",
        back_populates="slot",
    )


class Booking(Base):
    __tablename__ = "bookings"

    booking_id = Column(String(60), primary_key=True)

    slot_id = Column(
        Integer,
        ForeignKey("parking_slots.id"),
        nullable=False,
    )

    customer_name = Column(String(120), nullable=False)
    vehicle_type = Column(String(20), nullable=False)
    vehicle_number = Column(String(30), nullable=False, index=True)

    status = Column(
        String(20),
        nullable=False,
        default="booked",
    )

    booked_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    entry_time = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    exit_time = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    slot = relationship(
        "ParkingSlot",
        back_populates="bookings",
    )


Index(
    "ix_bookings_slot_status",
    Booking.slot_id,
    Booking.status,
)
