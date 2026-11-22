
from app.database import Base, engine
from app import db_models


def create_tables():
    print("Connecting to ParkSmart database...")

    Base.metadata.create_all(bind=engine)

    print("Database tables created successfully!")
    print("Created tables:")

    for table_name in Base.metadata.tables:
        print(f"- {table_name}")


if __name__ == "__main__":
    create_tables()
