from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNREADABLE = "UNREADABLE"
    CLOSED = "CLOSED"
    NOT_AUTOMATED = "NOT_AUTOMATED"


class BoundingBox(BaseModel):
    x: float = Field(description="X position as percentage of image width")
    y: float = Field(description="Y position as percentage of image height")
    w: float = Field(description="Width as percentage of image width")
    h: float = Field(description="Height as percentage of image height")


class CheckResult(BaseModel):
    id: str
    check: str
    name: str
    expected: str
    found: str
    status: Verdict
    confidence: float = Field(ge=0.0, le=1.0)
    box: Optional[list[float]] = Field(default=None, description="[x,y,w,h] percentages")
    detail: Optional[str] = None
    suggestion: Optional[str] = None


class InspectionRequest(BaseModel):
    project_name: str = "Control cabinet QC"
    checks: list[str] = ["presence", "labels", "ferrules", "alignment", "colour"]
    confidence_threshold: float = 0.72


class InspectionResponse(BaseModel):
    run_id: str
    timestamp: str
    project: str
    photo_file: str
    drawing: Optional[str] = None
    wire_list: Optional[str] = None
    label_list: Optional[str] = None
    checks_run: list[str]
    confidence_threshold: float
    results: list[CheckResult]
    alignment_score: Optional[float] = None
    mode: str = "CV Analysis"


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.2.0"
    cv_backend: str = "OpenCV + ORB/AKAZE"
