from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, String, Integer, Text, DateTime, func, Float, Boolean, ForeignKey, JSON

Base = declarative_base()


# =============================================================================
# 1. RFP MANAGEMENT
# =============================================================================

class RFP(Base):
    """
    Stores uploaded RFP documents and their metadata.
    """
    __tablename__ = "rfps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rfp_number = Column(String, unique=True, index=True)  # Unique RFP identifier
    title = Column(String, index=True)
    issuing_organization = Column(String)
    due_date = Column(DateTime, nullable=True)
    status = Column(String, default="uploaded")  # uploaded, processing, completed
    summary = Column(Text, nullable=True)  # Main Agent's summary
    document_path = Column(String, nullable=True)  # Path to uploaded RFP document
    extracted_text = Column(Text, nullable=True)  # Extracted text from document
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    products = relationship("RFPProduct", back_populates="rfp", cascade="all, delete-orphan")
    tests = relationship("RFPTest", back_populates="rfp", cascade="all, delete-orphan")
    responses = relationship("RFPResponse", back_populates="rfp", cascade="all, delete-orphan")


class RFPProduct(Base):
    """
    Products required in RFP's Scope of Supply.
    Extracted from the RFP document.
    """
    __tablename__ = "rfp_products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rfp_id = Column(Integer, ForeignKey("rfps.id", ondelete="CASCADE"), nullable=False)
    product_name = Column(String, nullable=False)
    product_category = Column(String)  # e.g., 'cable', 'connector', etc.
    quantity = Column(Float, default=1)
    unit = Column(String, default="units")  # meters, units, km
    specifications = Column(JSON, nullable=True)  # {"voltage": "1kV", "conductor": "copper", ...}
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    rfp = relationship("RFP", back_populates="products")
    matches = relationship("ProductMatch", back_populates="rfp_product", cascade="all, delete-orphan")


class RFPTest(Base):
    """
    Tests/Acceptance criteria required by the RFP.
    """
    __tablename__ = "rfp_tests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rfp_id = Column(Integer, ForeignKey("rfps.id", ondelete="CASCADE"), nullable=False)
    test_name = Column(String, nullable=False)
    test_type = Column(String)  # type_test, routine_test, acceptance_test
    description = Column(Text, nullable=True)
    standard_reference = Column(String, nullable=True)  # e.g., 'IEC 60502', 'IS 7098'
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    rfp = relationship("RFP", back_populates="tests")


# =============================================================================
# 2. OEM PRODUCT CATALOG (Technical Agent Repository)
# =============================================================================

class OEMManufacturer(Base):
    """
    OEM Manufacturers in the product catalog.
    """
    __tablename__ = "oem_manufacturers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)  # e.g., 'Polycab', 'Havells', 'KEI'
    website = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    products = relationship("OEMProduct", back_populates="manufacturer", cascade="all, delete-orphan")


class OEMProduct(Base):
    """
    OEM Product datasheets repository.
    Used by Technical Agent for spec matching.
    """
    __tablename__ = "oem_products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    manufacturer_id = Column(Integer, ForeignKey("oem_manufacturers.id", ondelete="CASCADE"), nullable=False)
    sku = Column(String, unique=True, index=True, nullable=False)  # Product SKU code
    product_name = Column(String, index=True)
    product_category = Column(String, index=True)  # e.g., "LT Cable", "HT Cable", "Control Cable"
    description = Column(Text, nullable=True)  # Product description
    specifications = Column(JSON, nullable=True)  # {"voltage": "1.1kV", "conductor": "copper", ...}
    keywords = Column(String, nullable=True)  # Search keywords separated by semicolons
    in_stock = Column(Boolean, default=True)  # Stock availability
    lead_time_days = Column(Integer, default=7)  # Lead time in days
    datasheet_url = Column(String, nullable=True)
    datasheet_path = Column(String, nullable=True)  # Local path to downloaded datasheet
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    manufacturer = relationship("OEMManufacturer", back_populates="products")
    pricing = relationship("ProductPricing", back_populates="oem_product", uselist=False, cascade="all, delete-orphan")
    matches = relationship("ProductMatch", back_populates="oem_product")


# =============================================================================
# 3. PRICING DATA (Pricing Agent)
# =============================================================================

class ProductPricing(Base):
    """
    Pricing table for OEM products.
    Used by Pricing Agent.
    """
    __tablename__ = "product_pricing"

    id = Column(Integer, primary_key=True, autoincrement=True)
    oem_product_id = Column(Integer, ForeignKey("oem_products.id", ondelete="CASCADE"), nullable=False)
    unit_price = Column(Float, nullable=False)  # Price per meter
    price_per_unit = Column(Float, nullable=True)  # Price per unit/drum
    currency = Column(String, default="INR")
    price_per = Column(String, default="unit")  # meter, unit, km
    valid_from = Column(DateTime, nullable=True)
    valid_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    oem_product = relationship("OEMProduct", back_populates="pricing")


class TestPricing(Base):
    """
    Pricing table for tests/services.
    Used by Pricing Agent.
    """
    __tablename__ = "test_pricing"

    id = Column(Integer, primary_key=True, autoincrement=True)
    test_name = Column(String, unique=True, index=True, nullable=False)
    test_category = Column(String)  # electrical, mechanical, thermal, etc.
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    currency = Column(String, default="INR")
    price_per = Column(String, default="per_sample")  # per_sample, per_lot, fixed
    standard_reference = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


# =============================================================================
# 4. MATCHING & RESPONSE (Agent Outputs)
# =============================================================================

class ProductMatch(Base):
    """
    Technical Agent's product recommendations.
    Maps RFP products to OEM products with spec match percentage.
    """
    __tablename__ = "product_matches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rfp_product_id = Column(Integer, ForeignKey("rfp_products.id", ondelete="CASCADE"), nullable=False)
    oem_product_id = Column(Integer, ForeignKey("oem_products.id", ondelete="CASCADE"), nullable=False)
    rank = Column(Integer, nullable=False)  # 1, 2, 3 (top 3 recommendations)
    spec_match_percentage = Column(Float, nullable=False)  # 0-100%
    spec_comparison = Column(JSON, nullable=True)  # Detailed comparison of each spec
    is_selected = Column(Boolean, default=False)  # Final selection for response
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    rfp_product = relationship("RFPProduct", back_populates="matches")
    oem_product = relationship("OEMProduct", back_populates="matches")


class RFPResponse(Base):
    """
    Final consolidated RFP response.
    Created by Main Agent after aggregating all agent outputs.
    """
    __tablename__ = "rfp_responses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rfp_id = Column(Integer, ForeignKey("rfps.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, default="draft")  # draft, review, final, submitted
    total_material_cost = Column(Float, default=0.0)
    total_test_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    currency = Column(String, default="INR")
    response_summary = Column(Text, nullable=True)  # AI-generated response summary
    created_at = Column(DateTime, server_default=func.now())
    submitted_at = Column(DateTime, nullable=True)

    # Relationships
    rfp = relationship("RFP", back_populates="responses")
    line_items = relationship("ResponseLineItem", back_populates="rfp_response", cascade="all, delete-orphan")
    tests = relationship("ResponseTest", back_populates="rfp_response", cascade="all, delete-orphan")


class ResponseLineItem(Base):
    """
    Line items (products) in the final RFP response.
    """
    __tablename__ = "response_line_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rfp_response_id = Column(Integer, ForeignKey("rfp_responses.id", ondelete="CASCADE"), nullable=False)
    rfp_product_id = Column(Integer, ForeignKey("rfp_products.id", ondelete="SET NULL"), nullable=True)
    oem_product_id = Column(Integer, ForeignKey("oem_products.id", ondelete="SET NULL"), nullable=True)
    quantity = Column(Float, default=1)
    unit_price = Column(Float, default=0.0)
    total_price = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    rfp_response = relationship("RFPResponse", back_populates="line_items")


class ResponseTest(Base):
    """
    Tests included in the final RFP response with pricing.
    """
    __tablename__ = "response_tests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rfp_response_id = Column(Integer, ForeignKey("rfp_responses.id", ondelete="CASCADE"), nullable=False)
    rfp_test_id = Column(Integer, ForeignKey("rfp_tests.id", ondelete="SET NULL"), nullable=True)
    test_name = Column(String, nullable=False)
    price = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    rfp_response = relationship("RFPResponse", back_populates="tests")
