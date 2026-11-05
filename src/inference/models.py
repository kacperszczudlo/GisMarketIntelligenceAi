from typing import List, Optional
from pydantic import BaseModel, Field


class RedFlagItem(BaseModel):
    """Identified legal or technical barrier in tender documentation."""
    title: str
    severity: str = Field(default="WYSOKIE")  # WYSOKIE, ŚREDNIE, NISKIE
    location: str
    citation: str
    legal_basis: str
    recommended_action: str


class CompetitorItem(BaseModel):
    """Competitor profiling item."""
    name: str
    probability: str  # Wysokie, Średnie, Niskie
    strengths: str
    weaknesses: str


class TenderReport(BaseModel):
    """Structured tender intelligence report model."""
    procurement_id: str
    title: str
    municipality: str
    executive_summary: str
    red_flags: List[RedFlagItem] = Field(default_factory=list)
    competitor_matrix: List[CompetitorItem] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)
    raw_llm_output: str = ""
    markdown_report: str = ""
