from openai import OpenAI
from app.config.settings import settings
from app.utils.prompts import build_poder_prompt
import json

client = OpenAI(api_key=settings.openai_api_key)

async def extract_poder_text(contenido: str, fecha_minuta_hint: str | None = None) -> dict:
    prompt = build_poder_prompt(contenido, fecha_minuta_hint)
    resp = client.chat.completions.create(
        model=settings.openai_model,
        temperature=0,
        messages=[
            {"role": "system", "content": "Eres un estricto parser de minutas notariales. Devuelve solo JSON válido."},
            {"role": "user", "content": prompt},
        ]
    )
    text = resp.choices[0].message.content.strip()
    try:
        return json.loads(text)
    except Exception as e:
        raise ValueError(f"El modelo no devolvió JSON válido. Respuesta: {text[:400]} ...") from e

async def extract_poder_image(image_b64: str, mime_type: str, fecha_minuta_hint: str | None = None) -> dict:
    """
    Envía imagen (jpg/png) como vision input.
    """
    data_url = f"data:{mime_type};base64,{image_b64}"
    prompt = build_poder_prompt(contenido="(extrae del contenido de la imagen)", fecha_minuta_hint=fecha_minuta_hint)

    resp = client.chat.completions.create(
        model=settings.openai_model,  # Debe ser un modelo con visión (ej. gpt-4o / gpt-4o-mini)
        temperature=0,
        messages=[
            {"role": "system", "content": "Eres un estricto parser de minutas notariales. Devuelve solo JSON válido."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}}
                ]
            }
        ]
    )
    text = resp.choices[0].message.content.strip()
    try:
        return json.loads(text)
    except Exception as e:
        raise ValueError(f"El modelo no devolvió JSON válido (imagen). Respuesta: {text[:400]} ...") from e
