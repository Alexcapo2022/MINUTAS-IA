# app/services/minuta_service.py
import time
import uuid
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.models.minuta import HCredencialSeguridad, PSeguridad
from app.models.servicio_cnl import ServicioCnl
from app.models.servicio_cnl_prompt import ServicioCnlPrompt

from app.repositories.prompt_repository import PromptRepository
from app.repositories.ciiu_repository import CiiuRepository
from app.repositories.minuta_repository import MinutaRepository
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
from app.utils.prompt import build_service_rules_text

from app.schemas.payload_schemas import CanonicalPayload


def _ms(dt: float) -> float:
    return round(dt * 1000, 2)

class MinutaService:
    def __init__(self, db: Session):
        self.db = db
        self.prompt_repo = PromptRepository(db)
        self.ciiu_repo = CiiuRepository(db)
        self.minuta_repo = MinutaRepository(db)
        self.ai = OpenAIService()

    async def extract(
        self,
        file: UploadFile,
        co_cnl: str,
        token: str = None,
        fecha_minuta_hint: str | None = None,
    ) -> dict:
        t_total0 = time.perf_counter()
        t0 = time.perf_counter()

        # 0) Validar Seguridad Token
        if not token:
            raise HTTPException(status_code=400, detail="falta token")

        credencial = self.db.query(HCredencialSeguridad).join(
            PSeguridad, HCredencialSeguridad.co_seguridad == PSeguridad.co_seguridad
        ).filter(
            HCredencialSeguridad.no_token_api == token,
            HCredencialSeguridad.in_estado == 1
        ).first()

        if not credencial:
            raise HTTPException(status_code=400, detail="token incorrecto")

        co_seguridad_val = credencial.co_seguridad
        no_notaria_val = credencial.seguridad.name

        # 1) Texto del archivo
        contenido = await get_text_from_upload(file)
        
        # Capturamos el binario para persistencia posterior
        await file.seek(0)
        docx_bytes = await file.read()
        
        t1 = time.perf_counter()
        print(
            f"[MINUTA] t1(get_text)={_ms(t1-t0)}ms"
        )

        # 2) Validar existencia del Servicio y Configuración de Prompt
        t0 = time.perf_counter()
        
        # Primero: ¿Existe el servicio en el maestro?
        servicio_master = self.db.query(ServicioCnl).filter(
            ServicioCnl.co_cnl == co_cnl,
            ServicioCnl.in_estado == 1
        ).first()
        
        if not servicio_master:
            raise HTTPException(status_code=400, detail="servicio no disponible")

        # Segundo: ¿Tiene un prompt activo configurado?
        row = self.prompt_repo.get_prompt_and_servicio_by_co_cnl(co_cnl)
        t2 = time.perf_counter()
        print(f"[MINUTA] t2(prompt_repo)={_ms(t2-t0)}ms")

        if not row:
            raise HTTPException(status_code=400, detail="servicio no disponible")

        prompt_obj = row.get("prompt") if isinstance(row, dict) else None
        nombre_servicio = (row.get("de_servicio") or "").strip() if isinstance(row, dict) else ""
        servicio_obj = row.get("servicio_obj") if isinstance(row, dict) else None  # ← Step 2.5

        template = (getattr(prompt_obj, "de_promp", "") or "").strip()

        if not template:
            raise HTTPException(
                status_code=404,
                detail=f"Prompt vacío/no encontrado para co_cnl={co_cnl}",
            )

        # 2.5) Reglas de negocio parametrizadas del servicio (sin I/O de BD)
        t0 = time.perf_counter()
        service_rules = build_service_rules_text(servicio_obj)
        t2b = time.perf_counter()
        print(
            f"[MINUTA] t2.5(service_rules)={_ms(t2b-t0)}ms "
            f"| len={len(service_rules)} "
            f"| active={'{{service_rules}}' in template}"
        )
        if service_rules:
            print(f"[MINUTA] service_rules:\n{service_rules}")

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
            base_payload.acto.fecha_minuta = fecha_minuta_hint
        t4 = time.perf_counter()
        print(f"[MINUTA] t4(base_payload)={_ms(t4-t0)}ms")

        # 5) Render template con placeholders (incluye {{service_rules}})
        t0 = time.perf_counter()
        final_prompt = render_template(
            template,
            {
                "co_cnl": co_cnl,
                "contenido": contenido,
                "fecha_minuta_hint": fecha_minuta_hint or "",
                "ciiu_catalogo": ciiu_catalogo,
                "reglas_servicio": service_rules,
                "payload_base": base_payload.model_dump(by_alias=True),
            },
        )
        t5 = time.perf_counter()
        print(f"[MINUTA] t5(render_template)={_ms(t5-t0)}ms | prompt_len={len(final_prompt or '')}")

        # 6) LLM
        t0 = time.perf_counter()
        trace_id = uuid.uuid4().hex[:8]
        raw, telemetry = self.ai.extract_json(final_prompt, trace_id=trace_id)
        t6 = time.perf_counter()
        print(f"[MINUTA] trace={trace_id} t6(llm_extract_json)={_ms(t6-t0)}ms")

        # 7) Merge base + LLM
        t0 = time.perf_counter()
        llm_payload = self._extract_payload_object(raw)
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
            raise HTTPException(
                status_code=422,
                detail={"message": "El payload devuelto no cumple el schema estándar", "errors": e.errors()},
            )
        t8 = time.perf_counter()
        print(f"[MINUTA] t8(pydantic_validate)={_ms(t8-t0)}ms")

        # 9) Normalización final (con catálogos)
        pais_repo = PaisRepository(self.db)
        doc_repo = TipoDocumentoRepository(self.db)
        ocup_repo = OcupacionRepository(self.db)
        ec_repo = EstadoCivilRepository(self.db)
        moneda_repo = MonedaRepository(self.db)
        zona_repo = ZonaRegistralRepository(self.db)
        
        payload_dump = canonical.model_dump(by_alias=True)
        acto_p = (payload_dump.get("payload", payload_dump).get("acto") or {})
        nombre_servicio_p = (acto_p.get("nombre_servicio") or "").strip()

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
            nombre_servicio=nombre_servicio_p,
            min_otro=int(getattr(servicio_obj, "min_otro", 0) or 0),
        )

        final_payload = cleaned
        while isinstance(final_payload, dict) and "payload" in final_payload:
            final_payload = final_payload["payload"]

        if isinstance(final_payload, dict) and "co_cnl" in final_payload:
            final_payload.pop("co_cnl", None)

        t_total1 = time.perf_counter()
        print(f"[MINUTA] TOTAL={_ms(t_total1 - t_total0)}ms\n")

        # 10) Persistencia Histórica
        id_consulta_out = None
        try:
            audit_dict = {
                "raw_json": telemetry.get("raw_text"),
                "prompt_tokens": telemetry.get("prompt_tokens"),
                "completion_tokens": telemetry.get("completion_tokens"),
                "model": telemetry.get("model"),
                "latency_ms": telemetry.get("latency_ms"),
                "metadata_json": {"trace_id": trace_id}
            }
            consulta_obj = self.minuta_repo.save_full_minuta(
                payload=final_payload,
                docx_bytes=docx_bytes,
                co_cnl=co_cnl,
                estado="EXITO",
                audit_data=audit_dict,
                co_seguridad=co_seguridad_val,
                no_notaria=no_notaria_val
            )
            id_consulta_out = consulta_obj.id_consulta
        except Exception as e:
            print(f"[MINUTA] Error al guardar histórico (no crítico): {e}")
            
        if id_consulta_out and isinstance(final_payload, dict):
            final_payload["id_consulta"] = id_consulta_out

        return {
            "co_cnl": co_cnl,
            "payload": final_payload,
        }

    def _extract_payload_object(self, raw: dict) -> dict:
        if not isinstance(raw, dict): return {}
        obj = raw
        while isinstance(obj, dict) and "payload" in obj:
            obj = obj["payload"]
        return obj

    def _deep_merge_dict(self, base: dict, incoming: dict) -> dict:
        if not isinstance(base, dict) or not isinstance(incoming, dict): return base
        out = dict(base)
        for k, v in incoming.items():
            if k not in out: out[k] = v
            elif isinstance(out[k], dict) and isinstance(v, dict):
                out[k] = self._deep_merge_dict(out[k], v)
            elif isinstance(out[k], list) and isinstance(v, list):
                out[k] = v if len(v) > 0 else out[k]
            elif self._is_not_empty(v): out[k] = v
        return out

    def _is_not_empty(self, v) -> bool:
        if v is None: return False
        if isinstance(v, str): return v.strip() != ""
        if isinstance(v, (int, float)): return True
        if isinstance(v, (list, dict)): return len(v) > 0
        return True