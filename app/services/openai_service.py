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
    def extract_json(self, prompt: str, trace_id: str | None = None) -> tuple[dict, dict]:
        """
        Ejecuta el modelo y retorna (dict_parseado, telemetry_dict).
        """
        t0 = time.perf_counter()
        debug = getattr(settings, "openai_debug", True)

        try:
            resp = client.chat.completions.create(
                model=settings.openai_model,
                temperature=0,
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
        latency_ms = _ms(t1 - t0)

        # ===== Extracción de metadatos útiles =====
        choice = resp.choices[0] if resp.choices else None
        msg = choice.message if choice else None
        text = (msg.content or "").strip() if msg else ""

        usage = getattr(resp, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0

        if debug:
            print(
                "[OPENAI] "
                f"trace={trace_id} "
                f"model={settings.openai_model} "
                f"latency={latency_ms}ms "
                f"tokens(prompt={prompt_tokens}, completion={completion_tokens})"
            )
            print(f"[OPENAI] trace={trace_id} raw_len={len(text)}")

        # ===== Parse estricto =====
        try:
            data = parse_json_strict(text)
        except Exception as e:
            if debug:
                print(f"[OPENAI] trace={trace_id} PARSE_ERROR: {type(e).__name__}: {e}")
            raise

        telemetry = {
            "raw_text": text,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "model": settings.openai_model,
            "latency_ms": latency_ms
        }

        return data, telemetry