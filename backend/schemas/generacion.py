from pydantic import BaseModel, Field


class PasoGenerado(BaseModel):
    frase: str = Field(min_length=1)
    concepto: str = Field(min_length=1)
    candidatos_concepto: list[str] = Field(min_length=2, max_length=2)


class HistoriaGenerada(BaseModel):
    titulo: str = Field(min_length=1)
    pasos: list[PasoGenerado] = Field(min_length=4, max_length=8)
