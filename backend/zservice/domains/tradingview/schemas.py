from pydantic import BaseModel, Field


class TvModeRequest(BaseModel):
    mode: int


class TvTokenRequest(BaseModel):
    token: str = Field(max_length=8192)  # a TradingView session JWT is ~1 KB
