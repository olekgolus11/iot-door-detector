from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class ControlStateUpdate(BaseModel):
    collection_enabled: Optional[bool] = None
    active_source_mode: Optional[Literal["mock", "camera"]] = None
    baseline_occupancy: Optional[int] = Field(default=None, ge=0)

