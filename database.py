
from __future__ import annotations

import os
from datetime import date, datetime
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    sessionmaker,
)


class Base(DeclarativeBase):
    pass


# Prevents the starting income from being added repeatedly.
class SeedMarker(Base):
    __tablename__ = "seed_markers"

    key: Mapped[str] = mapped_column(
        String(120),
        primary_key=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    category: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        default="Other",
    )

    opening_stock: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    current_stock: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    unit_cost: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0,
    )

    selling_price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0,
    )

    # Retained for compatibility with older databases.
    # It is not shown or used in the app interface.
    low_stock_at: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )


class MoneyRecord(Base):
    __tablename__ = "money_records"

    __table_args__ = (
        Index(
            "ix_money_records_date_type",
            "record_date",
            "record_type",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    record_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    record_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    category: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        String(240),
        nullable=False,
    )

    amount: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )


class StockMovement(Base):
    __tablename__ = "stock_movements"

    __table_args__ = (
        Index(
            "ix_stock_movements_date_kind",
            "movement_date",
            "kind",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        nullable=False,
    )

    movement_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    kind: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    unit_cost: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0,
    )

    unit_price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0,
    )

    total_cost: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0,
    )

    total_revenue: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0,
    )

    note: Mapped[str] = mapped_column(
        String(240),
        nullable=False,
        default="",
    )


def get_database_url() -> str:

    url: Optional[str] = os.getenv("DATABASE_URL")

    if not url:

        try:
            import streamlit as st

            url = str(
                st.secrets.get("database_url", "")
            ).strip() or None

        except Exception:
            url = None

    if not url:
        return "sqlite:///business_data.db"

    if url.startswith("postgres://"):

        url = url.replace(
            "postgres://",
            "postgresql+psycopg://",
            1,
        )

    elif url.startswith("postgresql://"):

        url = url.replace(
            "postgresql://",
            "postgresql+psycopg://",
            1,
        )

    return url


def create_session_factory(database_url: str):

    connect_args = (
        {"check_same_thread": False}
        if database_url.startswith("sqlite")
        else {}
    )

    engine = create_engine(
        database_url,
        connect_args=connect_args,
        pool_pre_ping=True,
    )

    Base.metadata.create_all(engine)

    return sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )


def app_today():

    timezone_name = os.getenv(
        "APP_TIMEZONE",
        "Asia/Jakarta",
    )

    try:

        return datetime.now(
            ZoneInfo(timezone_name)
        ).date()

    except Exception:

        return date.today()
