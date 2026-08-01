import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import Dataset, Evaluation, ModelConfig, Report, User
from ..schemas import (
    ComparisonRequest,
    DatasetUploadOut,
    DimensionScores,
    EvaluationOut,
    EvaluationRequest,
    LoginRequest,
    ModelOut,
    PromptResult,
    RegisterRequest,
    Token,
    UserOut,
)
from ..security import create_access_token, get_current_user, get_optional_user, hash_password, verify_password
from ..services.evaluation_engine import (
    aggregate_scores,
    evaluate_response,
    grade_for,
    recommendation_for,
    risk_for,
    token_estimate,
    trust_score,
)
from ..services.providers import ProviderError, provider_for
from ..services.reporting import generate_report


router = APIRouter()


def evaluation_out(evaluation: Evaluation) -> EvaluationOut:
    return EvaluationOut(
        id=evaluation.id,
        name=evaluation.name,
        model_slug=evaluation.model_slug,
        dataset_name=evaluation.dataset_name,
        status=evaluation.status,
        mode=evaluation.mode,
        prompt_count=evaluation.prompt_count,
        trust_score=evaluation.trust_score,
        grade=evaluation.grade,
        risk_level=evaluation.risk_level,
        scores=DimensionScores(**json.loads(evaluation.scores_json)),
        results=[PromptResult(**row) for row in json.loads(evaluation.results_json)],
        recommendation=evaluation.recommendation,
        created_at=evaluation.created_at,
    )


@router.post("/auth/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> Token:
    if db.scalar(select(User).where(User.email == payload.email.lower())):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(name=payload.name.strip(), email=payload.email.lower(), password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return Token(access_token=create_access_token(user))


@router.post("/auth/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> Token:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    return Token(access_token=create_access_token(user))


@router.get("/auth/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.get("/models", response_model=list[ModelOut])
def list_models(db: Session = Depends(get_db)) -> list[ModelOut]:
    settings = get_settings()
    connected = {
        "openai": bool(settings.openai_api_key),
        "anthropic": bool(settings.anthropic_api_key),
        "google": bool(settings.gemini_api_key),
        "deepseek": bool(settings.deepseek_api_key),
        "mistral": bool(settings.mistral_api_key),
        "ollama": True,
    }
    rows = db.scalars(select(ModelConfig).where(ModelConfig.enabled.is_(True)).order_by(ModelConfig.id)).all()
    return [ModelOut(slug=row.slug, display_name=row.display_name, provider=row.provider, model_name=row.model_name, connected=connected.get(row.provider.lower(), False), supports_live=row.supports_live) for row in rows]


@router.post("/evaluate", response_model=list[EvaluationOut], status_code=status.HTTP_201_CREATED)
def evaluate(
    payload: EvaluationRequest,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
) -> list[EvaluationOut]:
    outputs: list[EvaluationOut] = []
    for slug in payload.model_slugs:
        try:
            provider, provider_model = provider_for(slug, payload.mode)
        except ProviderError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        prompt_results: list[dict[str, Any]] = []
        for prompt in payload.prompts:
            try:
                generated = provider.generate(prompt, provider_model, payload.temperature)
            except Exception as exc:
                raise HTTPException(status_code=502, detail=f"{slug} request failed: {exc}") from exc
            analysis = evaluate_response(prompt, generated.text)
            prompt_results.append(
                {
                    "prompt": prompt,
                    "response": generated.text,
                    "execution_time_ms": generated.execution_time_ms,
                    "token_usage": generated.input_tokens + generated.output_tokens or token_estimate(prompt + generated.text),
                    "estimated_cost_usd": generated.estimated_cost_usd,
                    "scores": analysis["scores"],
                    "flags": analysis["flags"],
                    "evidence": analysis["evidence"],
                }
            )

        scores = aggregate_scores([row["scores"] for row in prompt_results])
        total = trust_score(scores)
        evaluation = Evaluation(
            owner_id=user.id if user else None,
            name=payload.name,
            model_slug=slug,
            dataset_name=payload.dataset_name,
            status="completed",
            mode=payload.mode,
            prompt_count=len(payload.prompts),
            trust_score=total,
            grade=grade_for(total),
            risk_level=risk_for(total),
            scores_json=json.dumps(scores),
            results_json=json.dumps(prompt_results),
            recommendation=recommendation_for(total, scores),
            completed_at=datetime.now(timezone.utc),
        )
        db.add(evaluation)
        db.commit()
        db.refresh(evaluation)
        outputs.append(evaluation_out(evaluation))
    return outputs


@router.get("/evaluations", response_model=list[EvaluationOut])
def list_evaluations(
    limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[EvaluationOut]:
    rows = db.scalars(select(Evaluation).order_by(Evaluation.created_at.desc()).limit(limit)).all()
    return [evaluation_out(row) for row in rows]


@router.get("/evaluation/{evaluation_id}", response_model=EvaluationOut)
def get_evaluation(evaluation_id: int, db: Session = Depends(get_db)) -> EvaluationOut:
    evaluation = db.get(Evaluation, evaluation_id)
    if evaluation is None:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return evaluation_out(evaluation)


@router.post("/compare")
def compare(payload: ComparisonRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    rows = db.scalars(select(Evaluation).where(Evaluation.id.in_(payload.evaluation_ids))).all()
    if len(rows) != len(set(payload.evaluation_ids)):
        raise HTTPException(status_code=404, detail="One or more evaluations were not found")
    ranked = sorted(rows, key=lambda row: row.trust_score, reverse=True)
    return {
        "winner": ranked[0].model_slug,
        "score_gap": round(ranked[0].trust_score - ranked[-1].trust_score, 2),
        "evaluations": [evaluation_out(row).model_dump(mode="json") for row in ranked],
    }


@router.get("/leaderboard")
def leaderboard(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.execute(
        select(Evaluation.model_slug, func.avg(Evaluation.trust_score), func.count(Evaluation.id))
        .group_by(Evaluation.model_slug)
        .order_by(func.avg(Evaluation.trust_score).desc())
    ).all()
    return [{"rank": index + 1, "model": row[0], "average_trust_score": round(row[1], 2), "evaluation_count": row[2]} for index, row in enumerate(rows)]


@router.post("/upload-dataset", response_model=DatasetUploadOut, status_code=status.HTTP_201_CREATED)
async def upload_dataset(file: UploadFile = File(...), db: Session = Depends(get_db)) -> DatasetUploadOut:
    filename = Path(file.filename or "dataset").name
    suffix = Path(filename).suffix.lower()
    if suffix not in {".csv", ".json", ".xlsx"}:
        raise HTTPException(status_code=400, detail="Upload a CSV, JSON, or XLSX file")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Dataset must be smaller than 10 MB")
    try:
        if suffix == ".csv":
            frame = pd.read_csv(io.BytesIO(content))
        elif suffix == ".json":
            frame = pd.read_json(io.BytesIO(content))
        else:
            frame = pd.read_excel(io.BytesIO(content))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read dataset: {exc}") from exc
    if frame.empty:
        raise HTTPException(status_code=400, detail="The dataset is empty")
    if len(frame) > 100_000:
        raise HTTPException(status_code=400, detail="Keep uploads below 100,000 rows for this starter")
    preview = json.loads(frame.head(5).fillna("").to_json(orient="records"))
    dataset = Dataset(name=Path(filename).stem, filename=filename, prompt_count=len(frame), columns_json=json.dumps(list(frame.columns)), preview_json=json.dumps(preview))
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return DatasetUploadOut(id=dataset.id, name=dataset.name, filename=filename, prompt_count=dataset.prompt_count, columns=list(frame.columns), preview=preview)


@router.get("/datasets")
def list_datasets(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.scalars(select(Dataset).order_by(Dataset.created_at.desc())).all()
    return [{"id": row.id, "name": row.name, "filename": row.filename, "prompt_count": row.prompt_count, "columns": json.loads(row.columns_json), "created_at": row.created_at} for row in rows]


@router.get("/reports")
def list_reports(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.scalars(select(Evaluation).order_by(Evaluation.created_at.desc()).limit(50)).all()
    return [{"evaluation_id": row.id, "name": row.name, "model": row.model_slug, "trust_score": row.trust_score, "formats": ["pdf", "xlsx", "csv", "html"], "created_at": row.created_at} for row in rows]


@router.post("/generate-report/{evaluation_id}")
@router.get("/reports/{evaluation_id}")
def report(
    evaluation_id: int,
    format: str = Query(default="pdf", pattern="^(pdf|xlsx|csv|html)$"),
    db: Session = Depends(get_db),
) -> Response:
    evaluation = db.get(Evaluation, evaluation_id)
    if evaluation is None:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    data, media_type, filename = generate_report(evaluation, format)
    db.add(Report(evaluation_id=evaluation.id, format=format, filename=filename))
    db.commit()
    return Response(content=data, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})
