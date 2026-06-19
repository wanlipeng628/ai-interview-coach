from fastapi.testclient import TestClient

from app.main import app


def test_health_check() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_start_interview() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/interview/start",
        json={"job_role": "Java开发工程师"},
    )

    body = response.json()
    assert response.status_code == 201
    assert body["session_id"]
    assert "Java开发工程师" in body["first_question"]
