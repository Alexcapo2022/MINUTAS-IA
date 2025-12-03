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

CIIU_CATALOGO = [
  "AGRICULTURA GANADERIA CAZA Y SILVICULTURA",
  "PESCA",
  "EXPLOTACION DE MINAS Y CANTERAS",
  "INDUSTRIAS MANUFACTURERAS",
  "SUMINISTRO DE ELECTRICIDAD, GAS Y AGUA",
  "CONSTRUCCION",
  "COMERCIO AL POR MAYOR Y MENOR, REPARACION DE VEHICULOS AUTOMOTORES, ART. DOMESTICOS",
  "HOTELES Y RESTAURANTES",
  "TRANSPORTE,ALMACENAMIENTO Y COMUNICACIONES",
  "INTERMEDIACION FINANCIERA",
  "ACTIVIDADES INMOBILIARIAS, EMPRESARIALES Y DE ALQUILER",
  "ADMINISTRACION PUBLICA Y DEFENSA, PLANES DE SEGURIDAD SOCIAL DE AFILIACION OBLIGATORIA",
  "ENSEÑANZA(PRIVADA)",
  "ACTIVIDADES DE SERVICIOS SOCIALES Y DE SALUD (PRIVADA)",
  "OTRAS ACTIV. DE SERVICIOS COMUNITARIAS, SOCIALES Y PERSONALES",
  "HOGARES PRIVADOS CON SERVICIO DOMESTICO",
  "ORGANIZACIONES Y ORGANOS EXTRATERRITORIALES"
]

def build_constitucion_prompt(contenido: str, fecha_minuta_hint: Optional[str] = None) -> str:
  
    hint = f"\nHint_fechaMinuta: {fecha_minuta_hint}\n" if fecha_minuta_hint else ""
    # Asegúrate de tener CIIU_CATALOGO definido en este módulo:
    # CIIU_CATALOGO = [ "AGRICULTURA GANADERIA CAZA Y SILVICULTURA", "PESCA", ... ]
    catalogo_fmt = "\n".join(f"- {c}" for c in CIIU_CATALOGO)

    schema = f"""
Devuelve SOLO un JSON válido EXACTAMENTE con este esquema:

{{
  "tipoDocumento": "Constitución de Empresa",
  "tipoSociedad": "EIRL|SRL|SAC|SA|Otra",
  "fechaMinuta": "YYYY-MM-DD",

  "otorgantes": [
    {{
      "nombres": "string",
      "apellidoPaterno": "string",
      "apellidoMaterno": "string",
      "documento": {{ "tipo": "DNI|CE|PAS", "numero": "string" }},
      "nacionalidad": "string",
      "estadoCivil": "string",
      "domicilio": {{
        "direccion": "string",
        "ubigeo": {{ "departamento": "string", "provincia": "string", "distrito": "string" }}
      }},
      "porcentajeParticipacion": 0.0,
      "accionesSuscritas": 0,
      "montoAportado": 0.0,
      "genero": "MASCULINO|FEMENINO",
      "rol": "Titular|Socio|Accionista|Transferente"
    }}
  ],

  "beneficiario": {{
    "razonSocial": "string",
    "direccion": "string",
    "ubigeo": {{ "departamento": "string", "provincia": "string", "distrito": "string" }},
    "ciiu": ["string"]   // EXACTAMENTE 1 elemento, tomado del catálogo oficial más cercano al texto
  }},

  "transferencia": [
    {{
      "moneda": "SOLES|DOLARES AMERICANOS|EUROS",
      "monto": 0.0,
      "formaPago": "Contado",
      "oportunidadPago": "A LA FIRMA DEL INSTRUMENTO PÚBLICO PROTOCOLAR"
    }}
  ],

  "medioPago": [
    {{
      "medio": "Transferencia|Cheque|Depósito|Efectivo|Otro",
      "moneda": "SOLES|DOLARES AMERICANOS|EUROS",
      "valorBien": 0.0
    }}
  ],

  "bien": [
    {{ "tipo": "Mueble|Inmueble|Dinero|Otro|BIENES", "clase": "string", "otrosBienesNoEspecificados": "string" }}
  ]
}}

Reglas:
- Nada de explicaciones ni markdown; SOLO JSON.
- Si no aparece un dato: "" para strings, 0/0.0 para números, [] para listas.
- Documento: conserva solo dígitos para DNI/CE cuando aplique (si no, deja tal cual).
- Domicilio/Ubigeo: si el texto refiere Lima explícitamente sin provincia/departamento, usa "Lima" en ambos.
- fechaMinuta: si no puede inferirse, usa "" (cadena vacía).

- Género (OBLIGATORIO y BINARIO):
  * NO lo copies literalmente del documento.
  * Debes INFERIR el género evaluando nombres, pronombres y tratamientos (Sr., Sra., Don, Doña) y el contexto.
  * Valores permitidos solo: "MASCULINO" o "FEMENINO".
  * Si es ambiguo, selecciona el más probable según uso en español peruano.

- CIIU (EXACTAMENTE 1):
  * Primero, del texto, identifica TODAS las menciones/ideas de actividades económicas o giros.
  * Luego, para cada una, calcula su cercanía semántica contra el siguiente CATÁLOGO OFICIAL (elige la MÁS CERCANA):
{catalogo_fmt}
  * Devuelve en "beneficiario.ciiu" un ARRAY con **solo 1** string: la categoría del catálogo más cercana a lo descrito en el documento.
  * Si aparecen varias actividades, escoge la que corresponda a la primera detectada por orden de aparición en el texto.

- Moneda:
  * Normaliza a "SOLES", "DOLARES AMERICANOS" o "EUROS".
  * Ejemplos de normalización:
    - "PEN", "SOL", "SOLES", "S/", "S/." → "SOLES"
    - "USD", "US$", "USD$", "$", "dólares" → "DOLARES AMERICANOS"
    - "EUR", "€", "euros" → "EUROS"

- Transferencia (forma final OBLIGATORIA):
  * Debe contener **EXACTAMENTE 1** objeto.
  * "moneda": usa la moneda predominante/primera ligada al pago del capital; normaliza como se indicó.
  * "monto": **suma** de todos los "valorBien" en el array "medioPago".
  * "formaPago": **"Contado"**.
  * "oportunidadPago": **"A LA FIRMA DEL INSTRUMENTO PÚBLICO PROTOCOLAR"**.

- Medio de pago (detalle):
  * Lista cada concepto con "medio" (Efectivo/Depósito/Transferencia/Cheque/Otro), "moneda", "valorBien".
  * Si el documento describe varias líneas (p. ej., 4× S/1250), deben ir como **múltiples items** en "medioPago".
  * Si no hay valores claros, deja "medioPago": [] y ajusta "transferencia" con monto 0.0.

- Bien (defaults si no hay evidencia):
  * Si no encuentras detalles de bienes, usa por defecto:
    "bien": [{{ "tipo": "BIENES", "clase": "OTROS NO ESPECIFICADOS", "otrosBienesNoEspecificados": "CAPITAL" }}].
"""

    return f"""{schema}
--- CONTENIDO EXTRAÍDO (texto plano) ---
{contenido}
{hint}"""

def build_compraventa_prompt(contenido: str, fecha_minuta_hint: Optional[str] = None) -> str:
    fecha_txt = (
        f"Fecha de minuta: usar formato YYYY-MM-DD. Hint: {fecha_minuta_hint}."
        if fecha_minuta_hint
        else "Fecha de minuta: usar formato YYYY-MM-DD si se puede inferir; en caso contrario, deja \"\"."
    )

    schema = """
Devuelve SOLO un JSON válido EXACTAMENTE con este esquema:

{
  "tipoDocumento": "Compra Venta",
  "fechaMinuta": "YYYY-MM-DD",

  "otorgantes": [
    {
      "nombres": "string",
      "apellidoPaterno": "string",
      "apellidoMaterno": "string",
      "nacionalidad": "string",
      "documento": { "tipo": "DNI|CE|PAS", "numero": "string" },
      "profesionOcupacion": "string",
      "estadoCivil": "string",
      "domicilio": {
        "direccion": "string",
        "ubigeo": { "departamento": "string", "provincia": "string", "distrito": "string" }
      },
      "genero": "MASCULINO|FEMENINO",
      "porcentajeParticipacion": 0.0,
      "numeroAccionesParticipaciones": 0
    }
  ],

  "beneficiarios": [
    {
      "nombres": "string",
      "apellidoPaterno": "string",
      "apellidoMaterno": "string",
      "nacionalidad": "string",
      "documento": { "tipo": "DNI|CE|PAS", "numero": "string" },
      "profesionOcupacion": "string",
      "estadoCivil": "string",
      "domicilio": {
        "direccion": "string",
        "ubigeo": { "departamento": "string", "provincia": "string", "distrito": "string" }
      },
      "genero": "MASCULINO|FEMENINO",
      "porcentajeParticipacion": 0.0,
      "numeroAccionesParticipaciones": 0
    }
  ],

  "transferencia": [
    {
      "moneda": "SOLES|DOLARES AMERICANOS|EUROS",
      "monto": 0.0,
      "formaPago": "Contado|Crédito|Otro",
      "oportunidadPago": "A LA FIRMA DEL INSTRUMENTO PÚBLICO PROTOCOLAR"
    }
  ],

  "medioPago": [
    {
      "medio": "Transferencia|Cheque|Depósito|Efectivo|Otro",
      "moneda": "SOLES|DOLARES AMERICANOS|EUROS",
      "valorBien": 0.0,
      "banco": "string",
      "cuentaBancaria": "string",
      "fechaDocumentoPago": "YYYY-MM-DD|string",
      "numeroDocumentoPago": "string"
    }
  ],

  "bien": [
    {
      "tipo": "Mueble|Inmueble|Dinero|Otro|BIENES",
      "clase": "string",
      "partidaRegistral": "string",
      "ubigeo": { "departamento": "string", "provincia": "string", "distrito": "string" },
      "zonaRegistral": "string",
      "fechaMinuta": "YYYY-MM-DD|string|null"
    }
  ]
}
"""

    return f"""{schema}

Reglas:
- NO escribas explicaciones, ni markdown. SOLO JSON.
- Si un dato no aparece en la minuta:
  - Usa "" para strings, 0/0.0 para números, [] para listas.
- Documento:
  - Para DNI/CE intenta dejar solo dígitos.
- Ubigeo:
  - Si solo se menciona “Lima” sin provincia/departamento, usa "Lima" en los tres campos.
- {fecha_txt}

- Género (OBLIGATORIO y BINARIO):
  * NO lo copies literalmente del texto.
  * Debes INFERIR el género por el nombre, pronombres o tratamientos (Sr., Sra., Don, Doña).
  * Valores permitidos: "MASCULINO" o "FEMENINO".
  * Si es ambiguo, elige el más probable por uso en español peruano.

- Moneda:
  * Normaliza a "SOLES", "DOLARES AMERICANOS" o "EUROS".
  * "PEN","SOL","SOLES","S/","S/." → "SOLES".
  * "USD","US$","USD$","$","dólares" → "DOLARES AMERICANOS".
  * "EUR","€","euros" → "EUROS".

- Transferencia:
  * Debe haber exactamente 1 objeto en el array.
  * "moneda" será la moneda predominante del pago.
  * "monto" será la SUMA de todos los "valorBien" de medioPago.
  * "formaPago": si el texto dice “al contado”, usar "Contado"; si habla de pago en cuotas, usar "Crédito"; si no es claro, "Otro".
  * "oportunidadPago": por defecto "A LA FIRMA DEL INSTRUMENTO PÚBLICO PROTOCOLAR".

- Bien:
  * Si no hay detalle de bien, usar por defecto:
    "tipo": "BIENES",
    "clase": "PREDIOS",
    "partidaRegistral": "",
    "ubigeo": con campos vacíos,
    "zonaRegistral": "",
    "fechaMinuta": la misma fechaMinuta del documento (si existe).

Texto de entrada (minuta de COMPRA-VENTA):
\"\"\"{contenido}\"\"\""""

def build_donacion_prompt(contenido: str, fecha_minuta_hint: Optional[str] = None) -> str:
    fecha_txt = (
        f"Fecha de minuta: usar formato YYYY-MM-DD. Hint: {fecha_minuta_hint}."
        if fecha_minuta_hint
        else 'Fecha de minuta: usar formato YYYY-MM-DD si se puede inferir; si no, deja "".'
    )

    catalogo_fmt = "\n".join(f"- {c}" for c in CIIU_CATALOGO)

    schema = f"""
Devuelve SOLO un JSON válido EXACTAMENTE con este esquema:

{{
  "tipoDocumento": "Donación",
  "fechaMinuta": "YYYY-MM-DD",

  "otorgantePN": [
    {{
      "nombres": "",
      "apellidoPaterno": "",
      "apellidoMaterno": "",
      "nacionalidad": "",
      "documento": {{ "tipo": "DNI|CE|PAS", "numero": "" }},
      "profesionOcupacion": "",
      "estadoCivil": "",
      "domicilio": {{
        "direccion": "",
        "ubigeo": {{ "departamento": "", "provincia": "", "distrito": "" }}
      }},
      "genero": "MASCULINO|FEMENINO",
      "porcentajeParticipacion": 0.0,
      "numeroAccionesParticipaciones": 0
    }}
  ],

  "otorgantePJ": [
    {{
      "razonSocial": "",
      "documento": {{ "tipo": "RUC|OTRO", "numero": "" }},
      "partidaElectronica": "",
      "oficinaRegistral": "",
      "domicilio": {{
        "direccion": "",
        "ubigeo": {{ "departamento": "", "provincia": "", "distrito": "" }}
      }},
      "ciiu": [""],
      "representante": {{
        "nombres": "",
        "apellidoPaterno": "",
        "apellidoMaterno": "",
        "nacionalidad": "",
        "documento": {{ "tipo": "DNI|CE|PAS", "numero": "" }},
        "profesionOcupacion": "",
        "estadoCivil": "",
        "domicilio": {{
          "direccion": "",
          "ubigeo": {{ "departamento": "", "provincia": "", "distrito": "" }}
        }},
        "genero": "MASCULINO|FEMENINO",
        "zonaRegistral": "",
        "partidaElectronica": "",
        "tipoRepresentante": ""
      }}
    }}
  ],

  "beneficiarioPN": [
    {{
      "nombres": "",
      "apellidoPaterno": "",
      "apellidoMaterno": "",
      "nacionalidad": "",
      "documento": {{ "tipo": "DNI|CE|PAS", "numero": "" }},
      "profesionOcupacion": "",
      "estadoCivil": "",
      "domicilio": {{
        "direccion": "",
        "ubigeo": {{ "departamento": "", "provincia": "", "distrito": "" }}
      }},
      "genero": "MASCULINO|FEMENINO",
      "porcentajeParticipacion": 0.0,
      "numeroAccionesParticipaciones": 0
    }}
  ],

  "beneficiarioPJ": [
    {{
      "razonSocial": "",
      "documento": {{ "tipo": "RUC|OTRO", "numero": "" }},
      "partidaElectronica": "",
      "oficinaRegistral": "",
      "domicilio": {{
        "direccion": "",
        "ubigeo": {{ "departamento": "", "provincia": "", "distrito": "" }}
      }},
      "ciiu": [""],
      "representante": {{
        "nombres": "",
        "apellidoPaterno": "",
        "apellidoMaterno": "",
        "nacionalidad": "",
        "documento": {{ "tipo": "DNI|CE|PAS", "numero": "" }},
        "profesionOcupacion": "",
        "estadoCivil": "",
        "domicilio": {{
          "direccion": "",
          "ubigeo": {{ "departamento": "", "provincia": "", "distrito": "" }}
        }},
        "genero": "MASCULINO|FEMENINO",
        "zonaRegistral": "",
        "partidaElectronica": "",
        "tipoRepresentante": ""
      }}
    }}
  ],

  "transferencia": [
    {{
      "moneda": "SOLES|DOLARES AMERICANOS|EUROS",
      "monto": 0.0,
      "formaPago": "Donación|Anticipo",
      "oportunidadPago": ""
    }}
  ],

  "medioPago": [
    {{
      "medio": "Transferencia|Cheque|Depósito|Efectivo|Otro",
      "moneda": "SOLES|DOLARES AMERICANOS|EUROS",
      "valorBien": 0.0
    }}
  ],

  "bien": [
    {{
      "tipo": "Mueble|Inmueble|Dinero|Otro|BIENES",
      "clase": "",
      "ubigeo": {{ "departamento": "", "provincia": "", "distrito": "" }},
      "partidaElectronica": "",
      "zonaRegistral": "",
      "opcionBienMueble": "",
      "placaSerieMotor": "",
      "otrosNoEspecificado": ""
    }}
  ]
}}

"""

    return f"""{schema}

Reglas:
- NO escribas explicaciones ni markdown. SOLO JSON.
- **NUNCA** uses la palabra "string" como valor. Es un placeholder de ejemplo.
  - Si no se menciona un dato: usa "" para strings, 0 o 0.0 para números, [] para listas.
- Documento:
  - Para DNI/CE intenta dejar solo dígitos; para RUC igual.
- Ubigeo:
  - Si solo se menciona Lima sin provincia/departamento, usa "Lima" en los tres campos.
- {fecha_txt}

- Nacionalidad:
  * Si el campo "nacionalidad" está vacío,
    y el documento es DNI,
    y el ubigeo tiene un "departamento" no vacío,
    asume "PERUANA" como nacionalidad.

- Género (OBLIGATORIO y BINARIO):
  * NO copies literalmente el texto (no pongas "DE SEXO FEMENINO" etc).
  * Debes INFERIR género por nombre, pronombres o tratamientos (Sr., Sra., Don, Doña).
  * Valores permitidos: "MASCULINO" o "FEMENINO".
  * Si es ambiguo, elige el más probable según uso en español peruano.

- Moneda:
  * "PEN","SOL","SOLES","S/","S/." → "SOLES".
  * "USD","US$","USD$","$","dólares" → "DOLARES AMERICANOS".
  * "EUR","€","euros" → "EUROS".

- CIIU (EXACTAMENTE 1 categoría por persona jurídica):
  * Para cada persona jurídica (otorgantePJ y beneficiarioPJ), identifica la actividad económica principal.
  * Compara semánticamente contra este CATÁLOGO OFICIAL y elige la categoría MÁS CERCANA:
{catalogo_fmt}
  * En el JSON final, en el campo "ciiu" de cada persona jurídica, devuelve **un array con exactamente 1 string**: la categoría elegida del catálogo.
  * Si NO puedes inferir la actividad → devuelve [""].

- Transferencia:
  * Debe haber EXACTAMENTE 1 objeto.
  * "monto" = suma de todos los "valorBien" de "medioPago".
  * "formaPago": "Donación" si el texto habla de donación pura; "Anticipo" si indica anticipo de legítima.
  * "oportunidadPago": deja vacío si no se menciona nada específico.

Texto de entrada (minuta de DONACIÓN):
\"\"\"{contenido}\"\"\""""


