"""User font library endpoints — manage the fonts a user has acquired."""

import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db.models import Font, FontLicense, User, UserFont

router = APIRouter()

LICENSE_TYPES = {"desktop", "webfont", "app", "edoc", "digital_ad"}

FONT_EXTENSIONS = {".ttf", ".otf", ".woff", ".woff2", ".eot", ".svg"}

# Common font variant suffixes to strip when extracting family name from filename
_VARIANT_PATTERN = re.compile(
    r"[-_ ](regular|bold|italic|light|medium|semibold|black|thin|extralight|"
    r"extrabold|condensed|expanded|oblique|roman|book|heavy|narrow|"
    r"bolditalic|lightitalic|mediumitalic|blackitalic)$",
    re.IGNORECASE,
)


def _extract_font_name(filename: str) -> str:
    """Strip extension and style variants to get a clean family name."""
    name = filename
    for ext in FONT_EXTENSIONS:
        if name.lower().endswith(ext):
            name = name[: -len(ext)]
            break
    name = _VARIANT_PATTERN.sub("", name).strip("-_ ")
    # Convert CamelCase or PascalCase-like runs to spaced words if no separators
    if "-" not in name and "_" not in name and " " not in name:
        name = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name)
    return name.replace("-", " ").replace("_", " ").strip()


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


class UserFontSchema(BaseModel):
    id: int
    font_name: str
    foundry: Optional[str]
    category: Optional[str]
    license_type: Optional[str]
    source: str
    catalog_id: Optional[int]
    has_license_data: bool
    added_at: str


class UserFontDetailSchema(UserFontSchema):
    description: Optional[str]
    licenses: List[FontLicenseSchema]


class AddFontRequest(BaseModel):
    font_name: Optional[str] = None  # manual entry
    font_id: Optional[int] = None    # from catalog
    license_type: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _find_catalog_font(name: str, db: AsyncSession) -> Optional[Font]:
    """Try to match a font name against the catalog (case-insensitive)."""
    result = await db.execute(
        select(Font).options(selectinload(Font.licenses)).where(Font.name.ilike(name))
    )
    return result.scalar_one_or_none()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=List[UserFontSchema])
async def list_user_fonts(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserFont)
        .options(selectinload(UserFont.catalog_font).selectinload(Font.licenses))
        .where(UserFont.user_id == user.id)
        .order_by(UserFont.added_at.desc())
    )
    user_fonts = result.scalars().all()

    out = []
    for uf in user_fonts:
        cf = uf.catalog_font
        out.append(UserFontSchema(
            id=uf.id,
            font_name=cf.name if cf else uf.custom_font_name,
            foundry=cf.foundry if cf else None,
            category=cf.category if cf else None,
            license_type=uf.license_type,
            source=uf.source,
            catalog_id=uf.font_id,
            has_license_data=bool(cf and cf.licenses),
            added_at=uf.added_at.isoformat(),
        ))
    return out


@router.get("/{user_font_id}", response_model=UserFontDetailSchema)
async def get_user_font(
    user_font_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserFont)
        .options(selectinload(UserFont.catalog_font).selectinload(Font.licenses))
        .where(UserFont.id == user_font_id, UserFont.user_id == user.id)
    )
    uf = result.scalar_one_or_none()
    if not uf:
        raise HTTPException(status_code=404, detail="Font not in your library")

    cf = uf.catalog_font
    font_name = cf.name if cf else uf.custom_font_name

    # Collect licenses: prefer license matching the user's type, else all
    licenses: list[FontLicense] = []
    if cf and cf.licenses:
        if uf.license_type:
            licenses = [l for l in cf.licenses if l.license_type == uf.license_type]
            if not licenses:
                licenses = cf.licenses
        else:
            licenses = cf.licenses

    return UserFontDetailSchema(
        id=uf.id,
        font_name=font_name,
        foundry=cf.foundry if cf else None,
        category=cf.category if cf else None,
        description=cf.description if cf else None,
        license_type=uf.license_type,
        source=uf.source,
        catalog_id=uf.font_id,
        has_license_data=bool(licenses),
        added_at=uf.added_at.isoformat(),
        licenses=[
            FontLicenseSchema(
                id=l.id,
                license_type=l.license_type,
                can_use=l.can_use,
                cannot_use=l.cannot_use,
                description=l.description,
            )
            for l in licenses
        ],
    )


@router.post("", response_model=UserFontSchema, status_code=201)
async def add_font(
    req: AddFontRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if req.license_type and req.license_type not in LICENSE_TYPES:
        raise HTTPException(status_code=422, detail=f"Invalid license_type. Choose from: {LICENSE_TYPES}")

    catalog_font: Optional[Font] = None
    custom_name: Optional[str] = None
    source = "manual"

    if req.font_id:
        result = await db.execute(select(Font).where(Font.id == req.font_id))
        catalog_font = result.scalar_one_or_none()
        if not catalog_font:
            raise HTTPException(status_code=404, detail="Font not found in catalog")
        source = "catalog"
    elif req.font_name:
        catalog_font = await _find_catalog_font(req.font_name, db)
        if catalog_font:
            source = "catalog"
        else:
            custom_name = req.font_name.strip()
    else:
        raise HTTPException(status_code=422, detail="Provide either font_id or font_name")

    uf = UserFont(
        user_id=user.id,
        font_id=catalog_font.id if catalog_font else None,
        custom_font_name=custom_name,
        license_type=req.license_type,
        source=source,
    )
    db.add(uf)
    await db.flush()

    cf = catalog_font
    return UserFontSchema(
        id=uf.id,
        font_name=cf.name if cf else custom_name,
        foundry=cf.foundry if cf else None,
        category=cf.category if cf else None,
        license_type=uf.license_type,
        source=uf.source,
        catalog_id=uf.font_id,
        has_license_data=bool(cf),
        added_at=uf.added_at.isoformat(),
    )


@router.post("/upload-folder", status_code=201)
async def upload_font_folder(
    files: List[UploadFile] = File(...),
    license_type: Optional[str] = Form(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Accept a folder upload (multiple files). Only font filenames are processed;
    file contents are discarded — we store the font family name only.
    """
    if license_type and license_type not in LICENSE_TYPES:
        raise HTTPException(status_code=422, detail=f"Invalid license_type. Choose from: {LICENSE_TYPES}")

    added = []
    skipped = []

    seen_names: set[str] = set()

    for upload in files:
        filename = upload.filename or ""
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in FONT_EXTENSIONS:
            skipped.append(filename)
            continue

        family_name = _extract_font_name(filename)
        if not family_name or family_name.lower() in seen_names:
            skipped.append(filename)
            continue
        seen_names.add(family_name.lower())

        # Try catalog match
        catalog_font = await _find_catalog_font(family_name, db)
        uf = UserFont(
            user_id=user.id,
            font_id=catalog_font.id if catalog_font else None,
            custom_font_name=None if catalog_font else family_name,
            license_type=license_type,
            source="upload",
        )
        db.add(uf)
        added.append(family_name)

    await db.flush()
    return {"added": added, "skipped": skipped, "count": len(added)}


@router.delete("/{user_font_id}", status_code=204)
async def remove_font(
    user_font_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserFont).where(UserFont.id == user_font_id, UserFont.user_id == user.id)
    )
    uf = result.scalar_one_or_none()
    if not uf:
        raise HTTPException(status_code=404, detail="Font not in your library")
    await db.delete(uf)
