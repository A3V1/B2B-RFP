from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from app.db.base import SessionLocal
from app.db.models import (
    RFP, RFPProduct, RFPTest,
    OEMManufacturer, OEMProduct, ProductPricing, TestPricing,
    ProductMatch, RFPResponse, ResponseLineItem, ResponseTest
)


# =============================================================================
# Database Session Helper
# =============================================================================

def get_db() -> Session:
    """Get a database session."""
    return SessionLocal()


# =============================================================================
# RFP CRUD Operations
# =============================================================================

def create_rfp(
    rfp_number: str,
    title: str,
    issuing_organization: str = None,
    due_date: datetime = None,
    document_path: str = None,
    extracted_text: str = None
) -> RFP:
    """Create a new RFP record."""
    db = get_db()
    try:
        rfp = RFP(
            rfp_number=rfp_number,
            title=title,
            issuing_organization=issuing_organization,
            due_date=due_date,
            document_path=document_path,
            extracted_text=extracted_text
        )
        db.add(rfp)
        db.commit()
        db.refresh(rfp)
        return rfp
    finally:
        db.close()


def get_rfp_by_id(rfp_id: int) -> Optional[RFP]:
    """Get RFP by ID with all related data."""
    db = get_db()
    try:
        return db.query(RFP).options(
            joinedload(RFP.products),
            joinedload(RFP.tests),
            joinedload(RFP.responses)
        ).filter(RFP.id == rfp_id).first()
    finally:
        db.close()


def get_rfp_by_number(rfp_number: str) -> Optional[RFP]:
    """Get RFP by RFP number."""
    db = get_db()
    try:
        return db.query(RFP).filter(RFP.rfp_number == rfp_number).first()
    finally:
        db.close()


def get_all_rfps() -> List[RFP]:
    """Get all RFPs."""
    db = get_db()
    try:
        return db.query(RFP).order_by(RFP.created_at.desc()).all()
    finally:
        db.close()


def update_rfp_status(rfp_id: int, status: str) -> Optional[RFP]:
    """Update RFP status."""
    db = get_db()
    try:
        rfp = db.query(RFP).filter(RFP.id == rfp_id).first()
        if rfp:
            rfp.status = status
            db.commit()
            db.refresh(rfp)
        return rfp
    finally:
        db.close()


def update_rfp_summary(rfp_id: int, summary: str) -> Optional[RFP]:
    """Update RFP summary (from Main Agent)."""
    db = get_db()
    try:
        rfp = db.query(RFP).filter(RFP.id == rfp_id).first()
        if rfp:
            rfp.summary = summary
            db.commit()
            db.refresh(rfp)
        return rfp
    finally:
        db.close()


def update_rfp_extracted_text(rfp_id: int, text: str) -> Optional[RFP]:
    """Update RFP extracted text."""
    db = get_db()
    try:
        rfp = db.query(RFP).filter(RFP.id == rfp_id).first()
        if rfp:
            rfp.extracted_text = text
            db.commit()
            db.refresh(rfp)
        return rfp
    finally:
        db.close()


# =============================================================================
# RFP Products CRUD Operations
# =============================================================================

def create_rfp_product(
    rfp_id: int,
    product_name: str,
    product_category: str = None,
    quantity: float = 1,
    unit: str = "units",
    specifications: Dict[str, Any] = None
) -> RFPProduct:
    """Create a new RFP product (Scope of Supply item)."""
    db = get_db()
    try:
        product = RFPProduct(
            rfp_id=rfp_id,
            product_name=product_name,
            product_category=product_category,
            quantity=quantity,
            unit=unit,
            specifications=specifications
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        return product
    finally:
        db.close()


def get_rfp_products(rfp_id: int) -> List[RFPProduct]:
    """Get all products for an RFP."""
    db = get_db()
    try:
        return db.query(RFPProduct).filter(RFPProduct.rfp_id == rfp_id).all()
    finally:
        db.close()


def bulk_create_rfp_products(rfp_id: int, products: List[Dict[str, Any]]) -> List[RFPProduct]:
    """Bulk create RFP products."""
    db = get_db()
    try:
        created = []
        for p in products:
            product = RFPProduct(
                rfp_id=rfp_id,
                product_name=p.get("product_name"),
                product_category=p.get("product_category"),
                quantity=p.get("quantity", 1),
                unit=p.get("unit", "units"),
                specifications=p.get("specifications")
            )
            db.add(product)
            created.append(product)
        db.commit()
        for product in created:
            db.refresh(product)
        return created
    finally:
        db.close()


# =============================================================================
# RFP Tests CRUD Operations
# =============================================================================

def create_rfp_test(
    rfp_id: int,
    test_name: str,
    test_type: str = None,
    description: str = None,
    standard_reference: str = None
) -> RFPTest:
    """Create a new RFP test requirement."""
    db = get_db()
    try:
        test = RFPTest(
            rfp_id=rfp_id,
            test_name=test_name,
            test_type=test_type,
            description=description,
            standard_reference=standard_reference
        )
        db.add(test)
        db.commit()
        db.refresh(test)
        return test
    finally:
        db.close()


def get_rfp_tests(rfp_id: int) -> List[RFPTest]:
    """Get all tests for an RFP."""
    db = get_db()
    try:
        return db.query(RFPTest).filter(RFPTest.rfp_id == rfp_id).all()
    finally:
        db.close()


def bulk_create_rfp_tests(rfp_id: int, tests: List[Dict[str, Any]]) -> List[RFPTest]:
    """Bulk create RFP tests."""
    db = get_db()
    try:
        created = []
        for t in tests:
            test = RFPTest(
                rfp_id=rfp_id,
                test_name=t.get("test_name"),
                test_type=t.get("test_type"),
                description=t.get("description"),
                standard_reference=t.get("standard_reference")
            )
            db.add(test)
            created.append(test)
        db.commit()
        for test in created:
            db.refresh(test)
        return created
    finally:
        db.close()


# =============================================================================
# OEM Manufacturer CRUD Operations
# =============================================================================

def create_manufacturer(name: str, website: str = None) -> OEMManufacturer:
    """Create a new OEM manufacturer."""
    db = get_db()
    try:
        manufacturer = OEMManufacturer(name=name, website=website)
        db.add(manufacturer)
        db.commit()
        db.refresh(manufacturer)
        return manufacturer
    finally:
        db.close()


def get_manufacturer_by_name(name: str) -> Optional[OEMManufacturer]:
    """Get manufacturer by name."""
    db = get_db()
    try:
        return db.query(OEMManufacturer).filter(OEMManufacturer.name == name).first()
    finally:
        db.close()


def get_or_create_manufacturer(name: str, website: str = None) -> OEMManufacturer:
    """Get existing manufacturer or create new one."""
    db = get_db()
    try:
        manufacturer = db.query(OEMManufacturer).filter(OEMManufacturer.name == name).first()
        if not manufacturer:
            manufacturer = OEMManufacturer(name=name, website=website)
            db.add(manufacturer)
            db.commit()
            db.refresh(manufacturer)
        return manufacturer
    finally:
        db.close()


def get_all_manufacturers() -> List[OEMManufacturer]:
    """Get all manufacturers."""
    db = get_db()
    try:
        return db.query(OEMManufacturer).all()
    finally:
        db.close()


# =============================================================================
# OEM Product CRUD Operations
# =============================================================================

def create_oem_product(
    manufacturer_id: int,
    sku: str,
    product_name: str,
    product_category: str = None,
    specifications: Dict[str, Any] = None,
    datasheet_url: str = None,
    datasheet_path: str = None
) -> OEMProduct:
    """Create a new OEM product."""
    db = get_db()
    try:
        product = OEMProduct(
            manufacturer_id=manufacturer_id,
            sku=sku,
            product_name=product_name,
            product_category=product_category,
            specifications=specifications,
            datasheet_url=datasheet_url,
            datasheet_path=datasheet_path
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        return product
    finally:
        db.close()


def get_oem_product_by_sku(sku: str) -> Optional[OEMProduct]:
    """Get OEM product by SKU."""
    db = get_db()
    try:
        return db.query(OEMProduct).filter(OEMProduct.sku == sku).first()
    finally:
        db.close()


def get_oem_products_by_category(category: str) -> List[OEMProduct]:
    """Get OEM products by category."""
    db = get_db()
    try:
        return db.query(OEMProduct).filter(OEMProduct.product_category == category).all()
    finally:
        db.close()


def get_all_oem_products() -> List[OEMProduct]:
    """Get all OEM products with manufacturer and pricing."""
    db = get_db()
    try:
        return db.query(OEMProduct).options(
            joinedload(OEMProduct.manufacturer),
            joinedload(OEMProduct.pricing)
        ).all()
    finally:
        db.close()


def search_oem_products(search_term: str) -> List[OEMProduct]:
    """Search OEM products by name or SKU."""
    db = get_db()
    try:
        return db.query(OEMProduct).filter(
            (OEMProduct.product_name.ilike(f"%{search_term}%")) |
            (OEMProduct.sku.ilike(f"%{search_term}%"))
        ).all()
    finally:
        db.close()


# =============================================================================
# Pricing CRUD Operations
# =============================================================================

def create_product_pricing(
    oem_product_id: int,
    unit_price: float,
    currency: str = "INR",
    price_per: str = "unit"
) -> ProductPricing:
    """Create pricing for an OEM product."""
    db = get_db()
    try:
        pricing = ProductPricing(
            oem_product_id=oem_product_id,
            unit_price=unit_price,
            currency=currency,
            price_per=price_per
        )
        db.add(pricing)
        db.commit()
        db.refresh(pricing)
        return pricing
    finally:
        db.close()


def get_product_pricing(oem_product_id: int) -> Optional[ProductPricing]:
    """Get pricing for an OEM product."""
    db = get_db()
    try:
        return db.query(ProductPricing).filter(ProductPricing.oem_product_id == oem_product_id).first()
    finally:
        db.close()


def create_test_pricing(
    test_name: str,
    test_category: str,
    price: float,
    currency: str = "INR",
    price_per: str = "per_sample",
    description: str = None,
    standard_reference: str = None
) -> TestPricing:
    """Create a test pricing entry."""
    db = get_db()
    try:
        test_pricing = TestPricing(
            test_name=test_name,
            test_category=test_category,
            price=price,
            currency=currency,
            price_per=price_per,
            description=description,
            standard_reference=standard_reference
        )
        db.add(test_pricing)
        db.commit()
        db.refresh(test_pricing)
        return test_pricing
    finally:
        db.close()


def get_test_pricing_by_name(test_name: str) -> Optional[TestPricing]:
    """Get test pricing by test name."""
    db = get_db()
    try:
        return db.query(TestPricing).filter(TestPricing.test_name == test_name).first()
    finally:
        db.close()


def get_all_test_pricing() -> List[TestPricing]:
    """Get all test pricing entries."""
    db = get_db()
    try:
        return db.query(TestPricing).all()
    finally:
        db.close()


# =============================================================================
# Product Match CRUD Operations (Technical Agent)
# =============================================================================

def create_product_match(
    rfp_product_id: int,
    oem_product_id: int,
    rank: int,
    spec_match_percentage: float,
    spec_comparison: Dict[str, Any] = None,
    is_selected: bool = False
) -> ProductMatch:
    """Create a product match (Technical Agent recommendation)."""
    db = get_db()
    try:
        match = ProductMatch(
            rfp_product_id=rfp_product_id,
            oem_product_id=oem_product_id,
            rank=rank,
            spec_match_percentage=spec_match_percentage,
            spec_comparison=spec_comparison,
            is_selected=is_selected
        )
        db.add(match)
        db.commit()
        db.refresh(match)
        return match
    finally:
        db.close()


def get_matches_for_rfp_product(rfp_product_id: int) -> List[ProductMatch]:
    """Get all matches for an RFP product, ordered by rank."""
    db = get_db()
    try:
        return db.query(ProductMatch).options(
            joinedload(ProductMatch.oem_product)
        ).filter(
            ProductMatch.rfp_product_id == rfp_product_id
        ).order_by(ProductMatch.rank).all()
    finally:
        db.close()


def select_product_match(match_id: int) -> Optional[ProductMatch]:
    """Mark a product match as selected."""
    db = get_db()
    try:
        match = db.query(ProductMatch).filter(ProductMatch.id == match_id).first()
        if match:
            # Deselect other matches for the same RFP product
            db.query(ProductMatch).filter(
                ProductMatch.rfp_product_id == match.rfp_product_id
            ).update({"is_selected": False})
            match.is_selected = True
            db.commit()
            db.refresh(match)
        return match
    finally:
        db.close()


def bulk_create_product_matches(matches: List[Dict[str, Any]]) -> List[ProductMatch]:
    """Bulk create product matches."""
    db = get_db()
    try:
        created = []
        for m in matches:
            match = ProductMatch(
                rfp_product_id=m.get("rfp_product_id"),
                oem_product_id=m.get("oem_product_id"),
                rank=m.get("rank"),
                spec_match_percentage=m.get("spec_match_percentage"),
                spec_comparison=m.get("spec_comparison"),
                is_selected=m.get("is_selected", False)
            )
            db.add(match)
            created.append(match)
        db.commit()
        for match in created:
            db.refresh(match)
        return created
    finally:
        db.close()


# =============================================================================
# RFP Response CRUD Operations (Main Agent Output)
# =============================================================================

def create_rfp_response(
    rfp_id: int,
    status: str = "draft",
    total_material_cost: float = 0.0,
    total_test_cost: float = 0.0,
    response_summary: str = None
) -> RFPResponse:
    """Create an RFP response."""
    db = get_db()
    try:
        response = RFPResponse(
            rfp_id=rfp_id,
            status=status,
            total_material_cost=total_material_cost,
            total_test_cost=total_test_cost,
            total_cost=total_material_cost + total_test_cost,
            response_summary=response_summary
        )
        db.add(response)
        db.commit()
        db.refresh(response)
        return response
    finally:
        db.close()


def get_rfp_response(rfp_id: int) -> Optional[RFPResponse]:
    """Get the latest RFP response for an RFP."""
    db = get_db()
    try:
        return db.query(RFPResponse).options(
            joinedload(RFPResponse.line_items),
            joinedload(RFPResponse.tests)
        ).filter(RFPResponse.rfp_id == rfp_id).order_by(RFPResponse.created_at.desc()).first()
    finally:
        db.close()


def update_rfp_response_costs(
    response_id: int,
    total_material_cost: float,
    total_test_cost: float
) -> Optional[RFPResponse]:
    """Update RFP response costs."""
    db = get_db()
    try:
        response = db.query(RFPResponse).filter(RFPResponse.id == response_id).first()
        if response:
            response.total_material_cost = total_material_cost
            response.total_test_cost = total_test_cost
            response.total_cost = total_material_cost + total_test_cost
            db.commit()
            db.refresh(response)
        return response
    finally:
        db.close()


def create_response_line_item(
    rfp_response_id: int,
    rfp_product_id: int,
    oem_product_id: int,
    quantity: float,
    unit_price: float
) -> ResponseLineItem:
    """Create a response line item."""
    db = get_db()
    try:
        line_item = ResponseLineItem(
            rfp_response_id=rfp_response_id,
            rfp_product_id=rfp_product_id,
            oem_product_id=oem_product_id,
            quantity=quantity,
            unit_price=unit_price,
            total_price=quantity * unit_price
        )
        db.add(line_item)
        db.commit()
        db.refresh(line_item)
        return line_item
    finally:
        db.close()


def create_response_test(
    rfp_response_id: int,
    rfp_test_id: int,
    test_name: str,
    price: float
) -> ResponseTest:
    """Create a response test entry."""
    db = get_db()
    try:
        response_test = ResponseTest(
            rfp_response_id=rfp_response_id,
            rfp_test_id=rfp_test_id,
            test_name=test_name,
            price=price
        )
        db.add(response_test)
        db.commit()
        db.refresh(response_test)
        return response_test
    finally:
        db.close()


# =============================================================================
# Utility Functions
# =============================================================================

def delete_rfp(rfp_id: int) -> bool:
    """Delete an RFP and all related data (cascade)."""
    db = get_db()
    try:
        rfp = db.query(RFP).filter(RFP.id == rfp_id).first()
        if rfp:
            db.delete(rfp)
            db.commit()
            return True
        return False
    finally:
        db.close()


def get_rfp_with_all_data(rfp_id: int) -> Optional[Dict[str, Any]]:
    """Get RFP with all related data as a dictionary."""
    db = get_db()
    try:
        rfp = db.query(RFP).options(
            joinedload(RFP.products).joinedload(RFPProduct.matches).joinedload(ProductMatch.oem_product),
            joinedload(RFP.tests),
            joinedload(RFP.responses).joinedload(RFPResponse.line_items),
            joinedload(RFP.responses).joinedload(RFPResponse.tests)
        ).filter(RFP.id == rfp_id).first()

        if not rfp:
            return None

        return {
            "id": rfp.id,
            "rfp_number": rfp.rfp_number,
            "title": rfp.title,
            "issuing_organization": rfp.issuing_organization,
            "due_date": rfp.due_date,
            "status": rfp.status,
            "summary": rfp.summary,
            "products": [
                {
                    "id": p.id,
                    "product_name": p.product_name,
                    "product_category": p.product_category,
                    "quantity": p.quantity,
                    "unit": p.unit,
                    "specifications": p.specifications,
                    "matches": [
                        {
                            "id": m.id,
                            "rank": m.rank,
                            "spec_match_percentage": m.spec_match_percentage,
                            "is_selected": m.is_selected,
                            "oem_product": {
                                "sku": m.oem_product.sku,
                                "product_name": m.oem_product.product_name
                            } if m.oem_product else None
                        }
                        for m in p.matches
                    ]
                }
                for p in rfp.products
            ],
            "tests": [
                {
                    "id": t.id,
                    "test_name": t.test_name,
                    "test_type": t.test_type,
                    "standard_reference": t.standard_reference
                }
                for t in rfp.tests
            ],
            "responses": [
                {
                    "id": r.id,
                    "status": r.status,
                    "total_material_cost": r.total_material_cost,
                    "total_test_cost": r.total_test_cost,
                    "total_cost": r.total_cost,
                    "response_summary": r.response_summary
                }
                for r in rfp.responses
            ]
        }
    finally:
        db.close()
