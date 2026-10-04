from backend.app.core.database import engine, Base, SessionLocal
from backend.app.models import *
from backend.app.data.seed_data import seed_database

def init_db():
    print("Creating all database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")

    db = SessionLocal()
    try:
        print("Seeding initial canonical foods and identity mappings...")
        seed_database(db)
        print("Seed completed successfully.")
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
