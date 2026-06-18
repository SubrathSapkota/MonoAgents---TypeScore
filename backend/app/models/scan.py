# app/models/scan.py
from pydantic import BaseModel
from typing import List, Optional

class ScanRequest(BaseModel):
    url: str

class PageResult(BaseModel):
    url: str
    path: str
    fonts: List[str]
    css_files: List[str]
    inline_styles: List[str]
    error: Optional[str] = None

class ScanResponse(BaseModel):
    base_url: str
    pages: List[PageResult]