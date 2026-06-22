from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_optional
from app.db.database import get_db
from app.db.models import ScanResult, User
from app.models.scan import ScanRequest, ScanResponse
from app.scanners.scanner import scan_website
from app.analyzer.lighthouse import analyze_url as lighthouse_analyze
from app.analyzer.accessibility import analyze_accessibility
from app.scoring.engine import compute_scores

router = APIRouter()


class AnalyzeRequest(BaseModel):
    url: str
    use_browser: bool = False


async def _extract_fingerprints(url: str) -> list[dict] | None:
    """Attempt browser-based extraction. Returns None if unavailable."""
    try:
        from app.extractor import extract_site
        return await extract_site(url, max_pages=5, max_depth=1)
    except ImportError:
        print("[analyze] Playwright not installed — skipping browser extraction")
        return None
    except Exception as e:
        print(f"[analyze] Browser extraction failed: {e}")
        return None


@router.post("/scan", response_model=ScanResponse)
async def scan(req: ScanRequest):
    try:
        result = await scan_website(req.url)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze")
async def analyze(
    req: AnalyzeRequest,
    user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """
    Full analysis: scanner + lighthouse + accessibility + scoring.
    If the user is authenticated, cross-references scanned fonts against
    their library for a more accurate license compliance score.
    Saves result to history if authenticated.
    """
    try:
        scan_result = await scan_website(req.url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Browser-based font extraction (enriches brand consistency scoring)
    if req.use_browser:
        fingerprints = await _extract_fingerprints(req.url)
        if fingerprints:
            scan_result["fingerprints"] = fingerprints

    lighthouse = None
    try:
        lighthouse = await lighthouse_analyze(req.url)
    except Exception as e:
        print(f"[analyze] Lighthouse failed: {e}")

    a11y = None
    try:
        a11y = await analyze_accessibility(req.url)
    except Exception as e:
        print(f"[analyze] Accessibility scan failed: {e}")

    scores = compute_scores(scan_result, lighthouse, a11y)

    # Flatten all violations into a simple list for history storage
    all_issues = []
    for key, metric in scores["breakdown"].items():
        for v in metric.get("violations", []):
            all_issues.append({"metric": key, "message": v})

    # Save to history if user is logged in
    if user:
        bd = scores["breakdown"]
        scan_record = ScanResult(
            user_id=user.id,
            url=req.url,
            overall_score=scores["overall_score"],
            brand_consistency=bd["brand_consistency"]["score"],
            license_compliance=bd["license_compliance"]["score"],
            performance=bd["performance"]["score"],
            accessibility=bd["accessibility"]["score"],
            developer_experience=bd["developer_experience"]["score"],
            issues=all_issues,
            raw_data={
                "scan": scan_result,
                "lighthouse": lighthouse,
                "accessibility": a11y,
            },
        )
        db.add(scan_record)
        await db.flush()
        scan_id = scan_record.id
    else:
        scan_id = None

    return {
        **scan_result,
        "lighthouse": lighthouse,
        "accessibility": a11y,
        "scores": scores,
        "scan_id": scan_id,
    }
