from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field


class PlaceIn(BaseModel):
    external_id: int


class PlaceUpdate(BaseModel):
    notes: str | None = None
    visited: bool | None = None


class PlaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: int
    title: str
    notes: str | None
    visited: bool
    created_at: datetime


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    start_date: date | None = None
    places: list[PlaceIn] = Field(default_factory=list, max_length=10)


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    start_date: date | None = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    start_date: date | None
    created_at: datetime
    places: list[PlaceOut]

    @computed_field
    @property
    def completed(self) -> bool:
        return len(self.places) > 0 and all(p.visited for p in self.places)


class ProjectList(BaseModel):
    items: list[ProjectOut]
    total: int
    limit: int
    offset: int
