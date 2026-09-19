# backend/schemas/api.py
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class HistoriaIn(BaseModel):
    prompt: str


class PasoCandidato(BaseModel):
    id: int
    schematic: bool


class PasoOut(BaseModel):
    id: int
    orden: int
    frase: str
    concepto: str | None
    candidatos_concepto: list[str]
    imagen_tipo: str
    picto_id: int | None
    foto_path: str | None
    candidatos: list[PasoCandidato]
    concepto_ganador: str | None
    score_ganador: float | None


class HistoriaOut(BaseModel):
    id: int
    titulo: str
    prompt: str
    creada: datetime | None = None
    actualizada: datetime | None = None
    archivada: bool
    creada_por: str | None = None
    pasos: list[PasoOut] = []


class HistoriaListItem(BaseModel):
    id: int
    titulo: str
    creada: datetime | None = None
    actualizada: datetime | None = None


class HistoriaPatch(BaseModel):
    titulo: str | None = None
    archivada: bool | None = None


class PasoPatch(BaseModel):
    frase: str | None = None
    picto_id: int | None = None
    foto_path: str | None = None


class FijarIn(BaseModel):
    concepto: str
    alias: list[str] | None = None


class DiccionarioIn(BaseModel):
    concepto: str
    alias: list[str] = []
    tipo: Literal["picto", "foto"] = "picto"
    picto_id: int | None = None
    opciones: dict | None = None


class DiccionarioOut(BaseModel):
    id: int
    concepto: str
    alias: list[str]
    tipo: str
    picto_id: int | None
    foto_path: str | None
    opciones: dict | None
    creado: datetime | None = None


class DiccionarioPatch(BaseModel):
    concepto: str | None = None
    alias: list[str] | None = None
    tipo: Literal["picto", "foto"] | None = None
    picto_id: int | None = None
    opciones: dict | None = None
