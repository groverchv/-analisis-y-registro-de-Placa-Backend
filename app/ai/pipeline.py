import base64
import logging
import os
from pathlib import Path
from typing import Any, Iterable

import cv2
import numpy as np
import supervision as sv

try:
    from inference_sdk import InferenceHTTPClient
except ImportError:  # pragma: no cover - depends on local environment
    InferenceHTTPClient = None

from app.ai.validators import normalize_plate_text, validate_bolivian_plate
from app.config.settings import settings

ULTRALYTICS_SETTINGS_DIR = Path(__file__).resolve().parents[2] / ".ultralytics"
ULTRALYTICS_SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("YOLO_CONFIG_DIR", str(ULTRALYTICS_SETTINGS_DIR))

try:
    from ultralytics import YOLO
except Exception:  # pragma: no cover - dependency may be intentionally absent or misconfigured
    YOLO = None

logger = logging.getLogger(__name__)

PLATE_CLASS_KEYWORDS = (
    "plate",
    "license plate",
    "license_plate",
    "car plate",
    "car_plate",
)

LOCAL_MODEL_PATH = Path(settings.LOCAL_YOLO_MODEL_PATH)


def _error(message: str, http_status: int = 422, error_code: str = "pipeline_error") -> dict:
    return {
        "status": "ERROR",
        "message": message,
        "http_status": http_status,
        "error_code": error_code,
        "requires_manual_review": False,
    }


def _matches_plate_class(class_name: str) -> bool:
    normalized = class_name.strip().lower().replace("-", " ").replace("_", " ")
    return any(keyword.replace("_", " ") in normalized for keyword in PLATE_CLASS_KEYWORDS)


def _resolve_plate_class_ids(model_names: object) -> set[int]:
    if isinstance(model_names, dict):
        items = model_names.items()
    elif isinstance(model_names, Iterable):
        items = enumerate(model_names)
    else:
        return set()

    return {
        int(class_id)
        for class_id, class_name in items
        if isinstance(class_name, str) and _matches_plate_class(class_name)
    }


def _build_cloud_client() -> Any | None:
    if InferenceHTTPClient is None:
        logger.warning("inference-sdk is not installed. Roboflow Cloud fallback is unavailable.")
        return None

    if not settings.ROBOFLOW_API_KEY:
        logger.warning("ROBOFLOW_API_KEY not set. Roboflow Cloud fallback is unavailable.")
        return None

    return InferenceHTTPClient(
        api_url="https://detect.roboflow.com",
        api_key=settings.ROBOFLOW_API_KEY,
    )


def _build_local_model() -> Any | None:
    if YOLO is None:
        logger.info("ultralytics is not installed. Local YOLO is unavailable.")
        return None

    if not LOCAL_MODEL_PATH.exists():
        logger.info("Local YOLO model not found at %s", LOCAL_MODEL_PATH)
        return None

    try:
        return YOLO(str(LOCAL_MODEL_PATH))
    except Exception as exc:  # pragma: no cover - model loading depends on environment
        logger.error("Unable to load local YOLO model at %s: %s", LOCAL_MODEL_PATH, exc)
        return None


cloud_client = _build_cloud_client()
local_model = _build_local_model()
box_annotator = sv.BoxAnnotator(thickness=2)
label_annotator = sv.LabelAnnotator(text_scale=0.5)


def _filter_cloud_plate_detections(detections: sv.Detections) -> sv.Detections:
    class_names = detections.data.get("class_name") if detections.data else None
    if class_names is None:
        return detections

    plate_mask = np.array(
        [_matches_plate_class(str(class_name)) for class_name in class_names],
        dtype=bool,
    )
    return detections[plate_mask]


def _filter_local_plate_detections(
    detections: sv.Detections,
    model_names: object,
) -> sv.Detections:
    if detections.class_id is None:
        return detections

    plate_class_ids = _resolve_plate_class_ids(model_names)
    if not plate_class_ids:
        logger.warning("No plate class name was resolved from local model names: %s", model_names)
        return detections

    plate_mask = np.isin(detections.class_id, list(plate_class_ids))
    return detections[plate_mask]


def _select_best_detection(detections: sv.Detections) -> tuple[sv.Detections, float]:
    if len(detections) == 0:
        raise ValueError("No se detectó ninguna placa en la imagen.")

    if detections.confidence is None or len(detections.confidence) == 0:
        best_idx = 0
        confidence = 0.0
    else:
        best_idx = int(detections.confidence.argmax())
        confidence = float(detections.confidence[best_idx])

    return detections[[best_idx]], confidence


def _detect_with_local_yolo(image: np.ndarray) -> tuple[sv.Detections, float, str]:
    if local_model is None:
        raise RuntimeError("Local YOLO model is unavailable.")

    results = local_model.predict(
        source=image,
        conf=settings.DETECTION_CONFIDENCE_THRESHOLD,
        verbose=False,
    )
    if not results:
        raise RuntimeError("La inferencia local no devolvió resultados.")

    result = results[0]
    detections = sv.Detections.from_ultralytics(result)
    plate_detections = _filter_local_plate_detections(detections, result.names)
    best_detection, confidence = _select_best_detection(plate_detections)
    return best_detection, confidence, "YOLO_LOCAL"


def _detect_with_roboflow_cloud(image: np.ndarray) -> tuple[sv.Detections, float, str]:
    if cloud_client is None:
        raise RuntimeError("Roboflow Cloud is unavailable.")

    result = cloud_client.infer(image, model_id=settings.ROBOFLOW_MODEL_ID)
    detections = sv.Detections.from_inference(result)
    plate_detections = _filter_cloud_plate_detections(detections)
    best_detection, confidence = _select_best_detection(plate_detections)
    return best_detection, confidence, "ROBOFLOW_CLOUD"


def _run_detection(image: np.ndarray) -> tuple[sv.Detections, float, str]:
    if local_model is not None:
        return _detect_with_local_yolo(image)

    if cloud_client is not None:
        return _detect_with_roboflow_cloud(image)

    raise RuntimeError(
        "No hay backend de detección disponible. Falta un modelo local válido o ROBOFLOW_API_KEY."
    )


def analyze_plate(image_bytes: bytes, ocr_reader=None) -> dict:
    if not image_bytes:
        return _error("La imagen está vacía.", http_status=400, error_code="empty_image")

    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image is None:
        return _error(
            "No se pudo decodificar la imagen enviada.",
            http_status=400,
            error_code="invalid_image",
        )

    try:
        best_detection, detection_confidence, detector_backend = _run_detection(image)
    except ValueError as exc:
        return _error(str(exc), http_status=422, error_code="no_plate_detected")
    except Exception as exc:
        logger.error("Detection pipeline failed: %s", exc)
        return _error(
            f"Error durante la inferencia de detección: {exc}",
            http_status=503,
            error_code="detection_error",
        )

    if detection_confidence < settings.DETECTION_CONFIDENCE_THRESHOLD:
        return {
            "status": "LOW_CONFIDENCE",
            "message": "La placa fue detectada con confianza baja.",
            "detection_backend": detector_backend,
            "detection_confidence": detection_confidence,
            "requires_manual_review": True,
        }

    plate_crop = sv.crop_image(image=image, xyxy=best_detection.xyxy[0])
    if plate_crop.size == 0:
        return _error(
            "La detección de la placa no produjo un recorte válido.",
            http_status=422,
            error_code="empty_crop",
        )

    if ocr_reader is None:
        return _error("Motor OCR no inicializado.", http_status=503, error_code="ocr_unavailable")

    try:
        ocr_results = ocr_reader.readtext(plate_crop, detail=1)
    except Exception as exc:
        logger.error("OCR failed: %s", exc)
        return _error(
            f"Error durante OCR: {exc}",
            http_status=503,
            error_code="ocr_error",
        )

    if not ocr_results:
        return {
            "status": "LOW_CONFIDENCE",
            "message": "Placa detectada pero OCR no pudo leer caracteres.",
            "detection_backend": detector_backend,
            "detection_confidence": detection_confidence,
            "requires_manual_review": True,
        }

    raw_text = " ".join(str(item[1]).strip() for item in ocr_results if len(item) > 1).strip()
    normalized = normalize_plate_text(raw_text)
    if not normalized:
        return {
            "status": "LOW_CONFIDENCE",
            "message": "OCR devolvió texto vacío después de normalizar.",
            "detection_backend": detector_backend,
            "detection_confidence": detection_confidence,
            "requires_manual_review": True,
        }

    ocr_scores = [float(item[2]) for item in ocr_results if len(item) > 2]
    ocr_confidence = float(np.mean(ocr_scores)) if ocr_scores else 0.0
    combined_confidence = detection_confidence * ocr_confidence
    is_valid = validate_bolivian_plate(normalized)

    if not is_valid:
        status = "LOW_CONFIDENCE"
        requires_manual_review = True
        message = "OCR detectó texto, pero no coincide con un formato boliviano válido."
    elif combined_confidence < settings.CONFIDENCE_THRESHOLD:
        status = "LOW_CONFIDENCE"
        requires_manual_review = True
        message = "La lectura requiere revisión manual por baja confianza."
    else:
        status = "DETECTED"
        requires_manual_review = False
        message = None

    labels = [f"{normalized} ({combined_confidence:.0%})"]
    annotated = box_annotator.annotate(scene=image.copy(), detections=best_detection)
    annotated = label_annotator.annotate(scene=annotated, detections=best_detection, labels=labels)

    _, buffer = cv2.imencode(".jpg", annotated)
    annotated_b64 = base64.b64encode(buffer).decode("utf-8")

    _, crop_buffer = cv2.imencode(".jpg", plate_crop)
    crop_b64 = base64.b64encode(crop_buffer).decode("utf-8")

    return {
        "status": status,
        "message": message,
        "detected_plate": raw_text,
        "normalized_plate": normalized,
        "is_valid_bolivian_format": is_valid,
        "detection_backend": detector_backend,
        "detection_confidence": detection_confidence,
        "ocr_confidence": ocr_confidence,
        "combined_confidence": combined_confidence,
        "requires_manual_review": requires_manual_review,
        "annotated_image": f"data:image/jpeg;base64,{annotated_b64}",
        "plate_crop": f"data:image/jpeg;base64,{crop_b64}",
    }
