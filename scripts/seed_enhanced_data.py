"""Seed database with enhanced cable/wire product data

Usage:
    python scripts/seed_enhanced_data.py
"""
import os
import sys
import csv

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.base import SessionLocal
from app.db.models import Component, Test


def seed_components():
    """Load enhanced components from CSV"""
    db = SessionLocal()
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "components_enhanced.csv")

    print("=" * 60)
    print("SEEDING ENHANCED PRODUCT CATALOG")
    print("=" * 60)

    try:
        count = 0
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                # Convert string values to appropriate types
                component = Component(
                    sku=row['sku'],
                    name=row['name'],
                    description=row['description'],
                    category=row['category'],
                    voltage_kv=float(row['voltage_kv']) if row['voltage_kv'] else None,
                    conductor=row['conductor'],
                    cores=row['cores'],
                    cross_section_mm2=float(row['cross_section_mm2']) if row['cross_section_mm2'] else None,
                    insulation=row['insulation'],
                    armour=row['armour'],
                    sheath=row['sheath'],
                    standard=row['standard'],
                    application=row['application'],
                    fire_rating=row['fire_rating'] if row['fire_rating'] else None,
                    temperature_rating=row['temperature_rating'] if row['temperature_rating'] else None,
                    manufacturer=row['manufacturer'] if row['manufacturer'] else None,
                    keywords=row['keywords'],
                    price_per_meter=float(row['price_per_meter']) if row['price_per_meter'] else 0.0,
                    price_per_unit=float(row['price_per_unit']) if row['price_per_unit'] else 0.0,
                    currency=row['currency'],
                    in_stock=row['in_stock'].lower() == 'true',
                    lead_time_days=int(row['lead_time_days']) if row['lead_time_days'] else 0
                )
                db.add(component)
                count += 1

                if count % 10 == 0:
                    print(f"  Loaded {count} components...")

            db.commit()
            print(f"\n[OK] Successfully loaded {count} components")

            # Show sample data
            print("\nSample products:")
            samples = db.query(Component).limit(5).all()
            for s in samples:
                print(f"  - {s.sku}: {s.name} | {s.voltage_kv}kV {s.cores} {s.cross_section_mm2}mm2 {s.conductor} | Rs.{s.price_per_meter}/m")

    except Exception as e:
        print(f"[ERROR] Error loading components: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def seed_tests():
    """Load tests/services from CSV"""
    db = SessionLocal()
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "tests.csv")

    print("\n" + "=" * 60)
    print("SEEDING TESTS/SERVICES CATALOG")
    print("=" * 60)

    try:
        count = 0
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                test = Test(
                    test_id=row['test_id'],
                    test_name=row['test_name'],
                    category=row['category'],
                    description=row['description'],
                    base_price=float(row['base_price']) if row['base_price'] else 0.0,
                    unit=row['unit'],
                    currency=row['currency'],
                    duration_hours=int(row['duration_hours']) if row['duration_hours'] else None,
                    standard=row['standard'] if row['standard'] else None,
                    equipment_required=row['equipment_required'] if row['equipment_required'] else None
                )
                db.add(test)
                count += 1

                if count % 5 == 0:
                    print(f"  Loaded {count} tests...")

            db.commit()
            print(f"\n[OK] Successfully loaded {count} tests/services")

            # Show sample data
            print("\nSample tests:")
            samples = db.query(Test).limit(5).all()
            for s in samples:
                print(f"  - {s.test_id}: {s.test_name} ({s.category}) | Rs.{s.base_price} {s.unit}")

    except Exception as e:
        print(f"[ERROR] Error loading tests: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def main():
    seed_components()
    seed_tests()

    print("\n" + "=" * 60)
    print("SEEDING COMPLETE!")
    print("=" * 60)
    print("\nDatabase now contains:")
    print("  - Enhanced product catalog with detailed cable specifications")
    print("  - Tests/services catalog for pricing calculations")
    print("\nNext step: Start building the agents!")
    print("=" * 60)


if __name__ == "__main__":
    main()
