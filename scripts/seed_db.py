"""Seed the database with components from data/components.csv

Usage:
    python scripts/seed_db.py

This script will call app.db.base.init_db() to create tables and then import the CSV.
Ensure your DATABASE_URL in app/config.py (or .env) points to a reachable DB.
"""
import os
import sys

# Add parent directory to path so we can import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.base import init_db
from app.db.crud import bulk_insert_components_from_csv


def main():
    print("Initializing DB (creating tables if missing)")
    init_db()
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "components.csv")
    csv_path = os.path.normpath(csv_path)
    print("Importing components from:", csv_path)
    count = bulk_insert_components_from_csv(csv_path)
    print(f"Inserted {count} components from CSV")


if __name__ == "__main__":
    main()
