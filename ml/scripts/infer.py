import os
from argparse import ArgumentParser
from pathlib import Path

import cv2
import easyocr
import supervision as sv

ULTRALYTICS_SETTINGS_DIR = Path(__file__).resolve().parents[2] / ".ultralytics"
ULTRALYTICS_SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("YOLO_CONFIG_DIR", str(ULTRALYTICS_SETTINGS_DIR))

from ultralytics import YOLO

from app.ai.validators import normalize_plate_text, validate_bolivian_plate

PLATE_KEYWORDS = ("plate", "license plate", "license_plate", "car plate")


def is_plate_name(name: str) -> bool:
    normalized = name.strip().lower().replace("-", " ").replace("_", " ")
    return any(keyword.replace("_", " ") in normalized for keyword in PLATE_KEYWORDS)


def main() -> None:
    parser = ArgumentParser(description="Prueba inferencia YOLO local + OCR sobre una imagen.")
    parser.add_argument("--image", required=True)
    parser.add_argument(
        "--model",
        default=str(Path(__file__).resolve().parents[2] / "ml" / "models" / "best.pt"),
    )
    args = parser.parse_args()

    image_path = Path(args.image)
    model_path = Path(args.model)
    if not image_path.exists():
        raise SystemExit(f"No existe la imagen: {image_path}")
    if not model_path.exists():
        raise SystemExit(f"No existe el modelo: {model_path}")

    image = cv2.imread(str(image_path))
    if image is None:
        raise SystemExit(f"No se pudo leer la imagen: {image_path}")

    model = YOLO(str(model_path))
    result = model.predict(source=image, conf=0.35, verbose=False)[0]
    detections = sv.Detections.from_ultralytics(result)
    plate_ids = {int(class_id) for class_id, name in result.names.items() if is_plate_name(str(name))}

    if detections.class_id is not None and plate_ids:
        detections = detections[[class_id in plate_ids for class_id in detections.class_id]]

    if len(detections) == 0:
        raise SystemExit("No se detecto ninguna placa en la imagen.")

    best_idx = int(detections.confidence.argmax()) if detections.confidence is not None else 0
    best_detection = detections[[best_idx]]
    crop = sv.crop_image(image=image, xyxy=best_detection.xyxy[0])

    reader = easyocr.Reader(["es", "en"], gpu=False, verbose=False)
    ocr_results = reader.readtext(crop, detail=1)
    raw_text = " ".join(item[1] for item in ocr_results).strip() if ocr_results else ""
    normalized = normalize_plate_text(raw_text)

    print(f"model={model_path}")
    print(f"image={image_path}")
    print(f"classes={result.names}")
    print(f"detections={len(detections)}")
    print(f"detection_confidence={float(best_detection.confidence[0]) if best_detection.confidence is not None else 0.0}")
    print(f"ocr_results={ocr_results}")
    print(f"normalized={normalized}")
    print(f"is_valid_bolivian_format={validate_bolivian_plate(normalized)}")


if __name__ == "__main__":
    main()
