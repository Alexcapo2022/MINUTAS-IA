import re

def normalize_date_str(raw: str) -> str:
    """
    Convierte fechas de formatos comunes (DD/MM/YYYY, DD-MM-YYYY) a YYYY-MM-DD.
    Si ya está en YYYY-MM-DD lo mantiene. Si no entiende el formato, devuelve el original.
    """
    if not raw:
        return ""
    
    s = raw.strip()
    
    # 1) Caso DD/MM/YYYY o DD-MM-YYYY
    m = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$", s)
    if m:
        day, month, year = m.groups()
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    
    # 2) Caso YYYY-MM-DD (ya correcto)
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s
        
    return s
