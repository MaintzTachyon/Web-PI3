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


def test_sirve_frontend_y_historial_demo():
    with TestClient(app) as client:
        page = client.get("/")
        script = client.get("/js/datos.js")
        history = client.get("/api/v1/sensores/sensor-audio-01/historial?variable=leq_db&rango=15m")
    assert page.status_code == 200 and "Aula L419" in page.text
    assert script.status_code == 200
    assert len(history.json()["puntos"]) > 1


def test_historial_rechaza_variable():
    with TestClient(app) as client:
        response = client.get("/api/v1/sensores/sensor-co2-01/historial?variable=desconocida")
    assert response.status_code == 404
