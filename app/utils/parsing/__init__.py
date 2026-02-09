# Re-export público (para mantener: from app.utils.parsing import normalize_payload, etc)

from .payload import normalize_payload
from .uppercase import uppercase_payload

from ..domain.acto import normalize_acto
from ..domain.participante import normalize_participante
from ..domain.pagos import normalize_transferencia, normalize_medio_pago, normalize_moneda_str
from ..domain.bien import normalize_bien

from ..common.documento import normalize_documento
from ..common.ubicacion import normalize_ubigeo, normalize_domicilio

__all__ = [
    "normalize_payload",
    "uppercase_payload",
    "normalize_acto",
    "normalize_participante",
    "normalize_transferencia",
    "normalize_medio_pago",
    "normalize_moneda_str",
    "normalize_bien",
    "normalize_documento",
    "normalize_ubigeo",
    "normalize_domicilio",
]