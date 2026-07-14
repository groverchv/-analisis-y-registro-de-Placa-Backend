import os
from argparse import ArgumentParser
from pathlib import Path

ULTRALYTICS_SETTINGS_DIR = Path(__file__).resolve().parents[2] / ".ultralytics"
ULTRALYTICS_SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("YOLO_CONFIG_DIR", str(ULTRALYTICS_SETTINGS_DIR))

try:
    from ultralytics import YOLO
except ImportError as exc:  # pragma: no cover - depends on local environment
    raise SystemExit(
        "ultralytics no esta instalado. Agrega la dependencia antes de entrenar."
    ) from exc


def ensure_dataset_ready(dataset_root: Path) -> Path:
    data_yaml = dataset_root / "data.yaml"
    required_paths = [
        dataset_root / "train" / "images",
        dataset_root / "train" / "labels",
        dataset_root / "valid" / "images",
        dataset_root / "valid" / "labels",
        dataset_root / "test" / "images",
        dataset_root / "test" / "labels",
        data_yaml,
    ]
    missing = [path for path in required_paths if not path.exists()]
    if missing:
        raise SystemExit(
            "Dataset incompleto para entrenamiento YOLO. Faltan:\n"
            + "\n".join(f"- {path}" for path in missing)
        )
    return data_yaml


def main() -> None:
    parser = ArgumentParser(description="Entrena YOLOv8 para deteccion de placas.")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--weights", default="yolov8n.pt")
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[2]
    dataset_root = project_root / "ml" / "datasets" / "blpr"
    models_root = project_root / "ml" / "models"
    runs_root = project_root / "ml" / "runs"
    models_root.mkdir(parents=True, exist_ok=True)
    runs_root.mkdir(parents=True, exist_ok=True)

    data_yaml = ensure_dataset_ready(dataset_root)
    model = YOLO(args.weights)
    results = model.train(
        data=str(data_yaml),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        project=str(runs_root),
        name="blpr_yolov8_alpha",
        exist_ok=True,
    )

    best_path = Path(results.save_dir) / "weights" / "best.pt"
    if not best_path.exists():
        raise SystemExit(f"Entrenamiento finalizado sin `best.pt`: {best_path}")

    target = models_root / "best.pt"
    target.write_bytes(best_path.read_bytes())
    print(f"Modelo exportado a: {target}")


if __name__ == "__main__":
    main()
