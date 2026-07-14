import re

PATRON_PLACA_BOLIVIA = re.compile(r"^\d{4}[A-Z]{3}$")


def normalize_plate_text(raw_text: str) -> str:
    if not raw_text:
        return ""
    return re.sub(r"[^A-Z0-9]", "", raw_text.upper())


def validate_bolivian_plate(normalized_plate: str) -> bool:
    if not normalized_plate:
        return False
    return bool(PATRON_PLACA_BOLIVIA.fullmatch(normalized_plate))
