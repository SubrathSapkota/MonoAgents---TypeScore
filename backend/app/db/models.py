from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    DateTime, ForeignKey, Integer, Numeric, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, server_default=func.now()
    )

    fonts: Mapped[list["UserFont"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    scans: Mapped[list["ScanResult"]] = relationship(back_populates="user")


class Font(Base):
    __tablename__ = "fonts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    foundry: Mapped[Optional[str]] = mapped_column(String(255))
    category: Mapped[Optional[str]] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, server_default=func.now()
    )

    licenses: Mapped[list["FontLicense"]] = relationship(back_populates="font", cascade="all, delete-orphan")
    user_fonts: Mapped[list["UserFont"]] = relationship(back_populates="catalog_font")


class FontLicense(Base):
    __tablename__ = "font_licenses"
    __table_args__ = (UniqueConstraint("font_id", "license_type"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    font_id: Mapped[int] = mapped_column(ForeignKey("fonts.id", ondelete="CASCADE"), nullable=False)
    license_type: Mapped[str] = mapped_column(String(50), nullable=False)
    can_use: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    cannot_use: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    description: Mapped[Optional[str]] = mapped_column(Text)
    eula_url: Mapped[Optional[str]] = mapped_column(String(500))

    font: Mapped["Font"] = relationship(back_populates="licenses")


class UserFont(Base):
    __tablename__ = "user_fonts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    font_id: Mapped[Optional[int]] = mapped_column(ForeignKey("fonts.id", ondelete="SET NULL"))
    custom_font_name: Mapped[Optional[str]] = mapped_column(String(255))
    license_type: Mapped[Optional[str]] = mapped_column(String(50))
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="manual")
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="fonts")
    catalog_font: Mapped[Optional["Font"]] = relationship(back_populates="user_fonts")


class ScanResult(Base):
    __tablename__ = "scan_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    overall_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 1))
    brand_consistency: Mapped[Optional[float]] = mapped_column(Numeric(5, 1))
    license_compliance: Mapped[Optional[float]] = mapped_column(Numeric(5, 1))
    performance: Mapped[Optional[float]] = mapped_column(Numeric(5, 1))
    accessibility: Mapped[Optional[float]] = mapped_column(Numeric(5, 1))
    developer_experience: Mapped[Optional[float]] = mapped_column(Numeric(5, 1))
    issues: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    raw_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, server_default=func.now()
    )

    user: Mapped[Optional["User"]] = relationship(back_populates="scans")


class BrandGuideline(Base):
    """Placeholder for Phase 2 — PDF brand guideline uploads."""
    __tablename__ = "brand_guidelines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(Integer)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, server_default=func.now()
    )
    parsed_data: Mapped[Optional[dict]] = mapped_column(JSON)
