import os

from fastapi.testclient import TestClient

os.environ["BACKEND_MODO"] = "demo"

from app.main import app  # noqa: E402


def test_api_demo():
    with TestClient(app) as client:
        health = client.get("/api/v1/salud")
        latest = client.get("/api/v1/lecturas/ultimas")
        catalog = client.get("/api/v1/sensores")
    assert health.status_code == 200
    assert health.json()["influx"] == "ok"
    assert latest.json()["origen"] == "demo"
    assert len(latest.json()["sensores"]) == 2
    assert catalog.json()["aula"] == "L419"


def test_historial_rechaza_variable():
    with TestClient(app) as client:
        response = client.get("/api/v1/sensores/sensor-co2-01/historial?variable=desconocida")
    assert response.status_code == 404
