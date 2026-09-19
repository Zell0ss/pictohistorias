import json

import pytest
from pydantic import ValidationError

from backend.services.generacion import generate_historia

VALID_JSON = json.dumps({
    "titulo": "Al taller",
    "pasos": [
        {"frase": "Subo al coche", "concepto": "coche", "candidatos_concepto": ["vehiculo", "transporte"]},
        {"frase": "Llegamos al taller", "concepto": "taller", "candidatos_concepto": ["garaje", "mecanico"]},
        {"frase": "Espero un rato", "concepto": "esperar", "candidatos_concepto": ["sentarse", "quieto"]},
        {"frase": "Volvemos a casa", "concepto": "casa", "candidatos_concepto": ["hogar", "vuelta"]},
    ],
})


class FakeTextBlock:
    def __init__(self, text):
        self.text = text


class FakeResponse:
    def __init__(self, text):
        self.content = [FakeTextBlock(text)]


class FakeMessagesAPI:
    def __init__(self, texts):
        self._texts = list(texts)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        text = self._texts.pop(0)
        return FakeResponse(text)


class FakeClient:
    def __init__(self, texts):
        self.messages = FakeMessagesAPI(texts)


def test_generate_historia_returns_on_first_valid_response():
    client = FakeClient([VALID_JSON])

    resultado = generate_historia("texto de ejemplo", [], client)

    assert resultado.titulo == "Al taller"
    assert len(resultado.pasos) == 4
    assert len(client.messages.calls) == 1


def test_generate_historia_includes_prompt_in_user_message_and_conceptos_in_system():
    client = FakeClient([VALID_JSON])

    generate_historia("Vamos al taller", ["coche de mamá"], client)

    primer_mensaje = client.messages.calls[0]["messages"][0]["content"]
    assert primer_mensaje == "Vamos al taller"
    assert "coche de mamá" not in primer_mensaje

    system_prompt = client.messages.calls[0]["system"]
    assert "coche de mamá" in system_prompt
    assert "{{diccionario}}" not in system_prompt


def test_generate_historia_uses_fallback_text_when_diccionario_empty():
    client = FakeClient([VALID_JSON])

    generate_historia("texto", [], client)

    system_prompt = client.messages.calls[0]["system"]
    assert "(ninguno todavía)" in system_prompt
    assert "{{diccionario}}" not in system_prompt


def test_generate_historia_retries_once_on_invalid_json():
    client = FakeClient(["esto no es json", VALID_JSON])

    resultado = generate_historia("texto", [], client)

    assert resultado.titulo == "Al taller"
    assert len(client.messages.calls) == 2
    segundo_mensaje = client.messages.calls[1]["messages"]
    assert any("no es un JSON válido" in m["content"] or "no es un JSON" in m.get("content", "") for m in segundo_mensaje if isinstance(m.get("content"), str))


def test_generate_historia_raises_after_second_failure():
    client = FakeClient(["no json", "sigue sin ser json"])

    with pytest.raises((json.JSONDecodeError, ValidationError)):
        generate_historia("texto", [], client)


def test_generate_historia_fills_quien_escribe_in_system_prompt():
    client = FakeClient([VALID_JSON])

    generate_historia("texto", [], client, escribe="papá")

    system_prompt = client.messages.calls[0]["system"]
    assert "papá" in system_prompt
    assert "{{quien_escribe}}" not in system_prompt


def test_generate_historia_defaults_quien_escribe_to_mama():
    client = FakeClient([VALID_JSON])

    generate_historia("texto", [], client)

    system_prompt = client.messages.calls[0]["system"]
    assert "mamá" in system_prompt
