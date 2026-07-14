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
        "ultralytics no esta instalado. Agrega la dependencia antes de validar."
    ) from exc


def main() -> None:
    parser = ArgumentParser(description="Valida un modelo YOLOv8 entrenado para placas.")
    parser.add_argument(
        "--model",
        default=str(Path(__file__).resolve().parents[2] / "ml" / "models" / "best.pt"),
    )
    parser.add_argument(
        "--data",
        default=str(Path(__file__).resolve().parents[2] / "ml" / "datasets" / "blpr" / "data.yaml"),
    )
    args = parser.parse_args()

    model_path = Path(args.model)
    data_yaml = Path(args.data)

    if not model_path.exists():
        raise SystemExit(f"No existe el modelo: {model_path}")
    if not data_yaml.exists():
        raise SystemExit(f"No existe data.yaml: {data_yaml}")

    metrics = YOLO(str(model_path)).val(data=str(data_yaml))
    print(metrics)


if __name__ == "__main__":
    main()
