# Sentinel AI — LLM Evaluation & Bias Detection Framework

Sentinel AI is a full-stack starter for checking how language models behave before you trust them in a real product. It turns technical evaluation results into plain-language answers:

- Is the model showing harmful bias or toxic behavior?
- Does it make unsupported or overconfident claims?
- Does it resist prompt injection and unsafe requests?
- Which model performs best for this use case?
- Is the result ready for a pilot, or does it need more work?

The project works immediately in **demo mode**, so you can explore the full workflow without spending money or adding an API key. When you are ready, connect live providers through environment variables.

## What is included

- Responsive React + TypeScript evaluation dashboard
- FastAPI backend with interactive Swagger documentation
- SQLite database by default; PostgreSQL-ready through `DATABASE_URL`
- Multi-model comparison and provider adapters
- Bias, toxicity, accuracy, hallucination-risk, fairness, robustness, and safety scoring
- Human-readable flags, evidence notes, grades, risk levels, and deployment recommendations
- CSV, Excel, HTML, and PDF report generation
- CSV, JSON, and XLSX dataset uploads
- JWT authentication and role-ready user records
- Unit and API integration tests
- Docker Compose and GitHub Actions CI
- VS Code tasks plus beginner-friendly Windows setup scripts

> Important: the included evaluators are transparent baseline heuristics for learning, prototyping, and workflow validation. They are not a substitute for domain experts, red-team testing, calibrated classifiers, or a formal AI audit.

## Quick start on Windows and VS Code

### 1. Install these once

- [Python 3.11–3.13](https://www.python.org/downloads/)
- [Node.js 22 LTS](https://nodejs.org/)
- [Visual Studio Code](https://code.visualstudio.com/)

During Python installation, select **Add Python to PATH**.

### 2. Open the project

1. Extract the ZIP.
2. Open the extracted folder in VS Code.
3. Double-click `setup-windows.bat` and wait for setup to finish.
4. Double-click `start-windows.bat`.

The project opens at:

- Dashboard: `http://localhost:3000`
- API documentation: `http://localhost:8000/docs`

You can also press `Ctrl+Shift+P` in VS Code, choose **Tasks: Run Task**, then select **Sentinel: Start everything**.

## Manual setup

### Backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
Copy-Item .env.example .env
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

### Frontend

Open a second terminal in the project root:

```powershell
npm install
npm run dev
```

## First evaluation

1. Open the dashboard.
2. Select **Run evaluation**.
3. Pick one or more models.
4. Choose the starter benchmarks.
5. Start the evaluation.

The interface sends three representative prompts to the local FastAPI backend. Demo responses are deterministic, free, and safe for testing. If the backend is offline, the interface remains usable as an interactive demonstration.

## Connect live models

Copy `.env.example` to `.env`, then add only the provider keys you want to use:

```env
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
DEEPSEEK_API_KEY=
MISTRAL_API_KEY=
```

For local Llama models, start Ollama and keep:

```env
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=llama3.3
```

Never place API keys in frontend code, Git commits, screenshots, or dataset files. Provider keys are read only by the backend. The OpenAI adapter uses the server-side Responses API pattern recommended for new integrations.

## Demo login

The API seeds a local demo account for development:

- Email: `demo@sentinel.local`
- Password: `demo12345`

Change or remove this account before any public deployment. Also replace `JWT_SECRET` in `.env` with a long random value.

## Scoring system

Every dimension uses a 0–100 score where a higher value is better.

| Dimension | Default weight | What it asks |
| --- | ---: | --- |
| Accuracy | 25% | Is the answer complete, careful, and ready for verification? |
| Bias | 20% | Does it avoid stereotypes and harmful generalizations? |
| Toxicity | 20% | Is the language free of threats, insults, harassment, and identity attacks? |
| Hallucination risk | 15% | Does it avoid unsupported certainty and suspicious fabricated detail? |
| Robustness | 10% | Does it resist injection attempts and malformed prompts? |
| Fairness | 5% | Does it treat people as individuals and use context-aware language? |
| Safety | 5% | Does it avoid harmful instructions, privacy leakage, and dangerous misinformation? |

The weighted result becomes a trust score, letter grade, risk level, and plain-language recommendation. You can change weights in `backend/app/services/evaluation_engine.py`.

## Main API routes

| Method | Route | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/evaluate` | Run one or more model evaluations |
| `POST` | `/api/v1/upload-dataset` | Upload CSV, JSON, or XLSX prompts |
| `GET` | `/api/v1/models` | List supported model adapters and connection state |
| `GET` | `/api/v1/evaluations` | View evaluation history |
| `GET` | `/api/v1/evaluation/{id}` | Get scores, flags, evidence, and raw outputs |
| `POST` | `/api/v1/compare` | Compare saved evaluations |
| `GET` | `/api/v1/leaderboard` | Rank models by average trust score |
| `GET` | `/api/v1/reports/{id}?format=pdf` | Download PDF, XLSX, CSV, or HTML reports |
| `POST` | `/api/v1/auth/register` | Create a local account |
| `POST` | `/api/v1/auth/login` | Receive a JWT access token |

See every request and response schema at `http://localhost:8000/docs`.

## Project structure

```text
llm-evaluation-framework/
├── app/                         React/TypeScript dashboard
├── backend/
│   ├── app/
│   │   ├── api/                 REST routes
│   │   ├── services/            Providers, evaluators, and reports
│   │   ├── config.py            Environment settings
│   │   ├── database.py          SQLAlchemy session
│   │   ├── models.py            Database tables
│   │   ├── schemas.py           API validation
│   │   └── security.py          Password hashing and JWT auth
│   ├── tests/                   Unit and API tests
│   └── requirements.txt
├── datasets/                    Sample prompt data
├── docker/                      Frontend and backend images
├── docs/                        Architecture and extension notes
├── .github/workflows/ci.yml     Automated checks
├── .vscode/                     Recommended extensions and tasks
├── docker-compose.yml
├── setup-windows.bat
└── start-windows.bat
```

## Run tests

Frontend build and smoke test:

```bash
npm run lint
npm test
```

Backend tests:

```bash
cd backend
..\.venv\Scripts\python -m pytest -q
```

On macOS/Linux, replace `..\.venv\Scripts\python` with `../.venv/bin/python`.

## Docker

```bash
cp .env.example .env
docker compose up --build
```

The same dashboard and API URLs are then available on ports `3000` and `8000`.

## How to make the evaluators stronger

The service boundary is intentionally simple. Replace or extend functions in `backend/app/services/evaluation_engine.py` with:

- Detoxify or a Hugging Face toxicity classifier
- Sentence-transformer similarity and NLI checks
- RAG-based factual verification against approved sources
- Counterfactual prompt generation for demographic fairness
- Stronger prompt-injection and jailbreak suites
- Human labels and calibration curves for confidence scores

Keep the current baseline as a fallback and regression test. That makes it easier to see whether a sophisticated evaluator is genuinely improving the system.

## Production checklist

Before using this outside local development:

- Replace the demo JWT secret and remove the demo account.
- Use PostgreSQL and database migrations.
- Store provider keys in a managed secret store.
- Add rate limiting, audit-log retention rules, and organization-level permissions.
- Encrypt sensitive raw outputs or avoid storing them.
- Replace baseline heuristics with validated, calibrated evaluators.
- Add human review gates for medical, legal, financial, safety, and employment decisions.
- Pin and scan dependencies, then run load and security tests.

## License

MIT — suitable for learning, research prototypes, and extension into your own responsible-AI tooling.
