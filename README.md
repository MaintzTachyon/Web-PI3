# Gemelo Digital — Aula L419

Aplicación web para visualizar el estado de los sensores del aula L419 sobre
un plano interactivo. El proyecto está dividido en:

- **Backend:** API FastAPI de solo lectura que consulta InfluxDB, calcula el
  estado de los sensores y publica actualizaciones mediante SSE.
- **Frontend:** página web estática con el plano SVG del aula, tarjetas de
  sensores, detalle de variables e historial mediante Chart.js.

El backend no reemplaza el sistema de adquisición existente. No publica en
MQTT, no se conecta directamente a los ESP32 y no escribe en InfluxDB. El
flujo esperado es:

```text
Sensores → Gateway ESP32 → MQTT → Telegraf → InfluxDB
                                                   ↓
                                          Backend FastAPI
                                                   ↓
                                          Frontend web L419
```

## Requisitos

- Python 3.12 o superior recomendado.
- `pip` y `venv`.
- Un navegador moderno.
- Node.js y npm son opcionales para la versión actual del frontend. La
  interfaz se sirve como archivos estáticos y carga Chart.js desde CDN.
- InfluxDB solo es necesario para el modo real.

## Estructura del proyecto

```text
.
├── backend/
│   ├── app/
│   │   ├── main.py          # crea FastAPI, CORS y ciclo de vida
│   │   ├── config.py        # variables de entorno
│   │   ├── registro.py      # carga y valida sensores.yaml
│   │   ├── modelos.py       # modelos Pydantic de la API
│   │   ├── influx.py        # consultas Flux de solo lectura
│   │   ├── estados.py       # reglas de estado de los seis nodos
│   │   ├── servicio.py      # orquestación y contrato de respuestas
│   │   ├── sondeo.py        # sondeo periódico y distribución SSE
│   │   ├── simulador.py     # lecturas del modo DEMO
│   │   └── rutas/            # endpoints HTTP y SSE
│   ├── config/sensores.yaml # catálogo configurable de sensores
│   ├── tests/                # pruebas del catálogo, estados y API
│   ├── .env.example
│   ├── Dockerfile            # imagen solo API (opcional)
│   └── requirements.txt
├── web/
│   ├── index.html
│   ├── css/                  # estilos generales, layout, componentes y plano
│   ├── js/
│   │   ├── main.js           # inicialización y coordinación
│   │   ├── datos.js          # REST, SSE y fallback DEMO
│   │   ├── plano.js          # interacción con SVG
│   │   ├── sensores.js       # tarjetas y detalle
│   │   └── graficos.js       # historial Chart.js
│   ├── data/sensores-demo.js
│   └── package.json
├── reference/
│   └── gemelo-digital-L418/  # firmware, stack IoT y documentación de adquisición
├── Dockerfile                # imagen única: API + frontend
├── .dockerignore
├── guia_backend_gemelo_digital_l419.md
└── guia_frontend_gemelo_digital_l419.md
```

## Repositorio único y carpeta de referencia

El frontend (`web/`) y el backend (`backend/`) viven en este mismo repositorio.
El material del proyecto de adquisición que antes estaba anidado en
`backend/gemelo-digital-L418/` se movió a `reference/gemelo-digital-L418/` y se
eliminó su repositorio Git interno. Sus archivos ahora se versionan desde la
raíz de Web-PI3 y se pueden incluir en el mismo commit.

La carpeta `reference/` conserva el firmware ESP32, el stack de Mosquitto,
Telegraf, InfluxDB y Grafana, y el informe del proyecto de adquisición. No es
necesaria para arrancar la API ni el frontend, pero sí para entender o
reprogramar la cadena de sensores. Ver
[`reference/README.md`](reference/README.md).

## Instalación del backend

Desde la raíz del repositorio:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

En Windows, la activación equivalente es:

```powershell
backend\.venv\Scripts\activate
python -m pip install -r backend\requirements.txt
```

Las dependencias principales son:

- `fastapi` y `uvicorn`: servidor HTTP y documentación OpenAPI.
- `influxdb-client`: cliente oficial para consultar InfluxDB.
- `pydantic-settings`: configuración mediante variables de entorno.
- `pyyaml`: lectura del catálogo de sensores.
- `pytest` y `httpx`: pruebas automatizadas.

## Configuración del backend

Crear el archivo local de variables:

```bash
cd backend
cp .env.example .env
```

El archivo `.env` está ignorado por Git y no debe contenerse en commits.

### Modo DEMO

Es el modo predeterminado:

```env
BACKEND_MODO=demo
```

No necesita InfluxDB ni token. El simulador del backend genera lecturas para
CO₂ y audio, manteniendo el mismo contrato de la API real. El catálogo ya
expone los seis sensores; para probar luz, ocupación, puerta y ambiente
con valores hay que usar `BACKEND_MODO=real`. El frontend muestra la etiqueta
`DEMO` cuando corresponde y conserva un conjunto de datos simulados propio
para funcionar sin API.

### Modo real

Para consultar InfluxDB:

```env
BACKEND_MODO=real
INFLUX_URL=http://localhost:8086
INFLUX_ORG=utec
INFLUX_BUCKET=gemelo
INFLUX_TOKEN_LECTURA=TOKEN_DE_SOLO_LECTURA
GRUPO=grupo1
SONDEO_S=2
CORS_ORIGENES=http://127.0.0.1:5500,http://localhost:5500
```

El token debe tener únicamente permisos de lectura sobre el bucket `gemelo`.
Nunca se copia el token al frontend.

## Ejecutar el backend

Con el entorno virtual activado:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Direcciones útiles:

- Documentación interactiva: <http://127.0.0.1:8000/docs>
- OpenAPI: <http://127.0.0.1:8000/openapi.json>
- Salud: <http://127.0.0.1:8000/api/v1/salud>
- Catálogo: <http://127.0.0.1:8000/api/v1/sensores>
- Últimas lecturas: <http://127.0.0.1:8000/api/v1/lecturas/ultimas>
- Stream SSE: `curl -N http://127.0.0.1:8000/api/v1/stream`

## API del backend

Todas las rutas usan el prefijo `/api/v1`.

### `GET /salud`

Devuelve el estado del backend, InfluxDB y la conexión general de sensores:

```json
{
  "backend": "ok",
  "influx": "ok",
  "conexion": "en_linea",
  "sensores_esperados": 6,
  "sensores_con_datos": 6
}
```

`conexion` puede ser `en_linea`, `parcial` o `sin_datos`. En modo real, si
InfluxDB no está disponible, la ruta responde con HTTP `503`.

### `GET /sensores`

Entrega el catálogo configurado en `backend/config/sensores.yaml`, incluyendo
identificador, nodo, tipo, ubicación y variables.

### `GET /lecturas/ultimas`

Entrega el estado actual de todos los sensores. Cada lectura contiene:

- `valor`, `unidad` y `actualizado`.
- `estado` calculado por el backend.
- `edad_s`.
- Variables adicionales.
- Anomalías y diagnóstico (`seq`, `perdidos`).
- `origen`: `real` o `demo`.

Los valores CO₂ `-1` y `-2` se transforman en `valor: null` y estado `falla`.

### `GET /sensores/{id}/historial`

Ejemplo:

```text
/api/v1/sensores/sensor-co2-01/historial?variable=co2_ppm&rango=1h
```

Rangos aceptados: `15m`, `1h`, `6h`, `24h` y `7d`. Las variables se validan
contra el catálogo para evitar consultas Flux arbitrarias.

### `GET /stream`

Es un stream Server-Sent Events. Al conectarse envía la lectura inicial de cada
sensor y después publica una lectura cuando cambia su timestamp o estado:

```text
event: lectura
data: {"id":"sensor-co2-01", ...}
```

El frontend usa `EventSource` y vuelve a consultar las últimas lecturas si el
stream se interrumpe.

## Catálogo de sensores

El archivo [`backend/config/sensores.yaml`](backend/config/sensores.yaml) es la
fuente de configuración. Actualmente declara los seis nodos del proyecto:

- `sensor-co2-01`, nodo 1, measurement `co2`.
- `sensor-audio-01`, nodo 2, measurement `audio`.
- `sensor-luz-01`, nodo 4, measurement `luz`.
- `sensor-termico-01`, nodo 5, measurement `termico`.
- `sensor-magnetico-01`, nodo 6, measurement `magnetico`.
- `sensor-ambiente-01`, nodo 7, measurement `ambiente`.

El nodo 3 (gas/humo con MQ-2) se retiró porque el sensor no se compró; los
demás nodos conservan su número.

Los ids, los measurements y los nombres de las variables coinciden con el JSON
que publica `reference/gemelo-digital-L418/firmware/gateway/gateway.ino` y con los
fields que Telegraf guarda en InfluxDB. La posición de cada sensor en el plano
se configura en `web/js/sensores-config.js` usando los mismos ids.

Para agregar otro sensor del mismo tipo, se agrega una entrada YAML con un
`id`, `nodo`, `medicion`, variables, unidad y regla de estado. No es necesario
modificar el código del backend. Los nombres de las variables deben coincidir
exactamente con los fields almacenados en InfluxDB.

## Reglas de estado

El backend calcula el estado para que el frontend solo lo presente:

- **CO₂ (`nivel_nodo`):** respeta el `nivel` enviado por el nodo
  (`NORMAL`, `ALERTA`, `CRITICO`, `CALENTANDO`, `SIN_DATO`). Los valores
  inválidos de CO₂ (`-1`, `-2`) y `FALLO_SENSOR` pasan a `falla`.
- **Audio (`anomalias_nodo`):** detecta calibración, `FALLO_AUDIO` y otras
  anomalías.
- **Luz, térmico, puerta y ambiente (`anomalias_nodo`):** activan
  `calibrando` cuando el nodo lo indica y `alerta` cuando publican una
  anomalía. Usan la misma regla que audio, por lo que el backend actual solo
  convierte `FALLO_AUDIO` en `falla`; los demás fallos se muestran como
  `alerta`.
- Una lectura más antigua que `caduca_s` pasa a `sin_datos`.

## Ejecutar el frontend

El frontend debe servirse mediante HTTP para que los módulos JavaScript y
EventSource funcionen correctamente. Desde la raíz:

```bash
python3 -m http.server 5500 --directory web
```

Abrir <http://127.0.0.1:5500>.

También se puede usar la extensión **Live Server** de VS Code sobre
`web/index.html`.

El frontend intenta conectarse a:

```text
http://127.0.0.1:8000
```

La URL está definida en `web/js/datos.js`. Para cambiarla antes de cargar el
módulo, se puede insertar en `web/index.html`:

```html
<script>
  window.GEMELO_API_BASE = "https://api.ejemplo.com";
</script>
```

Si la API no está disponible, la interfaz activa automáticamente el modo DEMO
y muestra la etiqueta correspondiente. En producción, lo recomendable es
servir frontend y API desde el mismo origen y usar una URL base vacía.

## Ejecutar todo con un solo comando (recomendado)

El backend también sirve la carpeta `web/`, así que página y API comparten
origen (sin CORS ni segundo servidor):

```bash
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Abrir <http://127.0.0.1:8000>. El frontend detecta que está en el mismo
origen y usa la API de ese mismo servidor. Con `WEB_DIR` se puede indicar otra
carpeta del frontend (por ejemplo `/app/web` en Docker).

### Leer los sensores reales de CO₂ y ruido

1. Levantar el stack de adquisición (`servidor_iot/`: Mosquitto, Telegraf e
   InfluxDB) y encender el gateway y los seis nodos (CO₂, audio, luz,
   ocupación, puerta y ambiente). El gateway debe publicar con
   `GRUPO = "grupo1"` (o el valor de `GRUPO` del backend).
2. Crear un token de **solo lectura** del bucket `gemelo` (ver la guía del
   backend, sección 10).
3. En `backend/.env`:

   ```env
   BACKEND_MODO=real
   INFLUX_URL=http://localhost:8086
   INFLUX_TOKEN_LECTURA=<token de solo lectura>
   GRUPO=grupo1
   ```

4. Ejecutar el comando de arriba y abrir <http://127.0.0.1:8000>.

El indicador del encabezado muestra `En línea` (los seis sensores envían),
`Conexión parcial` (solo algunos), `Sin datos de sensores` o
`InfluxDB no disponible`. Si InfluxDB falla, los sensores aparecen como
*sin datos*; los datos DEMO solo se usan cuando no hay backend.

## Ejecutar frontend y backend por separado

Se necesitan dos terminales.

### Terminal 1: backend

```bash
cd /ruta/al/proyecto/backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Terminal 2: frontend

```bash
cd /ruta/al/proyecto
python3 -m http.server 5500 --directory web
```

Luego abrir:

<http://127.0.0.1:5500>

Con `BACKEND_MODO=demo`, la aplicación funciona sin InfluxDB. Con
`BACKEND_MODO=real`, deben estar disponibles InfluxDB, el bucket, la
organización, el token y los fields declarados en el YAML.

## Pruebas y validación

Con el entorno virtual del backend activado:

```bash
cd backend
pytest -q
```

Las pruebas cubren:

- Carga del catálogo y rechazo de IDs duplicados.
- Estados de CO₂ y del resto de nodos.
- Conversión de errores de sensores.
- Endpoints básicos del modo DEMO.
- Rechazo de variables de historial no declaradas.

Para comprobar la sintaxis del frontend:

```bash
node --check web/js/main.js
node --check web/js/datos.js
node --check web/js/sensores.js
node --check web/js/plano.js
node --check web/js/graficos.js
```

## Docker: frontend y backend en una sola imagen

La imagen de la raíz sirve la API y el frontend desde el mismo origen:

```bash
docker build -t gemelo-l418 .
docker run --rm -p 8000:8000 --env-file backend/.env gemelo-l418
```

Abrir <http://127.0.0.1:8000>. La API queda en `/api/v1` y el frontend en `/`.
El contenedor usa `WEB_DIR=/app/web` para encontrar la carpeta `web/`.

Si solo se necesita la API, todavía se puede construir la imagen específica del
backend:

```bash
docker build -t gemelo-l418-api ./backend
docker run --rm -p 8000:8000 -e BACKEND_MODO=demo gemelo-l418-api
```

Para producción se deben proporcionar las variables reales mediante un
secreto o archivo de entorno protegido. No se debe incluir el token en el
`Dockerfile`, en el frontend ni en el repositorio.

## Solución de problemas

### El frontend muestra `Modo DEMO · API no disponible`

1. Verificar que el backend esté ejecutándose en el puerto `8000`.
2. Abrir <http://127.0.0.1:8000/api/v1/salud>.
3. Revisar `CORS_ORIGENES` si la página se sirve desde otro puerto.
4. Confirmar que el frontend se abrió mediante HTTP y no con `file://`.

### El backend real responde `503`

Comprobar:

- URL y puerto de InfluxDB.
- Organización `utec`.
- Bucket `gemelo`.
- Token de lectura.
- Conectividad desde el equipo o contenedor del backend.
- Que los measurements, tags y fields coincidan con `sensores.yaml`.

### No aparecen datos de un sensor

Verificar que el nodo y measurement configurados sean correctos. Una lectura
que supera `caduca_s` se muestra como `sin_datos`; esto es intencional.

### El historial está vacío

Comprobar que la variable solicitada exista en el YAML y que InfluxDB tenga
datos dentro del rango seleccionado. Los huecos no se rellenan con ceros.

## Seguridad

- Usar un token de InfluxDB de solo lectura.
- Mantener `backend/.env` fuera de Git.
- No guardar tokens en archivos de `web/`.
- No conectar el navegador directamente a InfluxDB.
- Revisar y rotar credenciales de los sistemas de adquisición antes de una
  exposición pública.

## Documentación adicional

- [`guia_backend_gemelo_digital_l419.md`](guia_backend_gemelo_digital_l419.md)
- [`guia_frontend_gemelo_digital_l419.md`](guia_frontend_gemelo_digital_l419.md)
  
