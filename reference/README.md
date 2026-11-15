# Referencia del proyecto

Material de consulta que no se ejecuta como parte de la aplicación web. El
código ejecutable está en `backend/`, `web/`, `infra/` y `firmware/`.

## Contenido

| Ruta | Descripción |
|---|---|
| `docs/informe_gemelo_digital.tex` | Informe técnico del proyecto de adquisición. |
| `docs/README_gemelo_digital_L418.md` | Documentación original del repositorio de adquisición. |
| `grafana/dashboard_gemelo_L418_final.json` | Dashboard de Grafana exportado para importar manualmente. |

> El stack de producción ya incluye su propio dashboard provisionado en
> `infra/prod/grafana/dashboards/`. El JSON de `reference/grafana/` sirve como
> respaldo o para importarlo en una instalación de Grafana existente.

## Flujo de datos

```text
Nodos ESP32 → ESP-NOW → Gateway ESP32 → MQTT → Telegraf → InfluxDB
                                                              ↓
                                                    Backend FastAPI
                                                              ↓
                                                    Frontend web
```

- El **firmware** de los ESP32 está en `firmware/`.
- El **stack de adquisición** (Mosquitto, Telegraf, InfluxDB, Grafana) está en
  `infra/`.
- El **backend** solo consulta InfluxDB; no publica en MQTT ni habla
  directamente con los ESP32.

El historial Git del repositorio de adquisición no se conserva aquí: su
contenido se incorporó al repositorio Web-PI3. Si necesitas el historial
original, consulta el repositorio de origen en GitHub.
