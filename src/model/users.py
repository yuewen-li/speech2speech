from src.model.base import Base
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from datetime import datetime


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    plan = Column(String, default="trial")
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True)
    premium_start_date = Column(DateTime, nullable=True)
