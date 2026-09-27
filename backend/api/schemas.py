"""Pydantic request/response models - the API contract.

Person 1 (Lead Developer + DevOps) owns this file.
Person 2 (Frontend Developer) consumes it; changes here are breaking changes.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

TriageLevel = Literal["RED", "YELLOW", "GREEN"]
Language = Literal["en", "sw"]


class PatientContext(BaseModel):
    """Optional clinical context that changes triage risk."""

    hiv_status: str | None = Field(default=None, examples=["negative", "positive", "unknown"])
    pregnant: bool = False
    chronic_conditions: list[str] = Field(default_factory=list, examples=[["hypertension", "diabetes"]])
    location: str | None = Field(default=None, examples=["Kisumu"])
    sex: str | None = Field(default=None, examples=["female"])


class TriageRequest(BaseModel):
    """Request body for every triage endpoint."""

    symptoms: str = Field(min_length=3, max_length=2000, examples=["I have fever, headache and body aches for 2 days"])
    patient_age: int | None = Field(default=None, ge=0, le=120, examples=[25])
    patient_context: PatientContext = Field(default_factory=PatientContext)
    language: Language = "en"
    sex: str | None = None

    @field_validator("symptoms")
    @classmethod
    def symptoms_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("symptoms must not be blank")
        return value.strip()


class AnalyzeSymptomsRequest(TriageRequest):
    """`/api/analyze-symptoms` - Agent 1 only."""


class TriageDecisionRequest(BaseModel):
    """`/api/triage-decision` - takes an existing feature profile."""

    symptom_profile: dict[str, Any] = Field(
        ...,
        description="Canonical feature profile, as returned by /api/analyze-symptoms.",
    )


class CarePathwayRequest(BaseModel):
    """`/api/care-pathway` - Agent 3 only."""

    triage_level: TriageLevel
    symptom_profile: dict[str, Any] = Field(default_factory=dict)
    triage_result: dict[str, Any] | None = None
    language: Language = "en"


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    llm: dict[str, Any]
    knowledge_base: dict[str, Any]
    checks: dict[str, bool]
