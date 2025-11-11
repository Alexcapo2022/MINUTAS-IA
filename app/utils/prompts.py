# app/utils/prompts.py
from typing import Optional

SCHEMA_PODER_JSON = """
{
  "tipoMinuta": "PODER",
  "fechaMinuta": "YYYY-MM-DD|null",
  "otorgantes": [
    {
      "nombres": "",
      "apellidoPaterno": "",
      "apellidoMaterno": "",
      "nacionalidad": "",
      "tipoDocumento": "DNI|CE|PASAPORTE|OTRO",
      "numeroDocumento": "",
      "profesionOcupacion": "",
      "estadoCivil": "SOLTERO|CASADO|DIVORCIADO|VIUDO|CONVIVIENTE|SEPARADO|NO_PRECISADO",
      "domicilio": {
        "direccion": "",
        "ubigeo": {
          "distrito": "",
          "provincia": "",
          "departamento": ""
        }
      },
      "genero": "MASCULINO|FEMENINO",
      "rol": "PODERDANTE"
    }
  ],
  "beneficiarios": [
    {
      "nombres": "",
      "apellidoPaterno": "",
      "apellidoMaterno": "",
      "nacionalidad": "",
      "tipoDocumento": "DNI|CE|PASAPORTE|OTRO",
      "numeroDocumento": "",
      "profesionOcupacion": "",
      "estadoCivil": "SOLTERO|CASADO|DIVORCIADO|VIUDO|CONVIVIENTE|SEPARADO|NO_PRECISADO",
      "domicilio": {
        "direccion": "",
        "ubigeo": {
          "distrito": "",
          "provincia": "",
          "departamento": ""
        }
      },
      "genero": "MASCULINO|FEMENINO",
      "rol": "APODERADO"
    }
  ]
}
""".strip()


def build_poder_prompt(contenido: str, fecha_minuta_hint: Optional[str]) -> str:
    fecha_text = (
        f"La fecha de minuta, si se infiere, usar formato YYYY-MM-DD. Hint: {fecha_minuta_hint}."
        if fecha_minuta_hint
        else "La fecha de minuta, si se infiere, usar formato YYYY-MM-DD. Si no existe, usar null."
    )

    # La IA INFIERTE el género (binario) y lo inserta en el JSON final
    return f"""
Eres un extractor de datos notariales. A partir del texto de una minuta de PODER, devuelve EXCLUSIVAMENTE un JSON válido
con el siguiente esquema (sin comentarios adicionales, sin texto fuera del JSON):

Esquema:
{SCHEMA_PODER_JSON}

Instrucciones obligatorias:
- Identifica N otorgantes (rol = PODERDANTE) y N beneficiarios (rol = APODERADO).
- No generes "nombreCompleto". Solo devuelve nombres y apellidos por separado.
- Mantén tildes y apóstrofes en apellidos (p. ej., D'BROT).
- Documento: conserva solo dígitos cuando aplique (DNI/CE). Si no aparece, deja "".
- Estado civil: normaliza a los valores del esquema; si no figura, usa "NO_PRECISADO".
- Dirección/Ubigeo: si no se indica provincia/departamento y el texto refiere Lima explícitamente, usa "Lima".
- {fecha_text}
- Si un dato no aparece, deja "" o null según el esquema.

- **Género (OBLIGATORIO y BINARIO)**:
  * NO lo copies literalmente del documento.
  * **Debes INFERIR** el género evaluando nombres, pronombres, tratamientos (Sr., Sra., Don, Doña) y el contexto.
  * Valores permitidos **solo**: "MASCULINO" o "FEMENINO".
  * Si es ambiguo, elige el más probable según el uso del español peruano y el contexto del documento. No uses valores alternos.

- Devuelve únicamente el JSON final. Nada más.

Texto de entrada:
\"\"\"{contenido}\"\"\"
""".strip()

def build_constitucion_prompt(contenido: str, fecha_minuta_hint: str | None = None) -> str:
    schema = """
Devuelve SOLO un JSON válido EXACTAMENTE con este esquema:

{
  "tipoDocumento": "Constitución de Empresa",
  "tipoSociedad": "EIRL|SRL|SAC|SA|Otra",
  "fechaMinuta": "YYYY-MM-DD",

  "otorgantes": [
  {
    "nombres": "string",
    "apellidoPaterno": "string",
    "apellidoMaterno": "string",
    "documento": { "tipo": "DNI|CE|PAS", "numero": "string" },
    "nacionalidad": "string",
    "estadoCivil": "string",
    "domicilio": {
      "direccion": "string",
      "ubigeo": { "departamento": "string", "provincia": "string", "distrito": "string" }
    },
    "porcentajeParticipacion": 0.0,
    "accionesSuscritas": 0,
    "montoAportado": 0.0,
    "rol": "Titular|Socio|Accionista|Transferente"
  }
],

  "beneficiario": {
    "razonSocial": "string",            // aquí va la denominación social
    "direccion": "string",              // domicilio del beneficiario
    "ubigeo": { "departamento": "string", "provincia": "string", "distrito": "string" },
    "ciiu": ["string"]                  // SOLO descripciones, sin códigos
  },

  "transferencia": [
    { "moneda": "PEN|USD|EUR", "monto": 0.0, "formaPago": "Depósito|Transferencia|Efectivo|Crédito|Otro", "oportunidadPago": "string" }
  ],

  "medioPago": [
    { "medio": "Transferencia|Cheque|Depósito|Efectivo|Otro", "moneda": "PEN|USD|EUR", "valorBien": 0.0 }
  ],

  "bien": [
    { "tipo": "Mueble|Inmueble|Dinero|Otro", "clase": "string", "otrosBienesNoEspecificados": "string" }
  ]
}

Reglas:
- Nada de explicaciones ni markdown; SOLO JSON.
- Si no aparece un dato: "" para strings, 0/0.0 para números, [] para listas.
- ciiu: SOLO descripciones (sin códigos).
"""
    hint = f"\nHint_fechaMinuta: {fecha_minuta_hint}\n" if fecha_minuta_hint else ""
    return f"""{schema}
--- CONTENIDO EXTRAÍDO (texto plano) ---
{contenido}
{hint}"""
