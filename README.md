# MVP Minutas Notariales con IA

> **Objetivo**: extraer datos estructurados de **minutas notariales** (PDF/DOCX con texto) usando un **motor de IA** guiado por reglas, con soporte para **múltiples otorgantes** y **múltiples apoderados**, y **evidencia por campo** para auditoría.

---

## 1) Propuesta de valor

- **Ahorro de tiempo**: lectura automática de minutas en **PDF/DOCX** (sin OCR) y extracción de:
  - acto (p. ej., **PODER**),
  - **fecha** de la minuta,
  - **personas** (otorgantes / apoderados) con nombres, documentos, domicilio, estado civil, profesión,
  - **múltiples documentos por persona** (prioriza **DNI**, guarda pasaporte/otros como `docs_adicionales`).
- **Flexible ante variaciones**: el modelo **lee en secuencia** (no por plantillas rígidas) y arma cada persona mientras encuentra atributos.
- **Transparente**: cada campo puede incluir **evidencia** (cita + span) para ver **de dónde salió**.
- **Listo para escalar**: API FastAPI, diseño por capas, respuesta **compacta** (para UI) y **full** (auditoría).

---

## 2) Alcance del MVP (versión actual)

- **Entradas**: DOCX / PDF **con texto** (no imagen escaneada).
- **Acto base**: **PODER** (otros actos se podrán añadir).
- **Roles**: detecta **otorgante(s)** y **apoderado(s)** usando la bisagra **“otorga … a favor de …”**; si no está clara, marca como **indeterminado**.
- **Reglas clave**:
  - **Lectura secuencial**: abre “persona activa” al detectar un nombre y va sumando atributos contiguos (documento, domicilio, etc.).
  - **Múltiples documentos**: DNI como principal; pasaporte/CE/RUC a `docs_adicionales`.
  - **Domicilio**: frases “con domicilio en … / domiciliado en …” se asignan a la persona activa; normaliza comas/espacios raros.
  - **Fecha**: convierte a `YYYY-MM-DD` cuando se puede.
  - **Confianza**: puntajes por campo + clasificación del acto.
  - **Evidencia** (opcional): `evidence_text` + `char_span` por campo.

---


### 3.2 Stack de Tecnologías (MVP)

- **Lenguaje / Runtime**
  - Python **3.11+**
- **Framework Web**
  - **FastAPI** (API REST) + **Uvicorn** (ASGI server)
- **Modelado y validación**
  - **Pydantic** (modelos y DTOs)
- **Configuración**
  - **python-dotenv** para variables en `.env`
- **Procesamiento de documentos**
  - **PyMuPDF (`pymupdf`)** para PDF (texto nativo, sin OCR)
  - **python-docx** para DOCX
- **Cliente de IA**
  - **openai** (modelo **gpt-4o-mini** con salida JSON estructurada)
- **Subida de archivos**
  - **python-multipart** (multipart/form-data)
- **Middleware / utilidades**
  - **CORS** (Starlette/FastAPI)
  - **Middleware de timing** (tiempo de procesamiento por request)
- **Observabilidad (básico)**
  - Headers `X-Processing-Time-ms`, logs de errores
- **Pruebas**
  - Swagger UI (`/docs`), `curl`/Postman/Thunder Client
- **Roadmap opcional**
  - **Caché** (SQLite/Redis) por `raw_text_hash`
  - **Rate limiting / Backoff** para 429
  - **Logging estructurado** (JSON) + `request-id`
  - **OCR** (Tesseract) para PDFs escaneados (fase posterior)

---

## 4) Flujo del algoritmo (texto para graficar)

> **Descripción textual del flujo**, lista para que la conviertas en imágenes/diagramas.

1. **Recepción del archivo**
   - El cliente hace `POST /extract` enviando un **PDF** o **DOCX** (texto, no imagen).
   - Parámetros opcionales: `view=compact|full` y `reveal_id=true|false`.

2. **Ingesta y normalización**
   - Si es PDF, se extrae **texto** con PyMuPDF; si es DOCX, con `python-docx`.
   - Se **normalizan** espacios/saltos para obtener un texto plano limpio.

3. **Cálculo de hash y metadatos**
   - Se calcula `raw_text_hash` (SHA-256) para trazabilidad/cache.
   - Se determinan páginas, tamaño, extensión y nombre del archivo.

4. **Heurística rápida del acto**
   - Se busca la presencia de términos (p. ej., “poder”, “escritura pública”) para obtener un **`is_poder_guess`** (0–1) que orienta la clasificación.

5. **Preparación de prompt para IA**
   - Se define un **`json_schema`** de salida (estructura exacta esperada).
   - Se incluyen **reglas** (lectura secuencial, priorización de DNI, domicilio de persona activa, fecha top-level, roles por bisagra “otorga … a favor de …”).
   - Se agregan **few-shots** mínimos (ejemplos cortos y claros).
   - Se exige **modo JSON estricto** (sin texto adicional).

6. **Llamada al modelo de IA**
   - Se envía el **texto normalizado** + `json_schema` + reglas/few-shots al modelo de IA.
   - El modelo devuelve un **JSON** con acto, fecha y personas (otorgantes/beneficiarios/indeterminados), incluyendo documentos y domicilio.

7. **Sanitizado del JSON de IA**
   - Se garantiza que `otorgantes[]` y `beneficiarios[]` sean **listas válidas** de personas.
   - Se coloca `fecha_minuta` en **top-level** y se intenta estandarizar a `YYYY-MM-DD`.
   - Se consolidan documentos: **DNI** como principal; otros en `docs_adicionales`.
   - Se aceptan personas en `indeterminados[]` si no hubo bisagra clara.

8. **Validaciones locales y confianza**
   - Se validan **DNI/RUC** por formato (regex) y se ajusta `confidence.campos`.
   - Se valida **fecha** (ES→ISO) y se ajusta confianza si es válida.
   - Se combina la salida del modelo con la **heurística local** para `clasificacion_acto`.

9. **Formateo de la respuesta**
   - Si `view=full`: se retorna el JSON **completo** (`mapped` + `evidence` + `confidence`).
   - Si `view=compact`: se retorna un **resumen legible** (acto, fecha, nombre completo, doc principal —enmascarado por defecto— y dirección).
   - Se incluyen metadatos (`model`, `processing_ms`, `filename`, `text_hash`) y `warnings/errors` si corresponde.

10. **Entrega**
    - Se responde al cliente con la estructura:
      ```
              {
      "ok": true,
      "meta": {
        "model": "gpt-4o-mini",
        "filename": "minuta-demo.docx",
        "pages": 1
      },
      "view": "summary",
      "data": {
        "acto": "PODER",
        "fecha_minuta": "2025-09-30",
        "poderdantes_count": 2,
        "apoderados_count": 1,
        "poderdantes": [
          {
            "nombres": "ALEXANDER",
            "apellido_paterno": "CRUZ",
            "apellido_materno": "MARTICORENA",
            "nacionalidad": "PERUANA",
            "tipo_documento": "DNI",
            "numero_documento": "72924493",
            "profesion_ocupacion": "INGENIERO DE SISTEMAS",
            "estado_civil": "SOLTERO",
            "domicilio": {
              "direccion": "Jr. Cerro Prieto 116",
              "distrito": "Santiago de Surco",
              "provincia": "Lima",
              "departamento": "Lima",
              "ubigeo": ""
            }
          },
          {
            "nombres": "PEITO",
            "apellido_paterno": "MARTINEZ",
            "apellido_materno": "RODRIGUEZ",
            "nacionalidad": "PERUANA",
            "tipo_documento": "DNI",
            "numero_documento": "12345678",
            "profesion_ocupacion": "EMPLEADO",
            "estado_civil": "CASADO",
            "domicilio": {
              "direccion": "Av. Las Palmeras 450",
              "distrito": "San Miguel",
              "provincia": "Lima",
              "departamento": "Lima",
              "ubigeo": ""
            }
          }
        ],
        "apoderados": [
          {
            "nombres": "CAMILA",
            "apellido_paterno": "TORRES",
            "apellido_materno": "VEGA",
            "nacionalidad": "PERUANA",
            "tipo_documento": "DNI",
            "numero_documento": "44556677",
            "profesion_ocupacion": "ABOGADA",
            "estado_civil": "SOLTERA",
            "domicilio": {
              "direccion": "Calle Los Nogales 210",
              "distrito": "Miraflores",
              "provincia": "Lima",
              "departamento": "Lima",
              "ubigeo": ""
            }
          }
        ]
      },
      "errors": [],
      "warnings": []
    }


      ```
    - *(Opcional futuro)*: se registra en **caché** por `raw_text_hash` para evitar recomputar el mismo documento y resistir límites de cuota.

## 5) DIAGRAMA
<img width="1337" height="608" alt="image" src="https://github.com/user-attachments/assets/2410c813-7b01-4665-8c1c-bf2d0393d409" />