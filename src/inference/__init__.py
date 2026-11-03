"""Inference module for local LLM generation via Ollama with strict grounding."""

from src.inference.models import CompetitorItem, RedFlagItem, TenderReport
from src.inference.ollama_client import OllamaClient
from src.inference.prompts import (
    STRICT_GROUNDING_SYSTEM_PROMPT,
    build_competitor_matrix_prompt,
    build_grounded_prompt,
    build_historical_risk_prompt,
    build_kio_appeal_prompt,
    build_vendor_lockin_prompt,
)
from src.inference.report_generator import TenderReportGenerator

__all__ = [
    "OllamaClient",
    "TenderReportGenerator",
    "TenderReport",
    "RedFlagItem",
    "CompetitorItem",
    "STRICT_GROUNDING_SYSTEM_PROMPT",
    "build_grounded_prompt",
    "build_vendor_lockin_prompt",
    "build_kio_appeal_prompt",
    "build_competitor_matrix_prompt",
    "build_historical_risk_prompt",
]
