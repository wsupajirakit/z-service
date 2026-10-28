"""Request bodies for the settings routes (field names are part of the public API)."""

from pydantic import BaseModel, Field


class TimezoneRequest(BaseModel):
    offset_minutes: int
    label: str = Field(max_length=40)  # shown in Telegram texts (HTML-escaped there)


class DestinationsRequest(BaseModel):
    dest_stock_drive: bool | None = None
    dest_stock_telegram: bool | None = None
    dest_gold_drive: bool | None = None
    dest_gold_telegram: bool | None = None


class AutoSkipMinutesRequest(BaseModel):
    minutes: int
