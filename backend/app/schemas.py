from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class RegisterRequest(LoginRequest):
    name: str = Field(min_length=2, max_length=120)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    role: str


class ModelOut(BaseModel):
    slug: str
    display_name: str
    provider: str
    model_name: str
    connected: bool
    supports_live: bool


class EvaluationRequest(BaseModel):
    name: str = Field(default="Responsible AI baseline", min_length=2, max_length=200)
    model_slugs: list[str] = Field(default_factory=lambda: ["gpt-5.6"], min_length=1, max_length=8)
    prompts: list[str] = Field(min_length=1, max_length=500)
    dataset_name: str = Field(default="Custom prompts", max_length=200)
    mode: Literal["demo", "live"] = "demo"
    temperature: float = Field(default=0.2, ge=0, le=2)

    @model_validator(mode="after")
    def prompts_must_contain_text(self):
        if not all(prompt.strip() for prompt in self.prompts):
            raise ValueError("Prompts cannot be blank")
        return self


class DimensionScores(BaseModel):
    bias: float
    toxicity: float
    accuracy: float
    hallucination: float
    fairness: float
    robustness: float
    safety: float


class PromptResult(BaseModel):
    prompt: str
    response: str
    execution_time_ms: int
    token_usage: int
    estimated_cost_usd: float
    scores: DimensionScores
    flags: list[dict[str, Any]]
    evidence: list[str]


class EvaluationOut(BaseModel):
    id: int
    name: str
    model_slug: str
    dataset_name: str
    status: str
    mode: str
    prompt_count: int
    trust_score: float
    grade: str
    risk_level: str
    scores: DimensionScores
    results: list[PromptResult]
    recommendation: str
    created_at: datetime


class ComparisonRequest(BaseModel):
    evaluation_ids: list[int] = Field(min_length=2, max_length=10)


class DatasetUploadOut(BaseModel):
    id: int
    name: str
    filename: str
    prompt_count: int
    columns: list[str]
    preview: list[dict[str, Any]]
