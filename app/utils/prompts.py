SCHEMA_JSON = """
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
      "estadoCivil": "",
      "domicilio": {
        "direccion": "",
        "ubigeo": {
          "distrito": "",
          "provincia": "",
          "departamento": ""
        }
      },
      "rol": "APODERADO"
    }
  ]
}
""".strip()

def build_poder_prompt(contenido: str, fecha_minuta_hint: str | None):
    fecha_text = f"La fecha de minuta, si se infiere, usar formato YYYY-MM-DD. Hint: {fecha_minuta_hint}." if fecha_minuta_hint else \
                 "La fecha de minuta, si se infiere, usar formato YYYY-MM-DD. Si no existe, usar null."
    return f"""
Eres un extractor de datos notariales. A partir del texto de una minuta de PODER, devuelve EXCLUSIVAMENTE un JSON válido
con el siguiente esquema (sin comentarios adicionales, sin texto fuera del JSON):

Esquema:
{SCHEMA_JSON}

Instrucciones obligatorias:
- Identifica N otorgantes (rol = PODERDANTE) y N beneficiarios (rol = APODERADO).
- No generes "nombreCompleto". Solo devuelve nombres y apellidos por separado.
- Mantén tildes y apóstrofes en apellidos (p. ej., D'BROT).
- Documento: conserva solo dígitos cuando aplique (DNI/CE). Si no aparece, deja "".
- Estado civil: normaliza a los valores del esquema; si no figura, usa "NO_PRECISADO".
- Dirección/Ubigeo: si no se indica provincia/departamento y el texto refiere Lima explícitamente, usa "Lima".
- {fecha_text}
- Si un dato no aparece, deja "" o null según el esquema.
- Devuelve únicamente el JSON final. Nada más.

Texto de entrada:
\"\"\"{contenido}\"\"\"
""".strip()
