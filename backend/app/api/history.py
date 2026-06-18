"""Scan history endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db.models import ScanResult, User

router = APIRouter()


class ScoreBreakdownSchema(BaseModel):
    brand_consistency: Optional[float]
    license_compliance: Optional[float]
    performance: Optional[float]
    accessibility: Optional[float]
    developer_experience: Optional[float]


class ScanSummarySchema(BaseModel):
    id: int
    url: str
    overall_score: Optional[float]
    scores: ScoreBreakdownSchema
    issues_count: int
    created_at: str


class ScanDetailSchema(ScanSummarySchema):
    issues: list
    raw_data: dict


@router.get("", response_model=List[ScanSummarySchema])
async def list_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ScanResult)
        .where(ScanResult.user_id == user.id)
        .order_by(ScanResult.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    scans = result.scalars().all()
    return [_to_summary(s) for s in scans]


@router.get("/{scan_id}", response_model=ScanDetailSchema)
async def get_scan(
    scan_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ScanResult).where(ScanResult.id == scan_id, ScanResult.user_id == user.id)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    return ScanDetailSchema(
        **_to_summary(scan).model_dump(),
        issues=scan.issues,
        raw_data=scan.raw_data,
    )


def _to_summary(s: ScanResult) -> ScanSummarySchema:
    return ScanSummarySchema(
        id=s.id,
        url=s.url,
        overall_score=float(s.overall_score) if s.overall_score is not None else None,
        scores=ScoreBreakdownSchema(
            brand_consistency=float(s.brand_consistency) if s.brand_consistency is not None else None,
            license_compliance=float(s.license_compliance) if s.license_compliance is not None else None,
            performance=float(s.performance) if s.performance is not None else None,
            accessibility=float(s.accessibility) if s.accessibility is not None else None,
            developer_experience=float(s.developer_experience) if s.developer_experience is not None else None,
        ),
        issues_count=len(s.issues),
        created_at=s.created_at.isoformat(),
    )
