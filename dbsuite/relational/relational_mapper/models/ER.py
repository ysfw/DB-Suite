from __future__ import annotations

from typing import List, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator

class Attribute(BaseModel):
    name: str
    isPrimaryKey: Optional[bool] = False
    isMultiValued: Optional[bool] = False
    isDerived: Optional[bool] = False
    composite: Optional[List[Union[str, Attribute]]] = None

class Entity(BaseModel):
    name: str
    isWeak: Optional[bool] = False
    partialKey: Optional[List[str]] = None
    attributes: List[Attribute]

    @field_validator("partialKey")
    def validate_partial_key(cls, v, info):
        if info.data.get("isWeak") and not v:
            raise ValueError("Weak entities must have a partial key")
        if not info.data.get("isWeak") and v:
            raise ValueError("Only weak entities can have a partial key")
        return v


class ParticipantEntity(BaseModel):
    entityName: str
    cardinality: str
    participation: Literal["total", "partial"]


class Relationship(BaseModel):
    name: str
    isIdentifying: Optional[bool] = False
    participantEntities: List[ParticipantEntity]
    attributes: List[Attribute] = Field(default_factory=list)

    @field_validator("participantEntities")
    def validate_identifying_relationship(cls, v, info):
        if info.data.get("isIdentifying"):
            if len(v) < 2:
                raise ValueError("Identifying relationship must connect at least 2 entities")
        return v


class ERSchema(BaseModel):
    entities: List[Entity]
    relationships: List[Relationship]
