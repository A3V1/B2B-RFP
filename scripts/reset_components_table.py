"""Drop and recreate the components table

Usage:
    python scripts/reset_components_table.py

WARNING: This will delete all existing data in the components table.
"""
import os
import sys

# Add parent directory to path so we can import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.base import get_engine
from app.db.models import Component
from sqlalchemy import text


def main():
    engine = get_engine()

    print("Dropping components table if it exists...")
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS components CASCADE"))
        conn.commit()
    print("Table dropped.")

    print("Recreating components table with correct schema...")
    Component.__table__.create(bind=engine)
    print("Table created successfully.")


if __name__ == "__main__":
    main()
