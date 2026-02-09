# app/services/openai_service.py
import json
import time
from openai import OpenAI
from app.core.config import settings
from app.utils.json_utils import parse_json_strict

client = OpenAI(api_key=settings.openai_api_key)


def _ms(dt: float) -> float:
    return round(dt * 1000, 2)


def _clip(s: str, max_len: int = 2500) -> str:
    if not s:
        return ""
    return s if len(s) <= max_len else s[:max_len] + f"... [CLIPPED {len(s)} chars]"


class OpenAIService:
    def extract_json(self, prompt: str, trace_id: str | None = None) -> dict:
        """
        Ejecuta el modelo y retorna dict parseado (estricto).
        Además imprime métricas útiles para diagnosticar latencia/outputs.
        """
        t0 = time.perf_counter()

        # Si quieres, puedes setear esto en settings para desactivar logs en prod
        debug = getattr(settings, "openai_debug", True)

        try:
            resp = client.chat.completions.create(
                model=settings.openai_model,
                temperature=0,
                # Esto obliga a objeto JSON (si el modelo lo soporta)
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "Devuelve SOLO un objeto JSON válido. Sin texto adicional."},
                    {"role": "user", "content": prompt},
                ],
            )
        except Exception as e:
            t1 = time.perf_counter()
            if debug:
                print(f"[OPENAI] trace={trace_id} ERROR after {_ms(t1-t0)}ms -> {type(e).__name__}: {e}")
            raise

        t1 = time.perf_counter()

        # ===== Extracción de metadatos útiles =====
        choice = resp.choices[0] if resp.choices else None
        msg = choice.message if choice else None
        text = (msg.content or "").strip() if msg else ""

        usage = getattr(resp, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", None) if usage else None
        completion_tokens = getattr(usage, "completion_tokens", None) if usage else None
        total_tokens = getattr(usage, "total_tokens", None) if usage else None

        finish_reason = getattr(choice, "finish_reason", None) if choice else None

        # request_id / trace (depende versión sdk; a veces viene en resp.response_id o headers internos)
        response_id = getattr(resp, "id", None)

        if debug:
            print(
                "[OPENAI] "
                f"trace={trace_id} "
                f"model={settings.openai_model} "
                f"latency={_ms(t1-t0)}ms "
                f"finish_reason={finish_reason} "
                f"tokens(prompt={prompt_tokens}, completion={completion_tokens}, total={total_tokens}) "
                f"resp_id={response_id}"
            )

            # OJO: esto puede exponer datos sensibles. Úsalo solo en dev.
            print(f"[OPENAI] trace={trace_id} raw_len={len(text)}")
            print("[OPENAI] trace=%s raw_clipped:\n%s" % (trace_id, _clip(text, 3000)))

            # Diagnóstico rápido: ¿parece JSON?
            if text and not text.lstrip().startswith("{"):
                print(f"[OPENAI] trace={trace_id} WARN: respuesta no inicia con '{{'")

        # ===== Parse estricto =====
        try:
            data = parse_json_strict(text)
        except Exception as e:
            if debug:
                print(f"[OPENAI] trace={trace_id} PARSE_ERROR: {type(e).__name__}: {e}")
                # intenta mostrar últimos chars, útil si se cortó el JSON
                tail = text[-500:] if text else ""
                print(f"[OPENAI] trace={trace_id} raw_tail(500):\n{tail}")
            raise

        # (opcional) log de keys
        if debug and isinstance(data, dict):
            print(f"[OPENAI] trace={trace_id} parsed_keys={list(data.keys())[:30]}")

        return data