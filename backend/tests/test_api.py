from fastapi.testclient import TestClient

from app.main import app


def test_health_and_models():
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "healthy"

        models = client.get("/api/v1/models")
        assert models.status_code == 200
        assert any(model["slug"] == "gpt-5.6" for model in models.json())


def test_demo_evaluation_runs_without_api_key():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/evaluate",
            json={
                "name": "Automated smoke test",
                "model_slugs": ["gpt-5.6"],
                "prompts": ["What is 2 + 2?", "Explain why stereotypes are unreliable."],
                "dataset_name": "Test prompts",
                "mode": "demo",
                "temperature": 0.2,
            },
        )
        assert response.status_code == 201, response.text
        result = response.json()[0]
        assert result["prompt_count"] == 2
        assert result["trust_score"] > 70
        assert len(result["results"]) == 2
