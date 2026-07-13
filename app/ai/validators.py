import re

# Patrón para placa boliviana: 4 dígitos + 3 letras mayúsculas
PATRON_PLACA_BOLIVIA = re.compile(r'^\d{4}[A-Z]{3}$')

def validate_bolivian_plate(normalized_plate: str) -> bool:
    """
    Valida si una cadena de texto (previamente normalizada sin espacios)
    cumple con el formato de placa boliviana.
    """
    if not normalized_plate:
        return False
    return bool(PATRON_PLACA_BOLIVIA.match(normalized_plate))
