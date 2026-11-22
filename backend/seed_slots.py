
from app.database import SessionLocal
from app.db_models import ParkingSlot

AREAS = ["Parking A", "Parking B", "Parking C"]


def seed_slots():
    db = SessionLocal()

    try:
        added = 0

        for area in AREAS:
            for number in range(1, 101):
                existing = (
                    db.query(ParkingSlot)
                    .filter_by(
                        area=area,
                        slot_number=number,
                    )
                    .first()
                )

                if existing is None:
                    db.add(
                        ParkingSlot(
                            area=area,
                            slot_number=number,
                            status="available",
                        )
                    )
                    added += 1

        db.commit()

        total = db.query(ParkingSlot).count()

        print(f"New parking slots added: {added}")
        print(f"Total database parking slots: {total}")
        print("Parking slot setup completed!")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_slots()
