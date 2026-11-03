from app.estados import estado_anomalias_nodo, estado_nivel_nodo


def test_estados_co2():
    for nivel, esperado in [("NORMAL", "normal"), ("ALERTA", "alerta"), ("CRITICO", "critico"), ("CALENTANDO", "calentando")]:
        assert estado_nivel_nodo({"nivel": nivel, "co2_ppm": 600}, 1, 30) == esperado


def test_fallos_y_caducidad_co2():
    assert estado_nivel_nodo({"co2_ppm": -1, "nivel": "NORMAL"}, 1, 30) == "falla"
    assert estado_nivel_nodo({"co2_ppm": -2, "nivel": "NORMAL"}, 1, 30) == "falla"
    assert estado_nivel_nodo({"nivel": "NORMAL"}, 31, 30) == "sin_datos"
    assert estado_nivel_nodo({"co2_ppm": 600.0, "nivel": "NORMAL", "anomalias": "FALLO_SENSOR"}, 1, 30) == "falla"


def test_estados_audio():
    assert estado_anomalias_nodo({"calibrando": 1}, 1, 10) == "calibrando"
    assert estado_anomalias_nodo({"anomalias": "RUIDO_IMPACTO"}, 1, 10) == "alerta"
    assert estado_anomalias_nodo({"anomalias": "NINGUNA"}, 1, 10) == "normal"
    assert estado_anomalias_nodo({"anomalias": "FALLO_AUDIO"}, 1, 10) == "falla"

