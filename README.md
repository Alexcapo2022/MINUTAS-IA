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

## 3) Arquitectura (carpetas y capas)

