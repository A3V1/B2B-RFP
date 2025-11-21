from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, Integer, Text, DateTime, func, Float, Boolean

Base = declarative_base()


class RFP(Base):
    __tablename__ = "rfps"
    id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=True)
    filepath = Column(String, nullable=True)
    text = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class Component(Base):
    """
    Enhanced product model for cables/wires with detailed specifications.
    Used by Technical Agent for spec matching.
    """
    __tablename__ = "components"

    # Basic info
    id = Column(Integer, primary_key=True, autoincrement=True)
    sku = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, index=True)
    description = Column(Text)
    category = Column(String, index=True)  # e.g., "LT Cable", "HT Cable", "Control Cable"

    # Technical specifications
    voltage_kv = Column(Float, index=True)  # Voltage rating in kV (e.g., 1.1, 11, 33)
    conductor = Column(String, index=True)  # Copper or Aluminum
    cores = Column(String)  # e.g., "1C", "2C", "3C", "4C", "3.5C"
    cross_section_mm2 = Column(Float, index=True)  # Cross-sectional area in mm²
    insulation = Column(String, index=True)  # PVC, XLPE, EPR, etc.
    armour = Column(String)  # Unarmoured, SWA (Steel Wire Armour), AWA (Aluminum Wire Armour)
    sheath = Column(String)  # PVC, LSZH, etc.
    standard = Column(String)  # IS:1554, IS:7098, IEC, BS, etc.

    # Additional specs
    application = Column(String)  # Indoor, Outdoor, Underground, Submarine
    fire_rating = Column(String, nullable=True)  # FR, FRLS, FRLSH
    temperature_rating = Column(String, nullable=True)  # e.g., "90°C", "110°C"

    # Metadata
    manufacturer = Column(String, nullable=True)
    keywords = Column(String)

    # Pricing
    price_per_meter = Column(Float, default=0.0)  # Price per meter
    price_per_unit = Column(Float, default=0.0)  # For non-cable items
    currency = Column(String, default="INR")

    # Availability
    in_stock = Column(Boolean, default=True)
    lead_time_days = Column(Integer, default=0)


class Test(Base):
    """
    Tests and acceptance procedures required for RFPs.
    Used by Pricing Agent for cost calculation.
    """
    __tablename__ = "tests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    test_id = Column(String, unique=True, index=True, nullable=False)
    test_name = Column(String, index=True)
    category = Column(String, index=True)  # Routine, Type, Special, Acceptance
    description = Column(Text)

    # Pricing
    base_price = Column(Float, default=0.0)
    unit = Column(String)  # per_lot, per_sample, per_km, per_item
    currency = Column(String, default="INR")

    # Additional info
    duration_hours = Column(Integer, nullable=True)  # How long the test takes
    standard = Column(String, nullable=True)  # IS, IEC, BS standard
    equipment_required = Column(String, nullable=True)
