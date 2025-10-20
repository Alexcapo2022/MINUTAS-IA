# app/utils/ubigeo_online.py
from __future__ import annotations
import os, requests, unicodedata, re, json
from functools import lru_cache
from typing import Optional, List, Dict, Any

EAPI_URL = os.getenv("UBIGEO_ONLINE_URL", "https://free.e-api.net.pe/ubigeos.json")
TIMEOUT = float(os.getenv("UBIGEO_HTTP_TIMEOUT", "10"))

HEADERS = {
    "User-Agent": "mvp-minutas/1.0",
    "Accept": "application/json",
}

def _norm(s: str) -> str:
    if not s: return ""
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")  # quita tildes
    s = re.sub(r"[.,;:()\"'“”´`]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip().upper()
    return s

def _alias_dep(s: str) -> str:
    """Normaliza alias comunes de departamento/provincia."""
    s = _norm(s)
    if s in {"LIMA METROPOLITANA", "LIMA (METROPOLITANA)", "PROVINCIA DE LIMA"}:
        return "LIMA"
    return s

def _flatten_tree(tree: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convierte:
    { "AMAZONAS": { "BAGUA": { "ARAMANGO": {"ubigeo":"010202","id":23}, ... }, ... }, ... }
    en:
    [{"departamento":"AMAZONAS","provincia":"BAGUA","distrito":"ARAMANGO","ubigeo":"010202"}, ...]
    """
    out: List[Dict[str, Any]] = []
    for dep, provs in (tree or {}).items():
        if not isinstance(provs, dict): 
            continue
        for prov, dists in provs.items():
            if not isinstance(dists, dict): 
                continue
            for dist, payload in dists.items():
                if not isinstance(payload, dict): 
                    continue
                code = str(payload.get("ubigeo", "")).strip()
                if not code:
                    continue
                out.append({
                    "departamento": dep,
                    "provincia": prov,
                    "distrito": dist,
                    "ubigeo": code.zfill(6) if re.fullmatch(r"\d{6}", code) else code
                })
    return out

def _as_list_rows(data: Any) -> List[Dict[str, Any]]:
    # 1) Si ya es lista
    if isinstance(data, list):
        return data
    # 2) Si es dict con árbol D→P→D (y payload con 'ubigeo')
    if isinstance(data, dict):
        try:
            first_lvl = next(iter(data.values()))
            if isinstance(first_lvl, dict):
                second_lvl = next(iter(first_lvl.values()))
                if isinstance(second_lvl, dict):
                    third_lvl = next(iter(second_lvl.values()))
                    if isinstance(third_lvl, dict) and "ubigeo" in third_lvl:
                        return _flatten_tree(data)
        except StopIteration:
            pass
        # 3) Claves contenedoras de lista
        for key in ("data", "items", "ubigeos", "results", "result", "rows", "list"):
            val = data.get(key)
            if isinstance(val, list):
                return val
        # 4) Dict tipo {ubigeo: {...}}
        if data and all(isinstance(v, dict) for v in data.values()):
            out = []
            for k, v in data.items():
                row = dict(v)
                row.setdefault("ubigeo", k)
                out.append(row)
            return out
    # 5) Fallback
    return []

@lru_cache(maxsize=1)
def _fetch_all() -> List[Dict[str, Any]]:
    r = requests.get(EAPI_URL, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    try:
        data = r.json()
    except Exception:
        data = json.loads(r.text)
    return _as_list_rows(data)

def _clear_cache():
    _fetch_all.cache_clear()

def _debug_shape() -> Dict[str, Any]:
    try:
        r = requests.get(EAPI_URL, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        try:
            data = r.json()
        except Exception:
            data = json.loads(r.text)
        parsed = _as_list_rows(data)
        sample = parsed[:2]
        return {
            "ok": True,
            "type": type(data).__name__,
            "top_keys": list(data.keys())[:5] if isinstance(data, dict) else None,
            "parsed_len": len(parsed),
            "sample": sample
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

def find_ubigeo_online(dep: str, prov: str, dist: str) -> Optional[str]:
    dep_n, prov_n, dist_n = _alias_dep(dep), _alias_dep(prov), _norm(dist)
    try:
        rows = _fetch_all()
    except Exception:
        return None

    # 1) Exacto (dep, prov, dist)
    for row in rows:
        d = _alias_dep(row.get("departamento", ""))
        p = _alias_dep(row.get("provincia", ""))
        di = _norm(row.get("distrito", ""))
        if d == dep_n and p == prov_n and di == dist_n:
            code = str(row.get("ubigeo", "")).strip()
            return code.zfill(6) if re.fullmatch(r"\d{6}", code) else (code or None)

    # 2) Caso Lima/Lima: permitir que provincia == departamento
    for row in rows:
        d = _alias_dep(row.get("departamento", ""))
        p = _alias_dep(row.get("provincia", ""))
        di = _norm(row.get("distrito", ""))
        if d == dep_n and (p == prov_n or p == dep_n) and di == dist_n:
            code = str(row.get("ubigeo", "")).strip()
            return code.zfill(6) if re.fullmatch(r"\d{6}", code) else (code or None)

    # 3) Contains SOLO si dep y prov coinciden exactos (evita cruzar departamentos)
    for row in rows:
        d = _alias_dep(row.get("departamento", ""))
        p = _alias_dep(row.get("provincia", ""))
        di = _norm(row.get("distrito", ""))
        if d == dep_n and p == prov_n and (dist_n in di):
            code = str(row.get("ubigeo", "")).strip()
            return code.zfill(6) if re.fullmatch(r"\d{6}", code) else (code or None)

    return None
