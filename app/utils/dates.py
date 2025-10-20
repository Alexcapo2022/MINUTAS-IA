import re
from typing import Tuple

MONTHS = {
    "enero":"01","febrero":"02","marzo":"03","abril":"04","mayo":"05","junio":"06",
    "julio":"07","agosto":"08","septiembre":"09","setiembre":"09","octubre":"10","noviembre":"11","diciembre":"12"
}

def to_iso_date(text: str) -> Tuple[str, float]:
    if not text:
        return "", 0.0
    m = re.search(r"\b([0-3]?\d)[/.\-]([01]?\d)[/.\-]((?:19|20)\d{2})\b", text)
    if m:
        d, mo, y = m.groups()
        return f"{y}-{str(mo).zfill(2)}-{str(d).zfill(2)}", 0.9
    m = re.search(r"\b([0-3]?\d)\s+de\s+([a-záéíóú]+)\s+de\s+((?:19|20)\d{2})\b", text, flags=re.IGNORECASE)
    if m:
        d, mon, y = m.groups()
        mon_num = MONTHS.get(mon.lower())
        if mon_num:
            return f"{y}-{mon_num}-{str(int(d)).zfill(2)}", 0.85
    m = re.search(r"\b([a-záéíóú]+)\s+([0-3]?\d),\s*((?:19|20)\d{2})\b", text, flags=re.IGNORECASE)
    if m:
        mon, d, y = m.groups()
        mon_num = MONTHS.get(mon.lower())
        if mon_num:
            return f"{y}-{mon_num}-{str(int(d)).zfill(2)}", 0.75
    return "", 0.0
