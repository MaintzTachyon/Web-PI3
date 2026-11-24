# Infraestructura de adquisición IoT

Esta carpeta contiene la cadena que recibe los datos de los ESP32 y los deja
disponibles en InfluxDB. El backend FastAPI **no** forma parte de este stack:
solo consulta el bucket una vez que los datos están almacenados.

```text
Nodos ESP32 → ESP-NOW → Gateway ESP32 → MQTT → Telegraf → InfluxDB → Grafana
                                                                 ↓
                                                       Backend FastAPI
                                                                 ↓
                                                          Frontend web
```

## `local/` frente a `prod/`

| Carpeta | Uso | Puertos | Seguridad |
|---|---|---|---|
| `local/` | Pruebas en una laptop o servidor de desarrollo | MQTT `1883`, InfluxDB `8086`, Grafana `3000` | Sin TLS; Grafana con login |
| `prod/` | Exposición en una VM (AWS Academy, Azure, etc.) | MQTT TLS `8883`, HTTP/HTTPS `80/443` | Caddy con HTTPS, Mosquitto con TLS y usuarios, InfluxDB solo en `127.0.0.1` |

## Stack local

```bash
cd infra/local
cp .env.example .env
# editar .env con contraseñas propias
docker compose up -d
```

Servicios:

- **Mosquitto** en `localhost:1883`. El gateway publica en
  `utec/gemelo/<grupo>/<nodo>/<tipo>`.
- **Telegraf** se suscribe a los seis tipos (`co2`, `audio`, `luz`,
  `termico`, `magnetico`, `ambiente`) y escribe en InfluxDB.
- **InfluxDB** en <http://localhost:8086>, organización `utec`, bucket `gemelo`.
- **Grafana** en <http://localhost:3000>.

Variables requeridas en `local/.env`:

- `INFLUX_PASSWORD`
- `INFLUX_TOKEN`
- `GRAFANA_PASSWORD`

Para el backend se recomienda crear un token de **solo lectura** del bucket
`gemelo` y usarlo en `backend/.env` con `BACKEND_MODO=real`.

## Stack de producción

```bash
cd infra/prod
cp .env.example .env
# editar .env con dominio, correo y contraseñas
bash preparar.sh
docker compose up -d
```

`preparar.sh` hace tres cosas:

1. Genera una CA propia y el certificado TLS del broker en `ca/` y
   `mosquitto/certs/` (no se versionan).
2. Crea los usuarios MQTT `telegraf` y `grupo1` en
   `mosquitto/config/passwd`.
3. Ajusta permisos para el usuario de Mosquitto.

Variables requeridas en `prod/.env`:

- `DOMINIO`
- `ACME_EMAIL`
- `INFLUX_PASSWORD`
- `INFLUX_TOKEN`
- `GRAFANA_ADMIN_PASSWORD`
- `MQTT_TELEGRAF_PASS`
- `MQTT_GRUPO1_PASS`

El certificado `ca/ca.crt` se copia al firmware del gateway
(`firmware/gateway_nube/`) para que acepte el broker con TLS. Ese archivo y el
`.env` están excluidos por `.gitignore`.

## Relación con el backend

El backend se configura con las mismas credenciales de lectura:

```env
BACKEND_MODO=real
INFLUX_URL=http://localhost:8086
INFLUX_TOKEN_LECTURA=<token de solo lectura>
INFLUX_ORG=utec
INFLUX_BUCKET=gemelo
GRUPO=grupo1
```

El grupo debe coincidir con el valor `GRUPO` del gateway y con el usuario MQTT
creado en producción (`grupo1` por defecto).
