# app/routers/extract.py
import os
from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from app.core.config import DEFAULT_VIEW, MASK_IDS, OPENAI_MODEL
from app.schemas.base import ExtractOutFull, ExtractMapped
from app.schemas.responses import ApiResponse, ExtractOutCompact, ExtractOutSummary
from app.services.ingest import load_text_and_pages
from app.services.llm import call_llm_extract
from app.services.postprocess import (
    clean_noise,
    classify_is_poder,
    sanitize_llm_out,
    post_validate,
    hash_text,
    make_contract,
    preparse_roles_and_people,
    merge_with_preparsed_candidates,
    apply_fallbacks_from_evidence,
    enrich_with_ubigeo,  # ← completa dom.ubigeo usando lookup online
)
from app.utils.text import mask_doc

router = APIRouter(tags=["extract"])


@router.get("/health")
def health():
    return {"status": "ok", "model": OPENAI_MODEL}


@router.post("/extract", response_model=ApiResponse)
async def extract(
    request: Request,
    file: UploadFile = File(...),
    view: str = DEFAULT_VIEW,
    reveal_id: bool = False,
):
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Archivo vacío")

    # 1) Ingesta
    try:
        raw_text_norm, pages = load_text_and_pages(file.filename, raw)
    except ValueError as ve:
        raise HTTPException(status_code=415, detail=str(ve))

    # 2) Limpieza ligera (una sola vez)
    raw_text_norm = clean_noise(raw_text_norm)

    # 3) Hash + heurística de acto
    text_hash = hash_text(raw_text_norm)
    guess = classify_is_poder(raw_text_norm)

    # 4) Preparser determinístico (roles/personas)
    candidates = preparse_roles_and_people(raw_text_norm)

    # 5) LLM
    try:
        llm_out = call_llm_extract(raw_text_norm, make_contract())
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Falla LLM: {e}")

    # 6) Postproceso base
    llm_out["raw_text_hash"] = text_hash
    mapped_dict = sanitize_llm_out(llm_out, text_hash)
    mapped_dict = post_validate(mapped_dict)

    # 7) Merge determinístico + fallbacks + ubigeo online
    mapped_dict = merge_with_preparsed_candidates(mapped_dict, candidates)
    mapped_dict = apply_fallbacks_from_evidence(mapped_dict)
    mapped_dict = enrich_with_ubigeo(mapped_dict)  # ← rellena ubigeo si hay dep/prov/dist

    # 8) Confianza global (clasificación de acto)
    conf = mapped_dict.setdefault("confidence", {})
    conf["clasificacion_acto"] = max(float(conf.get("clasificacion_acto", 0.0)), guess)

    # 9) Validación final a modelo fuerte
    try:
        mapped = ExtractMapped(**mapped_dict)
    except Exception:
        mapped = ExtractMapped()

    # 10) Meta común
    meta = {
        "model": OPENAI_MODEL,
        "processing_ms": getattr(request.state, "processing_ms", None),
        "pages": pages,
        "filename": file.filename,
        "text_hash": text_hash,
    }

    # 11) Vistas: summary / full / compact
    if view == "summary":
        summary = ExtractOutSummary.from_mapped(mapped).model_dump()
        return ApiResponse(
            ok=True,
            meta={"model": OPENAI_MODEL, "filename": file.filename, "pages": pages},
            view="summary",
            data=summary,
            errors=[],
            warnings=[],
        )

    if view == "full":
        data = ExtractOutFull(
            ok=True,
            filename=file.filename,
            extension=os.path.splitext((file.filename or "").lower())[1],
            pages=pages,
            bytes_size=len(raw),
            text_preview=raw_text_norm[:600],
            text_hash_sha256=text_hash,
            is_poder_guess=guess,
            mapped=mapped,
        ).model_dump()
    else:
        mask_fn = None if reveal_id or not MASK_IDS else mask_doc
        compact = ExtractOutCompact.from_mapped(mapped, mask_fn=mask_fn)
        data = compact.model_dump()

    return ApiResponse(
        ok=True,
        meta=meta,
        view=view if view in ("compact", "full") else "compact",
        data=data,
        errors=[],
        warnings=[],
    )
