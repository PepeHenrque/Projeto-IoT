"""Modelos Pydantic (contrato da API) do CampusSmart."""
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class AlertLevel(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class Device(BaseModel):
    name: str = Field(examples=["Ar-condicionado"])
    status: str = Field(description="Texto de exibição", examples=["Ligado"])
    on: bool


class Room(BaseModel):
    id: int = Field(examples=[104])
    name: str = Field(examples=["Lab. Informática"])
    floor: str = Field(examples=["1º andar"])
    occupied: bool
    alerts: int = Field(description="Quantidade de alertas ativos da sala")
    lights: bool
    ac: bool = Field(description="Ar-condicionado ligado?")
    last: str = Field(description="Último uso (texto amigável)", examples=["há 2h 15min"])
    devices: list[Device]


class Alert(BaseModel):
    id: int
    room_id: int
    room_name: str
    equip: str = Field(examples=["Ar-condicionado"])
    title: str = Field(examples=["Sala ociosa com AC ligado"])
    priority: str = Field(description="Rótulo em PT-BR", examples=["Alta"])
    level: AlertLevel
    time: str = Field(examples=["há 45min"])


class CutCommandResponse(BaseModel):
    success: bool
    message: str
    room_id: int
    device: str
    command: str = "cut"
    executed_at: datetime
    resolved_alerts: int = Field(description="Alertas removidos por causa do comando")
    room: Room = Field(description="Estado atualizado da sala")


class ErrorResponse(BaseModel):
    detail: str
