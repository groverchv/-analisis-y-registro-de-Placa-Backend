from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from app.schemas.plate import PlateAnalysisResponse
from app.ai.pipeline import analyze_plate

router = APIRouter()

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_CONTENT_TYPES = ["image/jpeg", "image/png"]

@router.post("/analyze", response_model=PlateAnalysisResponse)
async def analyze_plate_endpoint(request: Request, file: UploadFile = File(...)):
    """
    Recibe una imagen, valida tamaño/formato, y ejecuta el pipeline ALPR.
    """
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400, 
            detail="Formato de archivo no permitido. Solo se aceptan imágenes JPEG y PNG."
        )
    
    # Leer el archivo a memoria
    image_bytes = await file.read()
    
    if len(image_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413, 
            detail="El archivo es demasiado grande. El límite máximo es de 5MB."
        )
    
    # Ejecutar pipeline AI
    result_dict = await run_in_threadpool(
        analyze_plate,
        image_bytes,
        request.app.state.ocr_reader,
    )

    if result_dict.get("status") == "ERROR":
        return JSONResponse(
            status_code=int(result_dict.get("http_status", 422)),
            content=PlateAnalysisResponse(
                status="ERROR",
                message=result_dict.get("message", "Error desconocido durante el análisis."),
            ).model_dump(),
        )
    
    return PlateAnalysisResponse(**result_dict)

@router.get("/health")
async def health_check():
    """
    Endpoint simple para verificar que la API está funcionando.
    """
    return {"status": "ok", "message": "API de ALPR funcionando correctamente."}
