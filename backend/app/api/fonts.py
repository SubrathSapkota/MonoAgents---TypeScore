"""Font catalog endpoints — read-only access to the master font database."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.db.models import Font, FontLicense

router = APIRouter()


# ── Response schemas ──────────────────────────────────────────────────────────

class LicenseItemSchema(BaseModel):
    name: str
    description: str
    link: Optional[str] = None


class FontLicenseSchema(BaseModel):
    id: int
    license_type: str
    can_use: List[LicenseItemSchema]
    cannot_use: List[LicenseItemSchema]
    description: Optional[str]
    eula_url: Optional[str]


class FontSummarySchema(BaseModel):
    id: int
    name: str
    foundry: Optional[str]
    category: Optional[str]
    description: Optional[str]
    license_types: List[str]  # available license types in catalog


class FontDetailSchema(FontSummarySchema):
    licenses: List[FontLicenseSchema]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=List[FontSummarySchema])
async def list_fonts(
    q: Optional[str] = Query(None, description="Search by name or foundry"),
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Font).options(selectinload(Font.licenses)).order_by(Font.name)
    if q:
        stmt = stmt.where(
            or_(Font.name.ilike(f"%{q}%"), Font.foundry.ilike(f"%{q}%"))
        )
    if category:
        stmt = stmt.where(Font.category == category)

    result = await db.execute(stmt)
    fonts = result.scalars().all()

    return [
        FontSummarySchema(
            id=f.id,
            name=f.name,
            foundry=f.foundry,
            category=f.category,
            description=f.description,
            license_types=[lic.license_type for lic in f.licenses],
        )
        for f in fonts
    ]


@router.get("/{font_id}", response_model=FontDetailSchema)
async def get_font(font_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Font).options(selectinload(Font.licenses)).where(Font.id == font_id)
    )
    font = result.scalar_one_or_none()
    if not font:
        raise HTTPException(status_code=404, detail="Font not found")

    return FontDetailSchema(
        id=font.id,
        name=font.name,
        foundry=font.foundry,
        category=font.category,
        description=font.description,
        license_types=[lic.license_type for lic in font.licenses],
        licenses=[
            FontLicenseSchema(
                id=lic.id,
                license_type=lic.license_type,
                can_use=lic.can_use,
                cannot_use=lic.cannot_use,
                description=lic.description,
                eula_url=lic.eula_url,
            )
            for lic in font.licenses
        ],
    )
