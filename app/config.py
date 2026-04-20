from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class PropertyMapping(BaseModel):
    date: str
    description: str | None = None


class CalendarConfig(BaseModel):
    token: str = Field(min_length=8)
    name: str
    database_id: str
    properties: PropertyMapping


class AppConfig(BaseModel):
    calendars: list[CalendarConfig]

    def by_token(self, token: str) -> CalendarConfig | None:
        for cal in self.calendars:
            if cal.token == token:
                return cal
        return None


def load_config(path: str | Path = "config.yaml") -> AppConfig:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return AppConfig.model_validate(raw)
