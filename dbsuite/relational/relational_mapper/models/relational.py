from pydantic import BaseModel, Field

class ForeignKey(BaseModel):
    columns: list[str]
    referenced_table: str
    referenced_columns: list[str]

class Table(BaseModel):
    name: str
    attributes: list[str]
    primary_key: list[str] = Field(default_factory=list)
    foreign_keys: list[ForeignKey] = Field(default_factory=list)


class RelationalSchema(BaseModel):
    tables: list[Table] = Field(default_factory=list)
