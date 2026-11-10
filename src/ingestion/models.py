from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, field_validator


class CPVClassification(BaseModel):
    """CPV code and dictionary description."""
    code: str = Field(..., min_length=8)
    name: str = Field(default="")


class AttachmentMetadata(BaseModel):
    """Metadata representation of procurement attachments (SWZ, OPZ, etc.)."""
    id: UUID = Field(default_factory=uuid4)
    procurement_id: Optional[UUID] = None
    file_name: str = Field(..., min_length=1)
    file_type: str = Field(default="SWZ")
    url: Optional[str] = None
    sha256_hash: Optional[str] = None
    raw_markdown: Optional[str] = None

    @field_validator("file_name")
    @classmethod
    def validate_file_name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("file_name cannot be whitespace only")
        return v.strip()


class TenderNotice(BaseModel):
    """Normalized tender notice representation mapped to procurements table."""
    id: UUID = Field(default_factory=uuid4)
    ocds_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    municipality_name: str = Field(..., min_length=1)
    voivodeship: str = Field(..., min_length=1)
    estimated_budget_pln: Optional[float] = None
    cpv_codes: List[str] = Field(default_factory=list)
    date_published: datetime
    date_deadline: datetime
    status: str = Field(default="ACTIVE")
    attachments: List[AttachmentMetadata] = Field(default_factory=list)

    @field_validator("ocds_id", "title", "municipality_name", "voivodeship")
    @classmethod
    def validate_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty or whitespace only")
        return v.strip()

    def is_deadline_past(self) -> bool:
        """Checks if tender submission deadline has passed."""
        now = datetime.now(timezone.utc)
        deadline = self.date_deadline if self.date_deadline.tzinfo else self.date_deadline.replace(tzinfo=timezone.utc)
        return now > deadline
