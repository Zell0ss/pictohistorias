import pytest
from pydantic import ValidationError

from backend.schemas.generacion import HistoriaGenerada, PasoGenerado


def _paso(**overrides):
    base = {"frase": "Subo al coche", "concepto": "coche", "candidatos_concepto": ["vehiculo", "transporte"]}
    base.update(overrides)
    return base


def test_historia_generada_accepts_valid_data():
    historia = HistoriaGenerada(titulo="Al taller", pasos=[_paso() for _ in range(4)])
    assert len(historia.pasos) == 4


def test_historia_generada_rejects_fewer_than_4_pasos():
    with pytest.raises(ValidationError):
        HistoriaGenerada(titulo="T", pasos=[_paso() for _ in range(3)])


def test_historia_generada_rejects_more_than_8_pasos():
    with pytest.raises(ValidationError):
        HistoriaGenerada(titulo="T", pasos=[_paso() for _ in range(9)])


def test_paso_generado_rejects_empty_frase():
    with pytest.raises(ValidationError):
        PasoGenerado(**_paso(frase=""))


def test_paso_generado_requires_exactly_two_candidatos():
    with pytest.raises(ValidationError):
        PasoGenerado(**_paso(candidatos_concepto=["solo-uno"]))
    with pytest.raises(ValidationError):
        PasoGenerado(**_paso(candidatos_concepto=["uno", "dos", "tres"]))
