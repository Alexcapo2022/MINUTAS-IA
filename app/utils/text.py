import re

def normalize_space(t: str) -> str:
    return re.sub(r"\s+", " ", t or "").strip()

def mask_doc(doc: str) -> str:
    if not doc or len(doc) < 4:
        return doc or ""
    # enmascara todo menos los 4 últimos
    return f"{doc[:-4].replace(doc[:-4],'*' * len(doc[:-4]))}{doc[-4:]}"

def full_name(nombres: str, ap_p: str, ap_m: str) -> str:
    parts = [p for p in [nombres, ap_p, ap_m] if p]
    return " ".join(parts)
