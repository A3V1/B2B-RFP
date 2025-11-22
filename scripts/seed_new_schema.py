"""Seed database with data for new schema (OEM Products, Test Pricing)

Usage:
    python scripts/seed_new_schema.py

This script populates:
    1. OEM Manufacturers
    2. OEM Products (with specifications as JSON)
    3. Product Pricing
    4. Test Pricing (services catalog)
"""
import os
import sys
import csv
import json

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.base import SessionLocal
from app.db.models import OEMManufacturer, OEMProduct, ProductPricing, TestPricing


# =============================================================================
# Sample Test Pricing Data
# =============================================================================
TEST_PRICING_DATA = [
    # Routine Tests
    {
        "test_name": "Conductor Resistance Test",
        "test_category": "Routine",
        "description": "Measurement of DC resistance of conductor at 20°C",
        "price": 2500.0,
        "price_per": "per_sample",
        "standard_reference": "IS 8130 / IEC 60228"
    },
    {
        "test_name": "Insulation Resistance Test",
        "test_category": "Routine",
        "description": "Measurement of insulation resistance at ambient temperature",
        "price": 3000.0,
        "price_per": "per_sample",
        "standard_reference": "IS 10810 / IEC 60502"
    },
    {
        "test_name": "High Voltage Test",
        "test_category": "Routine",
        "description": "AC voltage withstand test on insulation",
        "price": 4000.0,
        "price_per": "per_sample",
        "standard_reference": "IS 7098 / IEC 60502"
    },
    {
        "test_name": "Spark Test",
        "test_category": "Routine",
        "description": "Continuous spark test during extrusion",
        "price": 1500.0,
        "price_per": "per_km",
        "standard_reference": "IS 10810"
    },
    # Type Tests
    {
        "test_name": "Partial Discharge Test",
        "test_category": "Type",
        "description": "Measurement of partial discharge inception and extinction voltage",
        "price": 25000.0,
        "price_per": "per_sample",
        "standard_reference": "IEC 60502-2"
    },
    {
        "test_name": "Bending Test",
        "test_category": "Type",
        "description": "Flexibility test - bending around mandrel",
        "price": 8000.0,
        "price_per": "per_sample",
        "standard_reference": "IS 7098 / IEC 60502"
    },
    {
        "test_name": "Tensile Strength Test",
        "test_category": "Type",
        "description": "Mechanical strength test of insulation and sheath",
        "price": 6000.0,
        "price_per": "per_sample",
        "standard_reference": "IS 5831 / IEC 60811"
    },
    {
        "test_name": "Elongation at Break Test",
        "test_category": "Type",
        "description": "Measurement of elongation before breaking",
        "price": 6000.0,
        "price_per": "per_sample",
        "standard_reference": "IS 5831 / IEC 60811"
    },
    {
        "test_name": "Hot Set Test",
        "test_category": "Type",
        "description": "Cross-linking degree verification for XLPE",
        "price": 12000.0,
        "price_per": "per_sample",
        "standard_reference": "IEC 60811-507"
    },
    {
        "test_name": "Ageing Test",
        "test_category": "Type",
        "description": "Accelerated thermal ageing test",
        "price": 15000.0,
        "price_per": "per_sample",
        "standard_reference": "IS 5831 / IEC 60811"
    },
    {
        "test_name": "Loss of Mass Test",
        "test_category": "Type",
        "description": "Weight loss measurement after heat treatment",
        "price": 5000.0,
        "price_per": "per_sample",
        "standard_reference": "IEC 60811-409"
    },
    {
        "test_name": "Shrinkage Test",
        "test_category": "Type",
        "description": "Linear shrinkage measurement after heating",
        "price": 5000.0,
        "price_per": "per_sample",
        "standard_reference": "IEC 60811-504"
    },
    # Special Tests
    {
        "test_name": "Fire Resistance Test (C Category)",
        "test_category": "Special",
        "description": "Flame propagation test - Category C",
        "price": 35000.0,
        "price_per": "per_lot",
        "standard_reference": "IS 11269 / IEC 60332-3"
    },
    {
        "test_name": "Smoke Density Test",
        "test_category": "Special",
        "description": "Light transmittance measurement during burning",
        "price": 20000.0,
        "price_per": "per_sample",
        "standard_reference": "IS 10810 / IEC 61034"
    },
    {
        "test_name": "Halogen Content Test",
        "test_category": "Special",
        "description": "Determination of halogen content in cable materials",
        "price": 15000.0,
        "price_per": "per_sample",
        "standard_reference": "IEC 60754-1"
    },
    {
        "test_name": "Toxicity Index Test",
        "test_category": "Special",
        "description": "Measurement of toxic gas emission",
        "price": 25000.0,
        "price_per": "per_sample",
        "standard_reference": "NES 713"
    },
    {
        "test_name": "Water Absorption Test",
        "test_category": "Special",
        "description": "Moisture absorption measurement",
        "price": 8000.0,
        "price_per": "per_sample",
        "standard_reference": "IEC 60811-402"
    },
    # Acceptance Tests
    {
        "test_name": "Visual Inspection",
        "test_category": "Acceptance",
        "description": "Visual examination of cable surface and markings",
        "price": 1000.0,
        "price_per": "per_lot",
        "standard_reference": "IS 7098"
    },
    {
        "test_name": "Dimensional Check",
        "test_category": "Acceptance",
        "description": "Verification of conductor, insulation, and sheath dimensions",
        "price": 3500.0,
        "price_per": "per_sample",
        "standard_reference": "IS 7098 / IEC 60502"
    },
    {
        "test_name": "Length Verification",
        "test_category": "Acceptance",
        "description": "Measurement and verification of cable length",
        "price": 500.0,
        "price_per": "per_drum",
        "standard_reference": "IS 7098"
    },
    {
        "test_name": "Marking Verification",
        "test_category": "Acceptance",
        "description": "Verification of cable markings and labels",
        "price": 500.0,
        "price_per": "per_lot",
        "standard_reference": "IS 7098"
    },
]


def seed_manufacturers():
    """Create OEM manufacturers"""
    db = SessionLocal()

    print("\n[1/4] Seeding OEM Manufacturers...")

    manufacturers = [
        {"name": "Polycab India Ltd", "website": "https://www.polycab.com"},
        {"name": "Havells India Ltd", "website": "https://www.havells.com"},
        {"name": "KEI Industries Ltd", "website": "https://www.kei-ind.com"},
        {"name": "Finolex Cables Ltd", "website": "https://www.finolex.com"},
        {"name": "RR Kabel Ltd", "website": "https://www.rrkabel.com"},
    ]

    try:
        created_count = 0
        for m in manufacturers:
            # Check if manufacturer already exists
            existing = db.query(OEMManufacturer).filter(OEMManufacturer.name == m["name"]).first()
            if not existing:
                manufacturer = OEMManufacturer(name=m["name"], website=m["website"])
                db.add(manufacturer)
                created_count += 1

        db.commit()
        print(f"      Created {created_count} manufacturers")

        # Return manufacturer mapping
        all_manufacturers = db.query(OEMManufacturer).all()
        return {m.name: m.id for m in all_manufacturers}

    except Exception as e:
        print(f"      [ERROR] {e}")
        db.rollback()
        raise
    finally:
        db.close()


def seed_oem_products(manufacturer_ids: dict):
    """Load OEM products from CSV and convert to new schema"""
    db = SessionLocal()
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "components_enhanced.csv")

    print("\n[2/4] Seeding OEM Products...")

    # Manufacturer mapping from old CSV
    csv_manufacturer_map = {
        "OEM Cables Ltd": "Polycab India Ltd",
        "Premium Wires Co": "Havells India Ltd",
        "ElectroPower Cables": "KEI Industries Ltd",
    }

    try:
        count = 0
        skipped = 0
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                # Skip comment rows (start with #)
                if row.get("sku", "").startswith("#"):
                    skipped += 1
                    continue

                # Map old manufacturer to new
                old_manufacturer = row.get("manufacturer", "OEM Cables Ltd")
                manufacturer_name = csv_manufacturer_map.get(old_manufacturer, "Polycab India Ltd")
                manufacturer_id = manufacturer_ids.get(manufacturer_name)

                if not manufacturer_id:
                    print(f"      [WARN] Unknown manufacturer: {manufacturer_name}")
                    continue

                # Parse cross_section_mm2 - handle AWG values
                cross_section = row.get("cross_section_mm2", "")
                try:
                    cross_section_val = float(cross_section) if cross_section and not cross_section.endswith("AWG") else None
                except ValueError:
                    cross_section_val = None

                # Build specifications JSON
                specifications = {
                    "voltage_kv": float(row["voltage_kv"]) if row.get("voltage_kv") else None,
                    "conductor": row.get("conductor", ""),
                    "cores": row.get("cores", ""),
                    "cross_section_mm2": cross_section_val,
                    "cross_section_raw": cross_section,  # Keep original value for AWG etc.
                    "insulation": row.get("insulation", ""),
                    "armour": row.get("armour", ""),
                    "sheath": row.get("sheath", ""),
                    "standard": row.get("standard", ""),
                    "application": row.get("application", ""),
                    "fire_rating": row.get("fire_rating", "").strip() if row.get("fire_rating") else None,
                    "temperature_rating": row.get("temperature_rating", "").strip() if row.get("temperature_rating") else None,
                }

                # Parse in_stock boolean
                in_stock_val = row.get("in_stock", "True")
                in_stock = in_stock_val.lower() in ("true", "1", "yes") if in_stock_val else True

                # Parse lead_time_days
                lead_time = row.get("lead_time_days", "7")
                try:
                    lead_time_days = int(lead_time) if lead_time else 7
                except ValueError:
                    lead_time_days = 7

                # Create OEM product with new fields
                product = OEMProduct(
                    manufacturer_id=manufacturer_id,
                    sku=row["sku"],
                    product_name=row["name"],
                    product_category=row.get("category", ""),
                    description=row.get("description", ""),
                    specifications=specifications,
                    keywords=row.get("keywords", ""),
                    in_stock=in_stock,
                    lead_time_days=lead_time_days,
                )
                db.add(product)
                db.flush()  # Get the product ID

                # Create pricing with both price_per_meter and price_per_unit
                price_per_meter = float(row["price_per_meter"]) if row.get("price_per_meter") else 0.0
                price_per_unit = float(row["price_per_unit"]) if row.get("price_per_unit") else None

                if price_per_meter > 0 or price_per_unit:
                    pricing = ProductPricing(
                        oem_product_id=product.id,
                        unit_price=price_per_meter,
                        price_per_unit=price_per_unit,
                        currency=row.get("currency", "INR"),
                        price_per="meter"
                    )
                    db.add(pricing)

                count += 1
                if count % 20 == 0:
                    print(f"      Loaded {count} products...")

            db.commit()
            print(f"      Created {count} OEM products with pricing (skipped {skipped} comment rows)")

    except Exception as e:
        print(f"      [ERROR] {e}")
        db.rollback()
        raise
    finally:
        db.close()


def seed_test_pricing():
    """Seed test/service pricing data"""
    db = SessionLocal()

    print("\n[3/4] Seeding Test Pricing...")

    try:
        count = 0
        for t in TEST_PRICING_DATA:
            # Check if test already exists
            existing = db.query(TestPricing).filter(TestPricing.test_name == t["test_name"]).first()
            if not existing:
                test = TestPricing(
                    test_name=t["test_name"],
                    test_category=t["test_category"],
                    description=t["description"],
                    price=t["price"],
                    currency="INR",
                    price_per=t["price_per"],
                    standard_reference=t.get("standard_reference")
                )
                db.add(test)
                count += 1

        db.commit()
        print(f"      Created {count} test pricing entries")

    except Exception as e:
        print(f"      [ERROR] {e}")
        db.rollback()
        raise
    finally:
        db.close()


def show_summary():
    """Show database summary"""
    db = SessionLocal()

    print("\n[4/4] Database Summary...")

    try:
        manufacturers = db.query(OEMManufacturer).count()
        products = db.query(OEMProduct).count()
        product_pricing = db.query(ProductPricing).count()
        test_pricing = db.query(TestPricing).count()

        print(f"""
      Tables populated:
        - OEM Manufacturers: {manufacturers}
        - OEM Products: {products}
        - Product Pricing: {product_pricing}
        - Test Pricing: {test_pricing}
        """)

        # Sample products
        print("      Sample OEM Products:")
        samples = db.query(OEMProduct).limit(3).all()
        for s in samples:
            specs = s.specifications or {}
            print(f"        - {s.sku}: {s.product_name}")
            print(f"          Category: {s.product_category}")
            print(f"          Specs: {specs.get('voltage_kv')}kV, {specs.get('cores')}, {specs.get('cross_section_mm2') or specs.get('cross_section_raw')}mm², {specs.get('conductor')}")
            print(f"          In Stock: {s.in_stock}, Lead Time: {s.lead_time_days} days")

        # Sample test pricing
        print("\n      Sample Test Pricing:")
        test_samples = db.query(TestPricing).limit(3).all()
        for t in test_samples:
            print(f"        - {t.test_name} ({t.test_category}): Rs.{t.price} {t.price_per}")

    finally:
        db.close()


def main():
    print("=" * 60)
    print("SEEDING NEW DATABASE SCHEMA")
    print("=" * 60)

    # Step 1: Seed manufacturers
    manufacturer_ids = seed_manufacturers()

    # Step 2: Seed OEM products
    seed_oem_products(manufacturer_ids)

    # Step 3: Seed test pricing
    seed_test_pricing()

    # Step 4: Show summary
    show_summary()

    print("\n" + "=" * 60)
    print("SEEDING COMPLETE!")
    print("=" * 60)
    print("""
Database is now ready with:
  - OEM Manufacturers (Polycab, Havells, KEI, etc.)
  - OEM Products with specifications as JSON
  - Product Pricing linked to OEM products
  - Test Pricing for all test types (Routine, Type, Special, Acceptance)

The agents can now use this data for:
  - Technical Agent: Match RFP requirements to OEM products
  - Pricing Agent: Calculate material and test costs
    """)


if __name__ == "__main__":
    main()
