# app/utils/prompt/service_rules_builder.py
"""
Construye el bloque de REGLAS PARAMETRIZADAS DEL SERVICIO que se inyecta
en el prompt del LLM como placeholder {{service_rules}}.

Depende únicamente del objeto ServicioCnl (o cualquier objeto con los
atributos de parametrización). Sin I/O, sin BD, testeable de forma pura.
"""
from __future__ import annotations

from .prompt_mappers import map_tipo_persona_prompt, map_obligatoriedad_prompt


# ── Helpers internos ────────────────────────────────────────────────────────────

def _safe_int(obj, attr: str, default: int = 0) -> int:
    """Lee un atributo como int; devuelve default si es None o ausente."""
    return int(getattr(obj, attr, None) or default)


def _safe_str(obj, attr: str) -> str:
    """Lee un atributo como str limpio; devuelve '' si es None o ausente."""
    val = getattr(obj, attr, None)
    return (val or "").strip()


# ── Catálogos estandarizados ───────────────────────────────────────────────────

_MEDIOS_PAGO_PERMITIDOS = [
    "DEPOSITO EN CUENTA",
    "GIRO",
    "TRANSFERENCIA DE FONDOS",
    "ORDEN DE PAGO",
    "TARJETA DE DEBITO",
    "TARJETA DE CREDITO EMITIDA EN EL PAIS",
    "CHEQUE DE GERENCIA",
    "EFECTIVO 008- MENORES A 5000",
    "EFECTIVO 009- EN LOS DEMAS CASOS",
    "MEDIOS DE PAGO USADOS EN COMERCIO EXTERIOR",
    "DOCUMENTOS DE EDPYMES Y COOPERATIVAS DE AHORRO Y CREDITO",
    "TARJETA DE CREDITO EMITIDA O NO EN EL PAIS POR ENT",
    "TARJETAS DE CREDITO EMITIDAS EN EL EXTERIOR POR BA",
    "BIEN MUEBLE",
    "BIEN INMUEBLE",
    "OTROS MEDIOS DE PAGO",
]

# ── Builders de sección ────────────────────────────────────────────────────────

def _build_participante_rule(
    *,
    min_value: int,
    tipo_value: int,
    label_custom: str,
    label_default: str,
    field_path: str,
) -> str:
    """
    Genera el bloque de regla para un rol de participante (otorgante / beneficiario / otro).

    Args:
        min_value     : mínimo de participantes requeridos (0 = no aplica).
        tipo_value    : tipo de persona (0-3).
        label_custom  : nombre personalizado desde BD (p.ej. "VENDEDOR"). Puede ser "".
        label_default : label genérico (p.ej. "OTORGANTES").
        field_path    : ruta en el JSON de salida (p.ej. "participantes.otorgantes").
    """
    if min_value <= 0:
        return ""

    label = label_custom.upper() if label_custom else label_default

    lines = [
        f"- {label}:",
        f"  - Debes intentar identificar como mínimo {min_value} participante(s) en {field_path}.",
    ]

    tipo_txt = map_tipo_persona_prompt(tipo_value)
    if tipo_value > 0:
        lines.append(f"  - Tipo de persona permitido: {tipo_txt}.")

    if tipo_value in (2, 3):
        lines.append(
            "  - Si el tipo permitido incluye PERSONA JURIDICA, presta especial atención a: "
            "RUC, razón social, siglas societarias (S.A., S.A.C., S.R.L., E.I.R.L., S.C.R.L., S.A.A.), "
            'expresiones como "empresa", "sociedad", "asociación", "representada por", '
            '"representante legal", "gerente general", "apoderado de la empresa", "por intermedio de".'
        )

    if tipo_value in (2, 3):
        lines.append(
            "  - REGLA DE REPRESENTACIÓN: Si detectas una PERSONA JURIDICA actuando a través "
            "de un representante natural con DNI, extrae a AMBOS como objetos separados "
            "(Empresa + Persona) en esta misma lista. En 'relacion' del representante pon "
            "EXACTAMENTE: 'REPRESENTANTE DE [NOMBRE DE LA EMPRESA]'."
        )

    return "\n".join(lines)


def _build_valores_rule(in_valor: int) -> str:
    """Genera las instrucciones para extraer el precio o valor de transferencia."""
    if in_valor <= 0:
        return ""

    estado = map_obligatoriedad_prompt(in_valor)
    lines = [
        "- VALOR DE TRANSFERENCIA:",
        f"  - Estado: {estado}.",
        "  - UBICA EN EL TEXTO el precio o valor acordado para la transacción."
    ]
    return "\n".join(lines)


def _build_medio_pago_rule(in_medio_pago: int) -> str:
    if in_medio_pago <= 0:
        return ""

    estado = map_obligatoriedad_prompt(in_medio_pago)
    lines = [
        "- MEDIO DE PAGO:",
        f"  - Estado: {estado}.",
    ]
    if in_medio_pago == 1:
        lines.append(
            "  - MEDIO PAGO EXACTO: El campo 'medio_pago' dentro de valores.medioPago[] DEBE ser UNO de estos exactos "
            "(si no se especifica escoge OTROS MEDIOS DE PAGO):"
        )
        lines.append(
            "    DEPOSITO EN CUENTA, GIRO, TRANSFERENCIA DE FONDOS, ORDEN DE PAGO, TARJETA DE DEBITO, "
            "TARJETA DE CREDITO EMITIDA EN EL PAIS, CHEQUE DE GERENCIA, EFECTIVO 008- MENORES A 5000, "
            "EFECTIVO 009- EN LOS DEMAS CASOS, MEDIOS DE PAGO USADOS EN COMERCIO EXTERIOR, "
            "DOCUMENTOS DE EDPYMES Y COOPERATIVAS DE AHORRO Y CREDITO, TARJETA DE CREDITO EMITIDA O NO EN EL PAIS POR ENT, "
            "TARJETAS DE CREDITO EMITIDAS EN EL EXTERIOR POR BA, TARJETAS DE CREDITO EMITIDAS EN EL EXTERIOR POR BA, BIEN MUEBLE, BIEN INMUEBLE, OTROS MEDIOS DE PAGO"
        )
        lines.append(
            "    - RESTRICCIÓN: Si el texto menciona 'cheque de gerencia', el valor DEBE ser 'CHEQUE DE GERENCIA'."
        )
        lines.append(
            "    - Si mencionan bancos, anótalos en el campo 'bancos' del mismo objeto."
        )

    return "\n".join(lines)


def _build_bienes_rule(in_bienes: int, in_aporte_bienes: int) -> str:
    """Genera las instrucciones para extraer bienes y manejar aportes en especie."""
    if in_bienes <= 0:
        return ""

    estado = map_obligatoriedad_prompt(in_bienes)
    lines = [
        "- BIENES FÍSICOS O INTANGIBLES:",
        f"  - Estado: {map_obligatoriedad_prompt(in_bienes)}.",
        "  - UBICA EN EL TEXTO la tabla o lista donde se describen los bienes aportados.",
        "  - IMPORTANTE (DISTRITO): El ubigeo (Distrito, Provincia) del bien DEBE ser el de "
        "la ubicación física del inmueble descrito, NO el domicilio de los otorgantes.",
        "  - REGLAS ESTRICTAS DE AGRUPACIÓN (¡LEER CON CUIDADO!):",
        "    1. BIENES CON PARTIDA REGISTRAL (Vehículos, Inmuebles, Terrenos, etc.):",
        "       - Si el bien especifica una Partida Registral, **ES OBLIGATORIO** crear UN OBJETO INDIVIDUAL para CADA uno de ellos.",
        "       - El campo 'partida_registral' debe ser mapeado exactamente.",
        "    2. BIENES SIN PARTIDA REGISTRAL (Muebles, computadoras, estantes, sillas, etc.):",
        "       - **PUEDES AGRUPARLOS**. No es necesario listar silla por silla.",
        "       - Crea 1 solo objeto por aportante que resuma estos bienes.",
        "       - El campo 'otros_bienes' puede ser un resumen como 'APORTES EN BIENES NO DINERARIOS DE [NOMBRE DEL OTORGANTE]'.",
        "       - El campo 'tipo_bien' debe ser 'BIENES' y 'clase_bien' 'OTROS NO ESPECIFICADOS'."
    ]

    if in_aporte_bienes == 1:
        lines += [
            "  - APORTE DE CAPITAL CON BIENES O DINERO (REGLAS OBLIGATORIAS):",
            "    1) En 'valores.transferencia': 1 solo objeto con el monto TOTAL SUMADO de todos los aportes del contrato.",
            "    2) En 'valores.medioPago': Evalúa de qué forma aportó cada persona:",
            "       - Si aportó DINERO (Efectivo, Depósito, Transferencia): Usa el medio de pago financiero correspondiente (ej. 'DEPOSITO EN CUENTA', 'EFECTIVO 008...'). NUNCA uses 'BIEN MUEBLE' para dinero.",
            "       - Si aportó BIENES FÍSICOS (muebles, vehículos, inmuebles): Usa 'BIEN MUEBLE' o 'BIEN INMUEBLE'.",
            "       - 'valor_bien': El monto que aportó esa persona específica en esa forma de pago.",
            "    3) La suma de los 'monto_aportado' de otorgantes + suma de los 'valor_bien' en medioPago, DEBEN igualar al monto en 'transferencia'."
        ]

    return "\n".join(lines)


def _build_oportunidad_pago_rule(in_oportunidad_pago: int) -> str:
    if in_oportunidad_pago <= 0:
        return ""

    estado = map_obligatoriedad_prompt(in_oportunidad_pago)
    lines = [
        "- OPORTUNIDAD DE PAGO:",
        f"  - Estado: {estado}.",
    ]

    if in_oportunidad_pago == 1:
        lines.append(
            '  - Revisa con especial cuidado expresiones como: "al contado", "contra firma", '
            '"ya cancelado", "cancelado con anterioridad", "se pagará", "se cancela", '
            '"pagado", "pendiente de pago", "a plazos".'
        )

    return "\n".join(lines)


def _build_reconciliacion_rule(in_valor: int, in_medio_pago: int) -> str:
    """Inyecta la regla de oro para que los montos de Transferencia y Medio de Pago coincidan."""
    # Si pedimos medio de pago, SIEMPRE pedimos reconciliación (aunque in_valor sea 0)
    if in_medio_pago >= 1:
        return (
            "- REGLA DE RECONCILIACIÓN FINANCIERA (CRÍTICO):\n"
            "  - El monto total en 'valores.transferencia' DEBE IGUALAR a la suma en 'valores.medioPago'.\n"
            "  - NUNCA dejes el campo 'valor_bien' en 0.0 si el servicio tiene un monto de transferencia.\n"
            "  - Si solo hay 1 transferencia, el medio de pago DEBE tener ese mismo monto."
        )
    return ""


# ── Función Principal: Orquestador ──────────────────────────────────────────

def build_service_rules_text(servicio_obj: object) -> str:
    """
    Genera el bloque completo de reglas parametrizadas para inyectar en el prompt.

    Returns:
        str: Texto multilínea listo para usar como {{service_rules}}.
             Retorna "" si el objeto es None o todas las columnas están en 0.
    """
    if servicio_obj is None:
        return ""

    # Participantes
    sections = [
        _build_participante_rule(
            min_value=_safe_int(servicio_obj, "min_otorgante"),
            tipo_value=_safe_int(servicio_obj, "in_tipo_otorgante"),
            label_custom=_safe_str(servicio_obj, "no_otorgante"),
            label_default="OTORGANTES",
            field_path="participantes.otorgantes",
        ),
        _build_participante_rule(
            min_value=_safe_int(servicio_obj, "min_beneficiario"),
            tipo_value=_safe_int(servicio_obj, "in_tipo_beneficiario"),
            label_custom=_safe_str(servicio_obj, "no_beneficiario"),
            label_default="BENEFICIARIOS",
            field_path="participantes.beneficiarios",
        ),
        _build_participante_rule(
            min_value=_safe_int(servicio_obj, "min_otro"),
            tipo_value=_safe_int(servicio_obj, "in_tipo_otro"),
            label_custom=_safe_str(servicio_obj, "no_otro"),
            label_default="OTROS / TERCEROS",
            field_path="participantes.otorgantes",  # los "otros" suelen ir en otorgantes
        ),
        # Valores
        _build_valores_rule(_safe_int(servicio_obj, "in_valor")),
        _build_medio_pago_rule(_safe_int(servicio_obj, "in_medio_pago")),
        _build_oportunidad_pago_rule(_safe_int(servicio_obj, "in_oportunidad_pago")),
        # Reconciliación (si aplica)
        _build_reconciliacion_rule(
            in_valor=_safe_int(servicio_obj, "in_valor"),
            in_medio_pago=_safe_int(servicio_obj, "in_medio_pago"),
        ),
        # Bienes
        _build_bienes_rule(
            in_bienes=_safe_int(servicio_obj, "in_bienes"),
            in_aporte_bienes=_safe_int(servicio_obj, "in_aporte_bienes"),
        ),
    ]

    sections = [s.strip() for s in sections if s and s.strip()]

    if not sections:
        return ""

    return (
        "REGLAS PARAMETRIZADAS DEL SERVICIO (OBLIGATORIAS):\n"
        + "\n\n".join(sections)
    )
