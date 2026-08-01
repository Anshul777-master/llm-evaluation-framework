from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from .api.router import router
from .config import get_settings
from .database import Base, SessionLocal, engine
from .models import ModelConfig, User
from .security import hash_password


def seed_database() -> None:
    Path("data").mkdir(exist_ok=True)
    Base.metadata.create_all(bind=engine)
    models = [
        ("gpt-5.6", "GPT-5.6", "OpenAI", "gpt-5.6", True),
        ("claude", "Claude", "Anthropic", "claude-sonnet-4-5", True),
        ("gemini", "Gemini", "Google", "gemini-2.5-flash", True),
        ("deepseek", "DeepSeek", "DeepSeek", "deepseek-chat", True),
        ("mistral", "Mistral", "Mistral", "mistral-small-latest", True),
        ("llama", "Llama 3.3", "Ollama", "llama3.3", True),
    ]
    with SessionLocal() as db:
        if db.scalar(select(ModelConfig.id).limit(1)) is None:
            for slug, display, provider, model_name, live in models:
                db.add(ModelConfig(slug=slug, display_name=display, provider=provider, model_name=model_name, supports_live=live))
        if db.scalar(select(User).where(User.email == "demo@sentinel.local")) is None:
            db.add(User(name="Demo Researcher", email="demo@sentinel.local", password_hash=hash_password("demo12345"), role="admin"))
        db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    seed_database()
    yield


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Human-friendly LLM evaluation APIs for bias, toxicity, accuracy, hallucination risk, fairness, robustness, and safety.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:3000", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix=settings.api_prefix)


@app.get("/")
def root() -> dict[str, str]:
    return {"name": settings.app_name, "status": "ready", "docs": "/docs"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy", "environment": settings.environment}
