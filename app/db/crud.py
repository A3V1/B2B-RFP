from typing import Optional
from app.db.base import SessionLocal
from app.db.models import RFP, Component


def create_rfp_record(rfp_id: str, filename: str, filepath: str) -> RFP:
    db = SessionLocal()
    try:
        r = RFP(id=rfp_id, filename=filename, filepath=filepath)
        db.add(r)
        db.commit()
        db.refresh(r)
        return r
    finally:
        db.close()


def get_rfp_by_id(rfp_id: str) -> Optional[RFP]:
    db = SessionLocal()
    try:
        return db.query(RFP).filter(RFP.id == rfp_id).first()
    finally:
        db.close()


def update_rfp_text(rfp_id: str, text: str) -> Optional[RFP]:
    db = SessionLocal()
    try:
        r = db.query(RFP).filter(RFP.id == rfp_id).first()
        if not r:
            return None
        r.text = text
        db.add(r)
        db.commit()
        db.refresh(r)
        return r
    finally:
        db.close()


def create_component(name: str, description: str, keywords: str = None, price: float = 0.0) -> Component:
    db = SessionLocal()
    try:
        c = Component(name=name, description=description, keywords=keywords or "", price=price)
        db.add(c)
        db.commit()
        db.refresh(c)
        return c
    finally:
        db.close()


def bulk_insert_components_from_csv(csv_path: str) -> int:
    import csv
    db = SessionLocal()
    count = 0
    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    price = float(row.get("price") or 0)
                except Exception:
                    price = 0.0
                c = Component(
                    name=row.get("name"),
                    description=row.get("description"),
                    keywords=row.get("keywords"),
                    price=price,
                )
                db.add(c)
                count += 1
            db.commit()
        return count
    finally:
        db.close()
