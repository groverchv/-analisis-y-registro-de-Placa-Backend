# Lector de Placas UAGRM - Backend API

Bienvenido al Backend del Proyecto Lector de Placas UAGRM. Esta API está desarrollada en **FastAPI**, utiliza **PostgreSQL** (con driver asíncrono `psycopg` + SQLAlchemy), e integra **Roboflow** para la Inteligencia Artificial (Detección y OCR).

---

## Requisitos Previos

- Python 3.10 o superior.
- **PostgreSQL** instalado y corriendo en tu computadora.

---

## 1. Configurar la Base de Datos (¡Ya está en la Nube!)

Tu equipo ha decidido usar **Neon** para que la base de datos sea global y compartida por todos en tiempo real. 
- **NO necesitas instalar PostgreSQL localmente.**
- El código ya viene configurado para conectarse a la base de datos de producción automáticamente.

---

## 2. Instalación del Proyecto

Abre tu terminal en la carpeta de este proyecto (`backend/`) y ejecuta:

### En Windows:
```powershell
# 1. Crear entorno virtual
python -m venv venv

# 2. Activar entorno virtual
.\venv\Scripts\Activate.ps1

# 3. Instalar dependencias
pip install -r requirements.txt
```

### En Mac/Linux:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 3. Variables de Entorno (.env)

El archivo `.env` ya viene configurado en el repositorio (para entornos de desarrollo). 
Verifica que tengas estas líneas:

```env
APP_NAME="Lector de Placas UAGRM"
APP_VERSION="1.0.0"
DEBUG=true
ALLOWED_ORIGINS='["http://localhost:5173", "http://localhost:3000"]'
DATABASE_URL=postgresql+psycopg://neondb_owner:npg_Z5WMe3ICfrFx@ep-misty-recipe-adlghyw1-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require

# ROBOFLOW API KEY
ROBOFLOW_API_KEY=tu_api_key_aqui
ROBOFLOW_WORKSPACE=blpr-v4yyh
ROBOFLOW_PROJECT=license-plate-recognition-rxg4e
ROBOFLOW_VERSION=4
```

> **NOTA:** Pídele la `ROBOFLOW_API_KEY` al integrante encargado de la IA (Rol 4).

---

## 4. Migraciones y Poblado de Datos (Seed)

Para crear las tablas en tu base de datos recién creada y llenarla con datos de prueba (Estudiantes y Docentes reales de prueba):

```powershell
# Asegúrate de tener el entorno virtual activado
set PYTHONPATH=.

# 1. Aplicar las migraciones a PostgreSQL
alembic upgrade head

# 2. Llenar la base de datos con usuarios y vehículos de prueba
python seed_db.py
```

Si todo sale bien, verás un mensaje: `¡Base de datos sembrada con éxito!`.

---

## 5. Levantar el Servidor

Para encender el backend y dejarlo escuchando peticiones del frontend:

```powershell
uvicorn app.main:app --reload
```

El servidor estará corriendo en: **http://127.0.0.1:8000**

---

## 6. Endpoints Principales (Para el equipo Frontend)

Toda la documentación interactiva (Swagger UI) está disponible en:
**http://127.0.0.1:8000/docs**

### Flujo de Uso del Frontend:

1. **Enviar la imagen de la cámara:**
   - **POST** `/api/v1/plates/analyze`
   - *Form-Data:* `file` (archivo JPG/PNG).
   - *Respuesta:* Un JSON con la placa extraída (`"text": "ABC1234"`).

2. **Verificar si la placa está registrada:**
   - **GET** `/api/v1/vehicles/by-plate/{plate_text}`
   - *Si responde 200 OK:* El vehículo existe, devuelve los datos y el portón se abre.
   - *Si responde 404 Not Found:* El vehículo no existe. Mostrar formulario de registro.

3. **Validar un Estudiante (Registro Manual):**
   - **GET** `/api/v1/university-persons/validate/{student_code}`
   - *Ejemplo de código:* `202011111`
   - *Respuesta:* Datos del estudiante y su ID interno.

4. **Registrar el Vehículo:**
   - **POST** `/api/v1/vehicles/`
   - *Body (JSON):* `{"license_plate": "ABC1234", "owner_id": "uuid-del-estudiante"}`
   - *Respuesta:* Vehículo guardado permanentemente en PostgreSQL.

---

¡Listo! Con esto tienes el backend completamente funcional en tu máquina local.
