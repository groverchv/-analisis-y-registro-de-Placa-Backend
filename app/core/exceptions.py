from fastapi import HTTPException

class ImageProcessingException(HTTPException):
    def __init__(self, detail: str = "Error procesando la imagen"):
        super().__init__(status_code=400, detail=detail)

class AIModelException(HTTPException):
    def __init__(self, detail: str = "Error en el modelo de inteligencia artificial"):
        super().__init__(status_code=503, detail=detail)
