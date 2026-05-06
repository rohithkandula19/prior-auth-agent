from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

CriterionType = Literal["required", "contraindication", "documentation"]


class Criterion(BaseModel):
    id: str = Field(..., description="Stable identifier such as C001, C002")
    text: str = Field(..., description="Verbatim criterion text from the policy")
    type: CriterionType
    parent_id: str | None = None
    page_number: int = Field(..., ge=1)
    char_span: tuple[int, int] = Field(..., description="(start, end) offsets in raw_text")


class Policy(BaseModel):
    id: str
    payer: str
    procedure_code: str = Field(..., description="CPT or HCPCS code")
    procedure_name: str
    effective_date: date
    source_url: str
    raw_text: str
    criteria: list[Criterion]
    embedding_index_path: str | None = None
