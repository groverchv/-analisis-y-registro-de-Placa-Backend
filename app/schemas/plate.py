from pydantic import BaseModel
from typing import Optional

class PlateAnalysisResponse(BaseModel):
    status: str  # DETECTED | LOW_CONFIDENCE | ERROR
    detected_plate: Optional[str] = None
    normalized_plate: Optional[str] = None
    is_valid_bolivian_format: bool = False
    detection_confidence: Optional[float] = None
    ocr_confidence: Optional[float] = None
    combined_confidence: Optional[float] = None
    requires_manual_review: bool = False
    annotated_image: Optional[str] = None  # Base64
    plate_crop: Optional[str] = None       # Base64
    message: Optional[str] = None
