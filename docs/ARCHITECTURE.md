# Architecture

## Request flow

1. The React dashboard collects models, prompts, datasets, and evaluation settings.
2. `POST /api/v1/evaluate` validates the request and resolves a provider adapter.
3. The provider returns text, latency, and token counts.
4. The evaluation engine computes seven explainable baseline dimensions.
5. Aggregated scores become a trust score, grade, risk level, and recommendation.
6. SQLAlchemy stores the summary and raw evidence in SQLite or PostgreSQL.
7. Reporting services generate PDF, XLSX, CSV, or HTML on demand.

## Why demo mode exists

Demo mode removes three common blockers: missing API keys, provider cost, and non-deterministic tests. It uses stable, prompt-aware responses so the complete workflow remains testable. Live provider logic uses the same scoring and persistence path.

## Trust boundaries

- Provider API keys stay in backend environment variables.
- Uploaded datasets are parsed in memory and only a small preview is stored by this starter.
- JWT protects account-aware endpoints; production deployments should add organization scoping and refresh-token rotation.
- Raw model responses may contain sensitive information. Add redaction and retention policies before production use.

## Extension points

- Add providers in `services/providers.py` and seed their metadata in `main.py`.
- Add evaluators in `services/evaluation_engine.py`.
- Change weights through `DEFAULT_WEIGHTS` or move them into a database-backed policy table.
- Add background jobs with Celery, Dramatiq, or a managed task queue for large batches.
- Move JSON response fields into normalized tables when individual prompt-level analytics become large.
