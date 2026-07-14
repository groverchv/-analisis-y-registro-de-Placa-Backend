from __future__ import annotations

import random
import shutil
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory


SEED = 42
TRAIN_RATIO = 0.8
VALID_RATIO = 0.1
TEST_RATIO = 0.1
CLASS_NAMES = {
    0: "car",
    1: "license_plate",
}


def collect_pairs(images_dir: Path, labels_dir: Path) -> list[tuple[Path, Path]]:
    pairs: list[tuple[Path, Path]] = []
    missing_labels: list[Path] = []
    for image_path in sorted(images_dir.glob("*")):
        label_path = labels_dir / f"{image_path.stem}.txt"
        if not label_path.exists():
            missing_labels.append(image_path)
            continue
        pairs.append((image_path, label_path))

    if missing_labels:
        raise SystemExit(
            "Existen imagenes sin label correspondiente:\n"
            + "\n".join(str(path) for path in missing_labels[:20])
        )
    return pairs


def collect_all_pairs(dataset_root: Path) -> list[tuple[Path, Path]]:
    by_name: dict[str, tuple[Path, Path]] = {}
    for split_name in ("train", "valid", "test"):
        images_dir = dataset_root / split_name / "images"
        labels_dir = dataset_root / split_name / "labels"
        if not images_dir.exists() or not labels_dir.exists():
            continue
        for image_path, label_path in collect_pairs(images_dir, labels_dir):
            by_name[image_path.name] = (image_path, label_path)
    return sorted(by_name.values(), key=lambda pair: pair[0].name)


def count_classes(label_paths: list[Path]) -> Counter[int]:
    counts: Counter[int] = Counter()
    for label_path in label_paths:
        for line in label_path.read_text(encoding="utf-8", errors="replace").splitlines():
            parts = line.split()
            if parts:
                counts[int(parts[0])] += 1
    return counts


def ensure_empty_split(split_root: Path) -> None:
    for kind in ("images", "labels"):
        target = split_root / kind
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)


def copy_pairs(pairs: list[tuple[Path, Path]], split_root: Path) -> None:
    ensure_empty_split(split_root)
    for image_path, label_path in pairs:
        shutil.copy2(image_path, split_root / "images" / image_path.name)
        shutil.copy2(label_path, split_root / "labels" / label_path.name)


def validate_split(split_root: Path) -> tuple[int, int]:
    images_count = len(list((split_root / "images").glob("*")))
    labels_count = len(list((split_root / "labels").glob("*.txt")))
    if images_count != labels_count:
        raise SystemExit(
            f"Conteo inconsistente en {split_root}: images={images_count}, labels={labels_count}"
        )
    return images_count, labels_count


def write_data_yaml(dataset_root: Path) -> None:
    data_yaml = dataset_root / "data.yaml"
    lines = [
        "train: train/images",
        "val: valid/images",
        "test: test/images",
        "",
        f"nc: {len(CLASS_NAMES)}",
        "",
        "names:",
    ]
    lines.extend(f"  {class_id}: {class_name}" for class_id, class_name in CLASS_NAMES.items())
    data_yaml.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    dataset_root = Path(__file__).resolve().parents[2] / "ml" / "datasets" / "blpr"
    source_pairs = collect_all_pairs(dataset_root)
    if not source_pairs:
        raise SystemExit("No se encontraron pares imagen/label para dividir.")
    class_counts = count_classes([pair[1] for pair in source_pairs])

    random.seed(SEED)
    shuffled_pairs = source_pairs[:]
    random.shuffle(shuffled_pairs)

    total = len(shuffled_pairs)
    train_end = int(total * TRAIN_RATIO)
    valid_end = train_end + int(total * VALID_RATIO)

    train_pairs = shuffled_pairs[:train_end]
    valid_pairs = shuffled_pairs[train_end:valid_end]
    test_pairs = shuffled_pairs[valid_end:]

    with TemporaryDirectory(dir=dataset_root) as tmp_dir:
        tmp_root = Path(tmp_dir)
        copy_pairs(train_pairs, tmp_root / "train")
        copy_pairs(valid_pairs, tmp_root / "valid")
        copy_pairs(test_pairs, tmp_root / "test")

        for split_name in ("train", "valid", "test"):
            target_split = dataset_root / split_name
            if target_split.exists():
                shutil.rmtree(target_split)
            shutil.move(str(tmp_root / split_name), str(target_split))
    write_data_yaml(dataset_root)

    summary = {}
    for split_name in ("train", "valid", "test"):
        images_count, labels_count = validate_split(dataset_root / split_name)
        summary[split_name] = (images_count, labels_count)

    print(f"seed={SEED}")
    print(f"class_counts={dict(class_counts)}")
    for split_name, counts in summary.items():
        print(f"{split_name}_images={counts[0]}")
        print(f"{split_name}_labels={counts[1]}")
    print(f"data_yaml={dataset_root / 'data.yaml'}")


if __name__ == "__main__":
    main()
