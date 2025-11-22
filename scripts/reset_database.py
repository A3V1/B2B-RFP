"""Reset database and recreate all tables with new schema

Usage:
    python scripts/reset_database.py

WARNING: This will DROP all existing tables and data!
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import text
from app.db.base import engine, SessionLocal
from app.db.models import Base


def reset_database():
    """Drop all tables and recreate with new schema"""
    print("=" * 60)
    print("DATABASE RESET")
    print("=" * 60)
    print("\nWARNING: This will delete ALL existing data!")

    # Confirm reset
    confirm = input("\nType 'YES' to confirm database reset: ")
    if confirm != "YES":
        print("Reset cancelled.")
        return False

    print("\n[1/3] Dropping all existing tables...")

    # Drop all tables
    Base.metadata.drop_all(bind=engine)
    print("      All tables dropped.")

    print("\n[2/3] Creating new tables with updated schema...")

    # Create all tables with new schema
    Base.metadata.create_all(bind=engine)
    print("      All tables created.")

    print("\n[3/3] Verifying table creation...")

    # Verify tables exist
    db = SessionLocal()
    try:
        # Get list of tables
        result = db.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        tables = [row[0] for row in result]

        print(f"\n      Created {len(tables)} tables:")
        for table in tables:
            print(f"        - {table}")

    finally:
        db.close()

    print("\n" + "=" * 60)
    print("DATABASE RESET COMPLETE!")
    print("=" * 60)
    print("\nNext step: Run seed script to populate with sample data:")
    print("  python scripts/seed_new_schema.py")
    print("=" * 60)

    return True


def main():
    reset_database()


if __name__ == "__main__":
    main()
