import cv2
import numpy as np
import easyocr
import supervision as sv
import base64
import logging
from inference_sdk import InferenceHTTPClient

from app.config.settings import settings
from app.ai.validators import validate_bolivian_plate

logger = logging.getLogger(__name__)

# Initialize components globally to avoid reloading per request
try:
    if settings.ROBOFLOW_API_KEY:
        client = InferenceHTTPClient(
            api_url="https://detect.roboflow.com",
            api_key=settings.ROBOFLOW_API_KEY
        )
    else:
        logger.warning("ROBOFLOW_API_KEY not set. API calls will fail.")
        client = None

    # EasyOCR se maneja desde el lifespan en main.py y se inyecta en la petición
    reader = None
    
    # Supervision annotators for the response image
    box_annotator = sv.BoxAnnotator(thickness=2)
    label_annotator = sv.LabelAnnotator(text_scale=0.5)
except Exception as e:
    logger.error(f"Error initializing AI components: {e}")
    client, reader = None, None


def analyze_plate(image_bytes: bytes, ocr_reader=None) -> dict:
    """
    Pipeline completo:
    imagen → detección (Roboflow) → crop (Supervision) → OCR (EasyOCR) → validación
    """
    if not client:
        return {"status": "ERROR", "message": "Falta configurar la API KEY de Roboflow en el backend."}

    # 1. Decodificar imagen
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if image is None:
        return {"status": "ERROR", "message": "No se pudo decodificar la imagen"}
    
    # 2. Detección con Roboflow BLPR
    try:
        # Roboflow inference SDK can take a numpy array
        result = client.infer(image, model_id=settings.ROBOFLOW_MODEL_ID)
    except Exception as e:
        logger.error(f"Roboflow API error: {e}")
        return {"status": "ERROR", "message": f"Error comunicándose con Roboflow: {str(e)}"}
    
    # 3. Supervision: convertir resultados a Detections
    detections = sv.Detections.from_inference(result)
    
    # 4. Filtrar solo placas (el modelo BLPR detecta "car" y "license_plate")
    if "class_name" in detections.data:
        plate_mask = np.array([
            cn == "license_plate" or cn == "License_Plate" or "plate" in cn.lower()
            for cn in detections.data["class_name"]
        ])
    else:
        # Si no hay class_name, asumimos que todas las detecciones son válidas
        plate_mask = np.ones(len(detections), dtype=bool)
        
    plate_detections = detections[plate_mask]
    
    if len(plate_detections) == 0:
        return {"status": "ERROR", "message": "No se detectó ninguna placa en la imagen"}
    
    # 5. Tomar la detección con mayor confianza
    best_idx = int(plate_detections.confidence.argmax())
    best_detection = plate_detections[[best_idx]]
    detection_confidence = float(best_detection.confidence[0])
    
    # 6. Supervision: recortar la región de la placa
    # xyxy es un array de shape (1, 4), pasamos la primera fila
    plate_crop = sv.crop_image(image=image, xyxy=best_detection.xyxy[0])
    
    # 7. EasyOCR: leer texto del recorte
    ocr_engine = ocr_reader if ocr_reader else reader
    if not ocr_engine:
        return {"status": "ERROR", "message": "Motor OCR no inicializado."}
    
    ocr_results = ocr_engine.readtext(plate_crop, detail=1)
    
    if not ocr_results:
        return {
            "status": "LOW_CONFIDENCE",
            "message": "Placa detectada pero OCR no pudo leer caracteres",
            "detection_confidence": detection_confidence,
            "requires_manual_review": True
        }
    
    # 8. Concatenar textos y calcular confianza OCR
    # r[1] es el texto, r[2] es la confianza
    raw_text = " ".join([r[1] for r in ocr_results])
    ocr_confidence = float(np.mean([r[2] for r in ocr_results]))
    
    # 9. Normalizar: limpiar espacios, guiones y puntos
    normalized = raw_text.upper().replace(" ", "").replace("-", "").replace(".", "")
    
    # 10. Validar formato Bolivia (NNNNLLL)
    is_valid = validate_bolivian_plate(normalized)
    
    # 11. Confianza combinada
    combined_confidence = detection_confidence * ocr_confidence
    
    # 12. Clasificar
    if combined_confidence < settings.CONFIDENCE_THRESHOLD:
        status = "LOW_CONFIDENCE"
        requires_manual_review = True
    else:
        status = "DETECTED"
        requires_manual_review = False
    
    # 13. Supervision: generar imagen anotada
    labels = [f"{normalized} ({combined_confidence:.0%})"]
    annotated = box_annotator.annotate(scene=image.copy(), detections=best_detection)
    annotated = label_annotator.annotate(
        scene=annotated, detections=best_detection, labels=labels
    )
    
    # Convertir imágenes a base64 para el frontend
    _, buffer = cv2.imencode('.jpg', annotated)
    annotated_b64 = base64.b64encode(buffer).decode('utf-8')
    
    _, crop_buffer = cv2.imencode('.jpg', plate_crop)
    crop_b64 = base64.b64encode(crop_buffer).decode('utf-8')
    
    return {
        "status": status,
        "detected_plate": raw_text,
        "normalized_plate": normalized if is_valid else normalized,
        "is_valid_bolivian_format": is_valid,
        "detection_confidence": detection_confidence,
        "ocr_confidence": ocr_confidence,
        "combined_confidence": combined_confidence,
        "requires_manual_review": requires_manual_review,
        "annotated_image": f"data:image/jpeg;base64,{annotated_b64}",
        "plate_crop": f"data:image/jpeg;base64,{crop_b64}"
    }
