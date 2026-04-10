from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)

def parse_optional_date(date_str: str) -> date | None:
    """
    Intenta parsear un string de fecha (YYYY-MM-DD) a un objeto date de Python.
    Si falla o está vacío, retorna None.
    """
    if not date_str or not isinstance(date_str, str):
        return None
    
    date_str = date_str.strip()
    if not date_str or date_str == "":
        return None

    formats = ["%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
            
    logger.warning(f"No se pudo parsear la fecha: {date_str}")
    return None
