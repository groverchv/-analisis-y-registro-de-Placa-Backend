FROM python:3.11-slim

# Metadatos de la imagen
LABEL maintainer="UAGRM" \
      description="Backend del Lector de Placas Bolivianas - UAGRM"

# Variables de entorno para Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependencias del sistema necesarias para OpenCV y EasyOCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente de la aplicación
COPY . .

# Puerto de la aplicación
EXPOSE 8000

# Comando de inicio con Uvicorn
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
