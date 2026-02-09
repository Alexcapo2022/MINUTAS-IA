# app/services/minuta_service.py
import json
import time
import uuid
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.repositories.prompt_repository import PromptRepository
from app.repositories.ciiu_repository import CiiuRepository
from app.repositories.catalogos_repository import (
    PaisRepository,
    TipoDocumentoRepository,
    OcupacionRepository,
    EstadoCivilRepository,
    MonedaRepository,
    ZonaRegistralRepository,
)
from app.services.openai_service import OpenAIService
from app.utils.ingestion import get_text_from_upload
from app.utils.parsing.payload import normalize_payload
from app.utils.template import render_template

from app.schemas.payload_schemas import CanonicalPayload


def _ms(dt: float) -> float:
    return round(dt * 1000, 2)

class MinutaService:
    def __init__(self, db: Session):
        self.db = db
        self.prompt_repo = PromptRepository(db)
        self.ciiu_repo = CiiuRepository(db)
        self.ai = OpenAIService()

    async def extract(
        self,
        file: UploadFile,
        co_cnl: str,
        fecha_minuta_hint: str | None = None,
    ) -> dict:
        t_total0 = time.perf_counter()
        t0 = time.perf_counter()

        # 1) Texto del archivo
        contenido = await get_text_from_upload(file)
        t1 = time.perf_counter()
        print(
            f"[MINUTA] t1(get_text)={_ms(t1-t0)}ms"
        )

        # 2) Prompt + Servicio desde BD
        t0 = time.perf_counter()
        row = self.prompt_repo.get_prompt_and_servicio_by_co_cnl(co_cnl)
        t2 = time.perf_counter()
        print(f"[MINUTA] t2(prompt_repo)={_ms(t2-t0)}ms")

        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"No existe prompt/servicio activo para co_cnl={co_cnl}",
            )

        prompt_obj = row.get("prompt") if isinstance(row, dict) else None
        nombre_servicio = (row.get("de_servicio") or "").strip() if isinstance(row, dict) else ""

        template = (getattr(prompt_obj, "de_promp", "") or "").strip()

        if not template:
            raise HTTPException(
                status_code=404,
                detail=f"Prompt vacío/no encontrado para co_cnl={co_cnl}",
            )

        # 3) Catálogo CIIU (solo si el prompt lo necesita)
        t0 = time.perf_counter()
        ciiu_catalogo = ""
        if "{{ciiu_catalogo}}" in template:
            ciiu_catalogo = self.ciiu_repo.format_catalogo_for_prompt()
        t3 = time.perf_counter()
        print(f"[MINUTA] t3(ciiu_catalogo)={_ms(t3-t0)}ms | used={'{{ciiu_catalogo}}' in template}")

        # 4) Backend arma payload base (ESTÁNDAR)
        t0 = time.perf_counter()
        base_payload = CanonicalPayload()
        base_payload.acto.nombre_servicio = nombre_servicio
        if fecha_minuta_hint:
            base_payload.acto.fechaMinuta = fecha_minuta_hint
        t4 = time.perf_counter()
        print(f"[MINUTA] t4(base_payload)={_ms(t4-t0)}ms")

        # 5) Render template con placeholders
        t0 = time.perf_counter()
        final_prompt = render_template(
            template,
            {
                "co_cnl": co_cnl,
                "contenido": contenido,
                "fecha_minuta_hint": fecha_minuta_hint or "",
                "ciiu_catalogo": ciiu_catalogo,
                "payload_base": base_payload.model_dump(by_alias=True),
            },
        )
        t5 = time.perf_counter()
        print(f"[MINUTA] t5(render_template)={_ms(t5-t0)}ms | prompt_len={len(final_prompt or '')}")

        # 6) LLM
        t0 = time.perf_counter()
        trace_id = uuid.uuid4().hex[:8]
        raw = self.ai.extract_json(final_prompt, trace_id=trace_id)
        t6 = time.perf_counter()
        print(f"[MINUTA] trace={trace_id} t6(llm_extract_json)={_ms(t6-t0)}ms")

        # print("\n[MINUTA] RAW (parsed JSON) clipped:")
        # print(_clip_obj(raw, 2500))

        # (unwrap) parte de etapa 6/7, pero lo medimos aparte para ver si afecta
        t0 = time.perf_counter()
        llm_payload = self._extract_payload_object(raw)
        t6b = time.perf_counter()
        print(f"[MINUTA] t6b(unwrap_payload)={_ms(t6b-t0)}ms")

        # print("\n[MINUTA] llm_payload (after unwrap) clipped:")
        # print(_clip_obj(llm_payload, 2500))

        # 7) Merge base + LLM
        t0 = time.perf_counter()
        merged_dict = self._deep_merge_dict(
            base_payload.model_dump(by_alias=True),
            llm_payload,
        )
        t7 = time.perf_counter()
        print(f"[MINUTA] t7(deep_merge)={_ms(t7-t0)}ms")

        # 8) Validación Pydantic
        t0 = time.perf_counter()
        try:
            canonical = CanonicalPayload.model_validate(merged_dict)
        except ValidationError as e:
            t8_err = time.perf_counter()
            print(f"[MINUTA] t8(pydantic_validate)={_ms(t8_err-t0)}ms (FAILED)")
            print("\n[MINUTA] VALIDATION ERROR:", e.errors())
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "El payload devuelto no cumple el schema estándar",
                    "errors": e.errors(),
                },
            )
        t8 = time.perf_counter()
        print(f"[MINUTA] t8(pydantic_validate)={_ms(t8-t0)}ms")

        # 9) Normalización final (con catálogos)
        # Nota: aquí normalmente está el cuello si haces muchas búsquedas a BD por cada campo.
        t0 = time.perf_counter()
        pais_repo = PaisRepository(self.db)
        doc_repo = TipoDocumentoRepository(self.db)
        ocup_repo = OcupacionRepository(self.db)
        ec_repo = EstadoCivilRepository(self.db)
        moneda_repo = MonedaRepository(self.db)
        zona_repo = ZonaRegistralRepository(self.db)
        t9a = time.perf_counter()
        print(f"[MINUTA] t9a(init_repos)={_ms(t9a-t0)}ms")

        t0 = time.perf_counter()
        payload_dump = canonical.model_dump(by_alias=True)

        # intenta leer el servicio desde el payload ya “unwrappeado”
        acto = (payload_dump.get("payload", payload_dump).get("acto") or {}) if isinstance(payload_dump, dict) else {}
        nombre_servicio = (acto.get("nombre_servicio") or "").strip()

        print(f"[MINUTA] normalize_payload input: has_wrapper={'payload' in payload_dump if isinstance(payload_dump, dict) else False}")
        print(f"[MINUTA] normalize_payload nombre_servicio='{nombre_servicio}'")

        cleaned = normalize_payload(
            payload_dump,
            ciiu_repo=self.ciiu_repo,
            pais_repo=pais_repo,
            doc_repo=doc_repo,
            ocup_repo=ocup_repo,
            ec_repo=ec_repo,
            moneda_repo=moneda_repo,
            zona_repo=zona_repo,
            texto_contexto=contenido,
            nombre_servicio=nombre_servicio,   # ✅ CLAVE para CONTADO
        )

        # --- DEBUG MONEDA ---
        try:
            obj = cleaned.get("payload", cleaned)

            t0_tr = ((obj.get("valores", {}) or {}).get("transferencia", []) or [{}])[0] or {}
            t0_mp = ((obj.get("valores", {}) or {}).get("medioPago", []) or [{}])[0] or {}

            print("[MINUTA] DEBUG MONEDA transferencia[0]:",
                f"moneda='{t0_tr.get('moneda')}'",
                f"co_moneda='{t0_tr.get('co_moneda')}'",
                f"monto='{t0_tr.get('monto')}'")

            print("[MINUTA] DEBUG MONEDA medioPago[0]:",
                f"moneda='{t0_mp.get('moneda')}'",
                f"co_moneda='{t0_mp.get('co_moneda')}'",
                f"medio_pago='{t0_mp.get('medio_pago')}'")

        except Exception as e:
            print(f"[MINUTA] DEBUG MONEDA error => {e}")

        t9 = time.perf_counter()
        print(f"[MINUTA] t9(normalize_payload)={_ms(t9-t0)}ms")

        # print("\n[MINUTA] cleaned clipped:")
        # print(_clip_obj(cleaned, 2500))

        # unwrap final (post-9)
        t0 = time.perf_counter()
        final_payload = cleaned
        while (
            isinstance(final_payload, dict)
            and "payload" in final_payload
            and isinstance(final_payload["payload"], dict)
        ):
            final_payload = final_payload["payload"]

        if isinstance(final_payload, dict) and "co_cnl" in final_payload:
            final_payload.pop("co_cnl", None)

        t9b = time.perf_counter()
        print(f"[MINUTA] t9b(final_unwrap_cleanup)={_ms(t9b-t0)}ms")

        t_total1 = time.perf_counter()
        print(f"[MINUTA] TOTAL={_ms(t_total1 - t_total0)}ms\n")

        return {
            "co_cnl": co_cnl,
            "payload": final_payload,
        }

    def _extract_payload_object(self, raw: dict) -> dict:
        if not isinstance(raw, dict):
            return {}

        obj = raw
        while isinstance(obj, dict) and "payload" in obj and isinstance(obj["payload"], dict):
            obj = obj["payload"]

        return obj if isinstance(obj, dict) else {}

    def _deep_merge_dict(self, base: dict, incoming: dict) -> dict:
        if not isinstance(base, dict) or not isinstance(incoming, dict):
            return base

        out = dict(base)

        for k, v in incoming.items():
            if k not in out:
                out[k] = v
                continue

            if isinstance(out[k], dict) and isinstance(v, dict):
                out[k] = self._deep_merge_dict(out[k], v)
                continue

            if isinstance(out[k], list) and isinstance(v, list):
                out[k] = v if len(v) > 0 else out[k]
                continue

            if self._is_not_empty(v):
                out[k] = v

        return out

    def _is_not_empty(self, v) -> bool:
        if v is None:
            return False
        if isinstance(v, str):
            return v.strip() != ""
        if isinstance(v, (int, float)):
            return True   # 0 también cuenta
        if isinstance(v, list):
            return len(v) > 0
        if isinstance(v, dict):
            return len(v) > 0
        return True