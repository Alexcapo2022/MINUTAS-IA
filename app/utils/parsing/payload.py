from typing import Any, Optional

from .uppercase import uppercase_payload
from ..domain.acto import normalize_acto
from ..domain.participante import normalize_participante
from ..domain.pagos import normalize_transferencia, normalize_medio_pago
from ..domain.bien import normalize_bien

def normalize_payload(
    payload: dict,
    ciiu_repo: Optional[Any] = None,
    pais_repo: Optional[Any] = None,
    doc_repo: Optional[Any] = None,
    ocup_repo: Optional[Any] = None,
    ec_repo: Optional[Any] = None,
    moneda_repo: Optional[Any] = None,
    zona_repo: Optional[Any] = None,
    texto_contexto: str = "",
    nombre_servicio: str = "",
) -> dict:
    if not isinstance(payload, dict):
        return payload

    obj = payload
    while isinstance(obj, dict) and "payload" in obj and isinstance(obj["payload"], dict):
        obj = obj["payload"]

    if not isinstance(obj, dict):
        return payload

    obj["acto"] = normalize_acto(obj.get("acto", {}) if isinstance(obj.get("acto"), dict) else {})

    participantes = obj.get("participantes", {})
    if not isinstance(participantes, dict):
        participantes = {"otorgantes": [], "beneficiarios": []}

    otorgantes = participantes.get("otorgantes", [])
    beneficiarios = participantes.get("beneficiarios", [])

    participantes["otorgantes"] = [
        normalize_participante(
            p,
            ciiu_repo=ciiu_repo,
            pais_repo=pais_repo,
            doc_repo=doc_repo,
            ocup_repo=ocup_repo,
            ec_repo=ec_repo,
        )
        for p in (otorgantes if isinstance(otorgantes, list) else [])
    ]
    participantes["beneficiarios"] = [
        normalize_participante(
            p,
            ciiu_repo=ciiu_repo,
            pais_repo=pais_repo,
            doc_repo=doc_repo,
            ocup_repo=ocup_repo,
            ec_repo=ec_repo,
        )
        for p in (beneficiarios if isinstance(beneficiarios, list) else [])
    ]
    obj["participantes"] = participantes

    valores = obj.get("valores", {})
    if not isinstance(valores, dict):
        valores = {"transferencia": [], "medioPago": []}

    transferencia = valores.get("transferencia", [])
    medio_pago = valores.get("medioPago", [])

    valores["transferencia"] = [
        normalize_transferencia(t, moneda_repo=moneda_repo, nombre_servicio=nombre_servicio)
        for t in (transferencia if isinstance(transferencia, list) else [])
    ]
    valores["medioPago"] = [
        normalize_medio_pago(m, moneda_repo=moneda_repo) for m in (medio_pago if isinstance(medio_pago, list) else [])
    ]
    obj["valores"] = valores

    bienes_in = obj.get("bienes", [])
    obj["bienes"] = [
        normalize_bien(b, zona_repo=zona_repo, texto_contexto=texto_contexto)
        for b in (bienes_in if isinstance(bienes_in, list) else [])
    ]

    # ✅ al final, convierte todo a MAYÚSCULAS
    return uppercase_payload(obj)