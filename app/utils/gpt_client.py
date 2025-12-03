from openai import OpenAI
from app.config.settings import settings
from app.utils.prompts import (
    build_poder_prompt,
    build_constitucion_prompt,
    build_compraventa_prompt,  # 👈 nuevo
    build_donacion_prompt,  # 👈 nuevo
)
import json

client = OpenAI(api_key=settings.openai_api_key)

# === PODER (ya existente) ===
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
    data_url = f"data:{mime_type};base64,{image_b64}"
    prompt = build_poder_prompt("(extrae del contenido de la imagen)", fecha_minuta_hint)
    resp = client.chat.completions.create(
        model=settings.openai_model,  # modelo con visión
        temperature=0,
        messages=[
            {"role": "system", "content": "Eres un estricto parser de minutas notariales. Devuelve solo JSON válido."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ]
    )
    text = resp.choices[0].message.content.strip()
    try:
        return json.loads(text)
    except Exception as e:
        raise ValueError(
            f"El modelo no devolvió JSON válido (imagen). Respuesta: {text[:400]} ..."
        ) from e


# === CONSTITUCIONES (ya existente) ===
async def extract_constitucion_text(contenido: str, fecha_minuta_hint: str | None = None) -> dict:
    prompt = build_constitucion_prompt(contenido, fecha_minuta_hint)
    resp = client.chat.completions.create(
        model=settings.openai_model,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "Eres un estricto parser de constituciones societarias peruanas. Devuelve solo JSON válido.",
            },
            {"role": "user", "content": prompt},
        ]
    )
    text = resp.choices[0].message.content.strip()
    try:
        return json.loads(text)
    except Exception as e:
        raise ValueError(
            f"El modelo no devolvió JSON válido (constitución). Respuesta: {text[:400]} ..."
        ) from e


async def extract_constitucion_image(image_b64: str, mime_type: str, fecha_minuta_hint: str | None = None) -> dict:
    data_url = f"data:{mime_type};base64,{image_b64}"
    prompt = build_constitucion_prompt("(extrae del contenido de la imagen)", fecha_minuta_hint)
    resp = client.chat.completions.create(
        model=settings.openai_model,  # modelo con visión
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "Eres un estricto parser de constituciones societarias peruanas. Devuelve solo JSON válido.",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ]
    )
    text = resp.choices[0].message.content.strip()
    try:
        return json.loads(text)
    except Exception as e:
        raise ValueError(
            f"El modelo no devolvió JSON válido (constitución/imagen). Respuesta: {text[:400]} ..."
        ) from e


# === NUEVO: COMPRA-VENTA ===
async def extract_compraventa_text(contenido: str, fecha_minuta_hint: str | None = None) -> dict:
    """
    Extrae la estructura JSON de una minuta de COMPRA-VENTA a partir de texto plano.
    """
    prompt = build_compraventa_prompt(contenido, fecha_minuta_hint)
    resp = client.chat.completions.create(
        model=settings.openai_model,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "Eres un estricto parser de minutas notariales de compra-venta peruanas. Devuelve solo JSON válido.",
            },
            {"role": "user", "content": prompt},
        ]
    )
    text = resp.choices[0].message.content.strip()
    try:
        return json.loads(text)
    except Exception as e:
        raise ValueError(
            f"El modelo no devolvió JSON válido (compra-venta). Respuesta: {text[:400]} ..."
        ) from e


async def extract_compraventa_image(
    image_b64: str,
    mime_type: str,
    fecha_minuta_hint: str | None = None,
) -> dict:
    """
    Extrae la estructura JSON de una minuta de COMPRA-VENTA a partir de una imagen (PDF escaneado, foto, etc.).
    """
    data_url = f"data:{mime_type};base64,{image_b64}"
    prompt = build_compraventa_prompt("(extrae del contenido de la imagen)", fecha_minuta_hint)
    resp = client.chat.completions.create(
        model=settings.openai_model,  # debe ser modelo con visión
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "Eres un estricto parser de minutas notariales de compra-venta peruanas. Devuelve solo JSON válido.",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ]
    )
    text = resp.choices[0].message.content.strip()
    try:
        return json.loads(text)
    except Exception as e:
        raise ValueError(
            f"El modelo no devolvió JSON válido (compra-venta/imagen). Respuesta: {text[:400]} ..."
        ) from e

async def extract_donacion_text(
    contenido: str,
    fecha_minuta_hint: str | None = None
) -> dict:
    prompt = build_donacion_prompt(contenido, fecha_minuta_hint)
    resp = client.chat.completions.create(
        model=settings.openai_model,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "Eres un estricto parser de minutas notariales de donación. Devuelve solo JSON válido.",
            },
            {"role": "user", "content": prompt},
        ],
    )
    text = resp.choices[0].message.content.strip()
    try:
        return json.loads(text)
    except Exception as e:
        raise ValueError(
            f"El modelo no devolvió JSON válido (donación). Respuesta: {text[:400]} ..."
        ) from e