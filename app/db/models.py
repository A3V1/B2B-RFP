from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, Integer, Text, DateTime, func, Float

Base = declarative_base()


class RFP(Base):
    __tablename__ = "rfps"
    id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=True)
    filepath = Column(String, nullable=True)
    text = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class Component(Base):
    __tablename__ = "components"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, index=True)
    description = Column(Text)
    keywords = Column(String)
    price = Column(Float, default=0.0)
