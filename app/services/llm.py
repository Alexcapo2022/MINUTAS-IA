import json
from pathlib import Path
from typing import Dict, Any
from openai import OpenAI, APIConnectionError, RateLimitError, APITimeoutError
from app.core.config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_TIMEOUT

client = OpenAI(api_key=OPENAI_API_KEY)

def load_prompt_file() -> str:
    p = Path(__file__).resolve().parents[1] / "prompts" / "extractor.md"
    return p.read_text(encoding="utf-8")

def call_llm_extract(text: str, json_contract: Dict[str, Any]) -> Dict[str, Any]:
    system_and_fewshots = load_prompt_file()
    user_prompt = (
        "json_schema:\n"
        f"{json.dumps(json_contract, ensure_ascii=False)}\n\n"
        "CONTENIDO (texto plano normalizado):\n"
        f"{text}"
    )

    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_and_fewshots},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
        timeout=OPENAI_TIMEOUT,
        response_format={"type": "json_object"}
    )
    return json.loads(resp.choices[0].message.content)
