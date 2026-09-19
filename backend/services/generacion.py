import json
from pathlib import Path

from pydantic import ValidationError

from backend.schemas.generacion import HistoriaGenerada

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "historia.md"


def _load_system_prompt(diccionario_conceptos: list[str], quien_escribe: str) -> str:
    template = _PROMPT_PATH.read_text()
    if diccionario_conceptos:
        conceptos_texto = ", ".join(diccionario_conceptos)
    else:
        conceptos_texto = "(ninguno todavía)"
    return (
        template
        .replace("{{diccionario}}", conceptos_texto)
        .replace("{{quien_escribe}}", quien_escribe)
    )


def _build_user_message(prompt: str) -> str:
    return prompt


def _parse_and_validate(texto: str) -> HistoriaGenerada:
    data = json.loads(texto)
    return HistoriaGenerada(**data)


def generate_historia(
    prompt: str,
    diccionario_conceptos: list[str],
    client,
    model: str = "claude-sonnet-4-6",
    temperature: float = 0.7,
    max_tokens: int = 2000,
    escribe: str = "mamá",
) -> HistoriaGenerada:
    system = _load_system_prompt(diccionario_conceptos, escribe)
    user_message = _build_user_message(prompt)
    messages = [{"role": "user", "content": user_message}]

    response = client.messages.create(
        model=model, max_tokens=max_tokens, extra_body={"temperature": temperature},
        system=system, messages=messages,
    )
    texto = response.content[0].text

    try:
        return _parse_and_validate(texto)
    except (json.JSONDecodeError, ValidationError) as primer_error:
        mensajes_reintento = messages + [
            {"role": "assistant", "content": texto},
            {
                "role": "user",
                "content": (
                    f"Tu respuesta no es un JSON válido según el contrato. Error: {primer_error}. "
                    "Devuelve solo el JSON corregido, sin texto alrededor."
                ),
            },
        ]
        response = client.messages.create(
            model=model, max_tokens=max_tokens, extra_body={"temperature": temperature},
            system=system, messages=mensajes_reintento,
        )
        texto = response.content[0].text
        return _parse_and_validate(texto)
