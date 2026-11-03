# Guía de estructura y desarrollo del backend — Gemelo Digital del aula L419

Esta guía complementa a `guia_frontend_gemelo_digital_l419.md`. Define **qué construir, en qué orden y con qué estructura** para que la página del aula muestre datos reales. No contiene el código completo: contiene el diseño, los contratos y los pasos para implementarlo.

---

## 1. Objetivo y alcance

El backend es una **capa de lectura y presentación** entre InfluxDB y la página del aula. Su trabajo es:

- Leer las mediciones que ya se guardan en InfluxDB.
- Traducirlas al formato que necesita el frontend (valor, unidad, estado, hora de la última lectura).
- Entregarlas en tiempo casi real y como historial.
- Mantener las credenciales de InfluxDB fuera del navegador.

### Alcance de esta etapa

- Backend para **2 sensores reales**: el nodo de CO₂ (`nodo_id = 1`) y el nodo de audio (`nodo_id = 2`).
- Diseño **escalable** para los 4 sensores restantes: agregar un sensor del mismo tipo debe ser solo una entrada de configuración.
- Modo DEMO opcional, con el mismo formato que los datos reales, para desarrollar el frontend sin hardware.

### Fuera del alcance (no se toca)

- Firmware de los ESP32 y protocolo ESP-NOW.
- Gateway ESP32 v4, Mosquitto, Telegraf e InfluxDB: el flujo de adquisición actual se conserva tal cual.
- Escritura de datos: el backend **no escribe** en InfluxDB ni publica en MQTT.

> La guía del frontend pide no crear "un backend de adquisición paralelo". Este backend cumple eso: no adquiere nada, solo **consulta** lo que el sistema existente ya almacena.

---

## 2. Lo que el repositorio ya hace

Revisé `estructurapi3` (commit `c785fcf`, "conexiones de sensores"). Esto es lo que el backend debe respetar.

### 2.1 Flujo real de datos

```text
Nodo CO₂ (nodo_id 1) ─┐
                      ├─ ESP-NOW ─► Gateway ESP32 v4 ─ JSON ─► MQTT ─► Mosquitto
Nodo audio (nodo_id 2)┘                                                    │
                                                                           ▼
                                                                       Telegraf
                                                                           │
                                                                           ▼
                                                                       InfluxDB ──► Grafana
                                                                           │
                                                                    [ BACKEND NUEVO ]
                                                                           │
                                                                           ▼
                                                                  Página del aula L419
```

### 2.2 Tópicos y mensajes

El gateway publica un JSON por paquete recibido, en:

```text
utec/gemelo/<grupo>/nodo<id>/<tipo>        ej.: utec/gemelo/grupo1/nodo1/co2
utec/gemelo/<grupo>/gateway/estado         "online" / "offline" (retenido)
```

Campos comunes de todo mensaje: `nodo`, `mac`, `seq`, `ts` (UTC en ms, `null` si el gateway aún no tiene NTP), `uptime_ms`, `perdidos`, `tipo`.

### 2.3 Campos por tipo de sensor

| Tipo | `nodo_id` | Periodo de envío | Campos propios |
|---|---|---|---|
| `co2` | 1 | 5 s | `co2_ppm`, `delta_30s`, `temp_c`, `calentando`, `nivel`, `anomalias`, `anom_bits` |
| `audio` | 2 | 1 s | `leq_db`, `lmax_db`, `pico_db`, `base_db`, `freq_dom_hz`, `tonal`, `bloques_fuertes`, `calibrando`, `anomalias`, `anom_bits` |

Valores especiales definidos por el firmware:

- `co2_ppm`: `-1` = el sensor no respondió, `-2` = checksum inválido. **No son mediciones.**
- `nivel` (CO₂): `NORMAL`, `ALERTA` (≥ 1000 ppm), `CRITICO` (≥ 1500 ppm), `CALENTANDO` (3 min iniciales), `SIN_DATO`. Los umbrales los decide el nodo, no el backend.
- `anomalias`: texto `"A|B"` o `"NINGUNA"`. Valores posibles: CO₂ → `FALLO_SENSOR`, `CO2_PICO_RAPIDO`, `CO2_ALERTA_VENTILACION`, `CO2_CRITICO`; audio → `FALLO_AUDIO`, `RUIDO_IMPACTO`, `RUIDO_FUERTE_SOSTENIDO`, `RUIDO_MECANICO_CONSTANTE`.
- `temp_c`, o cualquier flotante inválido, llega como `null`.

### 2.4 Cómo queda en InfluxDB (según `telegraf.conf`)

| Elemento | Valor |
|---|---|
| Organización / bucket | `utec` / `gemelo` |
| `_measurement` | el valor de `tipo`: `co2`, `audio` |
| Tags | `nodo` (texto: `"1"`, `"2"`), `mac`, `grupo` |
| Fields | el resto de campos del JSON (los textos `nivel` y `anomalias` se guardan como string) |
| Tiempo | el campo `ts` del gateway |

> Confirma los nombres exactos con el paso 0 de la sección 11. Telegraf puede nombrar o convertir algo distinto a lo que se deduce del archivo de configuración.

### 2.5 Observaciones que afectan el diseño

1. **`temp_c` del nodo CO₂ no es la temperatura del aula.** El firmware la describe como "temperatura interna aprox." del sensor. El frontend no debe mostrarla como temperatura ambiente (el ejemplo de la guía del frontend usa temperatura y humedad; los sensores reales son CO₂ y audio).
2. **Un campo `null` no se guarda.** Si `temp_c` falta en el último paquete, su último valor en InfluxDB es de un paquete anterior. Por eso la "última lectura" no debe obtenerse con `pivot` en Flux (ver sección 8).
3. **El estado del gateway no llega a InfluxDB.** Telegraf solo se suscribe a `.../co2` y `.../audio`; el tópico `.../gateway/estado` no se almacena. El indicador de conexión se deriva de la **antigüedad de las lecturas** (sección 7.2).
4. **Telegraf tiene los tópicos fijos** (`co2` y `audio`). Un tipo nuevo de sensor exige editar `telegraf.conf` (sección 14).
5. **Si el gateway no tiene NTP**, envía `ts = null`. Verifica en el paso 0 qué hace Telegraf con esos mensajes (puede descartarlos o ponerles la hora de llegada).
6. **Hay dos stacks**: `servidor_iot/` (laptop, sin cifrado) y `servidor_iot_prod/` (VM, TLS + Caddy + Grafana público). El backend debe poder correr en ambos cambiando solo variables de entorno.

### 2.6 Hallazgos de seguridad del repositorio (resolver antes de exponer nada)

El repositorio es público y contiene:

- Los archivos `.env` de `servidor_iot/` y `servidor_iot_prod/` versionados (definen el token de InfluxDB y contraseñas). Si tienen valores reales, **rótalos** y agrega `.env` al `.gitignore`.
- El SSID y la contraseña de WiFi en texto plano en `gateway/gateway.ino` (y el SSID en `nodo_audio.ino`). Cambia la contraseña y mueve estos datos a un archivo ignorado por git (por ejemplo `secretos.h`).

El backend nuevo **no debe repetir** este patrón: sus credenciales van en un `.env` que no se versiona, con un `.env.example` sin valores reales.

---

## 3. Decisiones de arquitectura

### 3.1 Qué hace el backend y qué no

| Decisión | Elección | Motivo |
|---|---|---|
| Fuente de datos | **InfluxDB** (no MQTT) | Es la fuente única de verdad: las mismas cifras que Grafana, con historial. No duplica la adquisición. |
| Tiempo real | Sondeo interno a InfluxDB cada ~2 s + **SSE** hacia el navegador | Un solo consultor hacia InfluxDB sin importar cuántos navegadores estén abiertos. `EventSource` es nativo y no requiere librerías en el frontend. |
| Credenciales | Token de **solo lectura**, solo en el servidor | El navegador nunca ve el token (requisito de la guía del frontend). |
| Estado de sensores | Calculado en el backend a partir de los campos del nodo | El frontend solo pinta; no repite reglas. |
| Configuración de sensores | Archivo `sensores.yaml` | Agregar un sensor del mismo tipo = una entrada nueva, sin tocar código. |

### 3.2 Stack propuesto

| Pieza | Elección |
|---|---|
| Lenguaje | Python 3.12+ |
| Framework | FastAPI + Uvicorn |
| Acceso a InfluxDB | `influxdb-client` (consultas Flux) |
| Configuración | `pydantic-settings` + `pyyaml` |
| Pruebas | `pytest` + `httpx` |
| Contenedor | Docker (se suma al `docker-compose.yml` existente) |

Se eligió Python por coherencia con el resto del proyecto y porque FastAPI valida las respuestas y genera documentación interactiva en `/docs`, útil para probar sin frontend. Express (Node) también serviría; la estructura de este documento no cambia.

> La guía del frontend dice "no instalar todavía Flask/Express". Eso aplica a `web/`. El backend vive en su propia carpeta con sus propias dependencias.

---

## 4. Estructura de carpetas

Se agrega `backend/` en la raíz del repositorio, junto a `web/`, sin mover ni renombrar nada existente.

```text
estructurapi3/
├── gateway/  gateway_nube/  nodo_audio/  nodo_co2/     (sin cambios)
├── servidor_iot/  servidor_iot_prod/                    (solo se agrega el servicio "api")
├── web/                                                 (frontend)
│
└── backend/
    ├── Dockerfile
    ├── requirements.txt
    ├── .env.example
    ├── .gitignore
    │
    ├── config/
    │   └── sensores.yaml          # catálogo de sensores (fuente de escalabilidad)
    │
    ├── app/
    │   ├── main.py                # crea la app, CORS, rutas, tarea de sondeo
    │   ├── config.py              # variables de entorno (URL, org, bucket, token, modo)
    │   ├── registro.py            # carga y valida sensores.yaml
    │   ├── modelos.py             # esquemas de respuesta (contrato con el frontend)
    │   ├── influx.py              # cliente de solo lectura y consultas Flux
    │   ├── estados.py             # reglas de estado por tipo de sensor
    │   ├── servicio.py            # une registro + influx + estados; caché corta
    │   ├── sondeo.py              # tarea en segundo plano y difusión a clientes SSE
    │   ├── simulador.py           # modo DEMO con el mismo contrato
    │   └── rutas/
    │       ├── salud.py           # GET /api/v1/salud
    │       ├── sensores.py        # catálogo e historial
    │       ├── lecturas.py        # últimas lecturas
    │       └── stream.py          # SSE
    │
    └── tests/
        ├── test_estados.py
        ├── test_registro.py
        └── test_api.py
```

| Archivo | Responsabilidad |
|---|---|
| `registro.py` | Lee `sensores.yaml`, valida (ids únicos, `nodo` único por medición, variables declaradas) y falla al arrancar si hay errores. |
| `influx.py` | Único módulo que conoce Flux e InfluxDB. Construye consultas **solo con valores validados contra el registro**. |
| `estados.py` | Funciones puras: reciben los campos de la última lectura y devuelven el estado. Fáciles de probar. |
| `servicio.py` | Orquesta: pide a `influx.py`, aplica `estados.py`, arma el contrato. Mantiene una caché de ~1 s. |
| `sondeo.py` | Una sola tarea que consulta cada ~2 s, detecta lecturas nuevas y las envía a todas las conexiones SSE. |
| `simulador.py` | Genera lecturas coherentes con `origen: "demo"`. Se activa con `BACKEND_MODO=demo`. |

---

## 5. Registro de sensores (`config/sensores.yaml`)

Es el núcleo de la escalabilidad. Ejemplo con los 2 sensores actuales:

```yaml
aula: L419
grupo: grupo1

sensores:
  - id: sensor-co2-01
    nodo: 1
    medicion: co2
    etiqueta: "CO₂"
    periodo_s: 5
    caduca_s: 30              # sin lecturas por este tiempo -> "sin_datos"
    ubicacion: { x: null, y: null }   # coordenadas en el SVG; pendiente del plano real
    variable_principal: co2_ppm
    estado: { regla: nivel_nodo, campo: nivel }
    variables:
      co2_ppm:   { etiqueta: "CO₂",              unidad: ppm, decimales: 0, agregacion: mean, invalidos: [-1, -2] }
      delta_30s: { etiqueta: "Cambio en 30 s",   unidad: ppm, decimales: 0, agregacion: mean }
      temp_c:    { etiqueta: "Temp. interna del sensor", unidad: "°C", decimales: 0, agregacion: mean, uso: diagnostico }

  - id: sensor-audio-01
    nodo: 2
    medicion: audio
    etiqueta: "Ruido"
    periodo_s: 1
    caduca_s: 10
    ubicacion: { x: null, y: null }
    variable_principal: leq_db
    estado: { regla: anomalias_nodo, campo: anomalias, calibrando: calibrando }
    variables:
      leq_db:      { etiqueta: "Nivel equivalente", unidad: dB,  decimales: 1, agregacion: mean }
      lmax_db:     { etiqueta: "Máximo",            unidad: dB,  decimales: 1, agregacion: max }
      pico_db:     { etiqueta: "Pico",              unidad: dB,  decimales: 1, agregacion: max }
      base_db:     { etiqueta: "Ruido de fondo",    unidad: dB,  decimales: 1, agregacion: mean }
      freq_dom_hz: { etiqueta: "Frecuencia dominante", unidad: Hz, decimales: 0, agregacion: mean }
```

Reglas de uso:

- El `id` es el **identificador estable** que usará el SVG del frontend (`sensor-co2-01`). No se cambia una vez creado.
- Los nombres de `variables` son **exactamente** los nombres de los fields en InfluxDB. No inventes alias en esta capa.
- Las variables con `uso: diagnostico` se entregan en el detalle, pero no como valor principal del indicador.
- Los 4 sensores restantes no están definidos en el repositorio. Se agregarán aquí cuando existan (sección 14); no se deben crear entradas ficticias.

---

## 6. Contrato de la API

Prefijo `/api/v1`. Todo en JSON, fechas en ISO 8601 UTC (el frontend las muestra en hora local, Lima UTC-5). Los nombres de campo respetan los del arreglo `sensoresDemo` de la guía del frontend (`id`, `tipo`, `valor`, `unidad`, `estado`, `actualizado`), de modo que reemplazar los datos simulados por los reales no obligue a rehacer la interfaz.

### 6.1 Endpoints

| Método y ruta | Uso en el frontend |
|---|---|
| `GET /api/v1/salud` | Indicador de conexión del encabezado. |
| `GET /api/v1/sensores` | Catálogo: ids, etiquetas, unidades, ubicación. Se pide una vez al abrir la página. |
| `GET /api/v1/lecturas/ultimas` | Estado inicial de todos los marcadores. |
| `GET /api/v1/sensores/{id}/historial?variable=co2_ppm&rango=1h` | Gráfico de historial al seleccionar un sensor. |
| `GET /api/v1/stream` (SSE) | Actualizaciones en vivo. |

### 6.2 `GET /api/v1/lecturas/ultimas`

```json
{
  "aula": "L419",
  "generado": "2026-11-03T20:04:35Z",
  "origen": "real",
  "sensores": [
    {
      "id": "sensor-co2-01",
      "nodo": 1,
      "tipo": "co2",
      "etiqueta": "CO₂",
      "valor": 650,
      "unidad": "ppm",
      "estado": "normal",
      "actualizado": "2026-11-03T20:04:32Z",
      "edad_s": 3,
      "variables": {
        "co2_ppm":   { "valor": 650, "unidad": "ppm", "etiqueta": "CO₂" },
        "delta_30s": { "valor": 4,   "unidad": "ppm", "etiqueta": "Cambio en 30 s" }
      },
      "anomalias": [],
      "diagnostico": { "seq": 1234, "perdidos": 0 }
    }
  ]
}
```

- `origen` es `"real"` o `"demo"`. El frontend usa este campo para mostrar la etiqueta **DEMO / SIMULACIÓN** exigida por su guía.
- Si un sensor no tiene datos recientes: `valor: null`, `estado: "sin_datos"`, y `actualizado` con la última hora conocida si existe.
- Un `co2_ppm` de `-1` o `-2` se entrega como `valor: null` con estado `falla`, nunca como número.

### 6.3 `GET /api/v1/sensores/{id}/historial`

Parámetros (con lista cerrada para evitar consultas arbitrarias):

| Parámetro | Valores | Notas |
|---|---|---|
| `variable` | una de las declaradas para ese sensor | Si no existe: `404`. |
| `rango` | `15m`, `1h`, `6h`, `24h`, `7d` | Por defecto `1h`. |

La ventana de agregación se elige sola para no superar ~500 puntos:

| Rango | Ventana |
|---|---|
| 15m | 10 s |
| 1h | 30 s |
| 6h | 2 min |
| 24h | 5 min |
| 7d | 30 min |

Respuesta:

```json
{
  "id": "sensor-co2-01",
  "variable": "co2_ppm",
  "unidad": "ppm",
  "rango": "1h",
  "ventana_s": 30,
  "puntos": [ { "t": "2026-11-03T19:04:30Z", "v": 612.4 } ]
}
```

La función de agregación (`mean` o `max`) sale de `agregacion` en el YAML. Los huecos se omiten, no se rellenan con ceros.

### 6.4 `GET /api/v1/salud`

```json
{
  "backend": "ok",
  "influx": "ok",
  "conexion": "parcial",
  "sensores_esperados": 2,
  "sensores_con_datos": 1
}
```

`conexion` alimenta el indicador del encabezado:

| Valor | Condición |
|---|---|
| `en_linea` | Todos los sensores del registro tienen datos recientes. |
| `parcial` | Al menos uno, pero no todos. |
| `sin_datos` | Ninguno (gateway apagado, WiFi caído o Telegraf detenido). |

Si el frontend no logra contactar al backend, muestra "sin conexión con el servidor" por su cuenta. Si InfluxDB no responde, las rutas devuelven `503` con `{"influx": "no_disponible"}`.

### 6.5 `GET /api/v1/stream` (Server-Sent Events)

```text
event: lectura
data: { ...mismo objeto de sensor que en /lecturas/ultimas... }

event: conexion
data: { "conexion": "parcial", "sensores_con_datos": 1 }

: latido   (comentario cada 15 s para mantener la conexión)
```

- Se emite `lectura` solo cuando hay una lectura nueva (cambia `actualizado`) o cambia el `estado`.
- Al conectarse, el cliente recibe primero una `lectura` por sensor para no esperar al siguiente paquete.
- `EventSource` se reconecta solo; aun así, el frontend debe tener un respaldo: si el stream falla, consultar `/lecturas/ultimas` cada 5 s.

---

## 7. Lógica de estado

### 7.1 Estados que entrega el backend

`normal` · `alerta` · `critico` · `calentando` · `calibrando` · `falla` · `sin_datos`

El frontend deberá tener un estilo para cada uno (su guía solo ejemplifica `normal`).

### 7.2 Reglas

Cada sensor declara su `regla` en el YAML; `estados.py` mantiene un diccionario `regla → función`.

| Regla | Aplica a | Lógica (se evalúa en este orden) |
|---|---|---|
| `nivel_nodo` | CO₂ | 1) `edad_s > caduca_s` → `sin_datos`. 2) `anom_bits` con `FALLO_SENSOR`, o `co2_ppm` en `-1/-2` → `falla`. 3) Si no, traducir `nivel`: `NORMAL→normal`, `ALERTA→alerta`, `CRITICO→critico`, `CALENTANDO→calentando`, `SIN_DATO→sin_datos`. |
| `anomalias_nodo` | Audio | 1) `edad_s > caduca_s` → `sin_datos`. 2) `calibrando = 1` → `calibrando`. 3) `FALLO_AUDIO` → `falla`. 4) Cualquier otra anomalía distinta de `NINGUNA` → `alerta`. 5) Si no → `normal`. |

Principios:

- **El backend no redefine umbrales** que ya decide el firmware (1000 y 1500 ppm). Si se cambian en el nodo, el backend no necesita tocarse.
- `edad_s` se calcula como `ahora_del_servidor − _time` de la lectura. Ambos relojes dependen de NTP; si se observa un desfase constante, corregirlo a nivel del sistema, no con un parche en el código.
- `caduca_s` está en el YAML por sensor: 30 s para CO₂ (envía cada 5 s) y 10 s para audio (cada 1 s). Ajústalos según la estabilidad real del WiFi.

---

## 8. Consultas a InfluxDB (Flux)

Todas las consultas viven en `influx.py`.

### 8.1 Última lectura de un sensor

```flux
from(bucket: "gemelo")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "co2" and r.nodo == "1" and r.grupo == "grupo1")
  |> last()
```

**No uses `pivot` aquí.** Cada field se guarda como una serie distinta; si un campo faltó en el último paquete (por ejemplo `temp_c = null`), su `last()` trae una hora anterior y el `pivot` por `_time` separaría el resultado en varias filas. En su lugar:

1. Recibe un registro por field, con su `_time`.
2. `actualizado` = el `_time` **más reciente** entre todos los fields.
3. Descarta (o marca como obsoletos) los fields cuya hora sea anterior a `actualizado`.

La ventana `-1h` es configurable; si no hay nada en ese lapso, el sensor sale como `sin_datos`.

### 8.2 Historial

```flux
from(bucket: "gemelo")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "co2" and r.nodo == "1" and r._field == "co2_ppm")
  |> aggregateWindow(every: 30s, fn: mean, createEmpty: false)
```

### 8.3 Seguridad de las consultas

- `medicion`, `nodo`, `_field`, `rango` y `fn` **nunca** se arman con texto que escribió el usuario: salen del registro o de una lista cerrada. Esto evita inyección de Flux.
- Si la versión instalada de `influxdb-client` admite parámetros enlazados en `query()`, úsalos además de la validación.
- Las llamadas del cliente son bloqueantes: ejecútalas con `asyncio.to_thread` para no frenar el servidor.
- Para el estado inicial, lanza una consulta por sensor en paralelo; con 6 sensores el costo es bajo.

---

## 9. Tiempo real

Diseño de `sondeo.py`:

1. Al iniciar, `main.py` crea **una** tarea en segundo plano.
2. Cada `SONDEO_S` (por defecto 2 s), pide la última lectura de cada sensor y la guarda en una caché en memoria.
3. Si cambió `actualizado` o `estado` respecto a lo último emitido, publica el evento a la cola de cada cliente SSE conectado.
4. `GET /lecturas/ultimas` lee esa misma caché (válida ~1 s), así que la cantidad de navegadores abiertos **no** multiplica las consultas a InfluxDB.
5. Si InfluxDB falla, la tarea registra el error, emite `conexion: sin_datos` y reintenta en el siguiente ciclo, sin caerse.

Para el audio (1 lectura por segundo), un sondeo de 2 s mostrará todas las lecturas con un pequeño retraso; para esta interfaz es suficiente. Si más adelante se necesita menos latencia, el cambio queda aislado en `sondeo.py`.

---

## 10. Seguridad

| Tema | Medida |
|---|---|
| Token de InfluxDB | Crear un **token de solo lectura** del bucket `gemelo` solo para el backend. No usar el token de administrador. |
| Variables de entorno | `.env` fuera de git; `.env.example` con nombres y sin valores. |
| Exposición | InfluxDB sigue accesible solo dentro de la red de Docker / `127.0.0.1`. Solo el backend (vía Caddy) sale a internet. |
| CORS | En desarrollo, permitir el origen de Live Server (`http://127.0.0.1:5500`). En producción, mismo origen: sin CORS. |
| Métodos | Solo `GET`. No hay endpoints de escritura. |
| Límites | `rango` y `variable` con lista cerrada; máximo ~500 puntos por respuesta. |
| Datos personales | No se expone `mac` ni datos de red en las respuestas públicas. |

Crear el token de lectura (con el stack de Docker en marcha):

```bash
# 1) Obtener el ID del bucket
docker exec influxdb influx bucket list --org utec --token "$INFLUX_TOKEN"

# 2) Crear el token de solo lectura (reemplaza <BUCKET_ID>)
docker exec influxdb influx auth create \
  --org utec --read-bucket <BUCKET_ID> \
  --description "api-lectura-gemelo" --token "$INFLUX_TOKEN"
```

Copia el token resultante a `backend/.env`.

---

## 11. Proceso de creación paso a paso

### Paso 0 — Verificar que los datos ya llegan a InfluxDB

Antes de escribir código, confirma lo que existe. En el stack en marcha:

```bash
# Mensajes del gateway (sustituye grupo1 si usas otro)
docker exec mosquitto mosquitto_sub -t 'utec/gemelo/#' -v

# Qué mediciones, tags y fields hay realmente en InfluxDB
docker exec influxdb influx query --org utec --token "$INFLUX_TOKEN" '
import "influxdata/influxdb/schema"
schema.measurements(bucket: "gemelo")'
```

En la interfaz de InfluxDB (puerto 8086, **Data Explorer**) revisa, para `co2` y `audio`, los tags (`nodo`, `grupo`, `mac`) y los nombres de field. **Si algún nombre difiere de la sección 2.3, el YAML debe seguir a InfluxDB, no al revés.**

Anota también qué pasa cuando el gateway no tiene NTP (`ts = null`).

### Paso 1 — Crear la carpeta y el entorno

```bash
cd estructurapi3
mkdir -p backend/config backend/app/rutas backend/tests
cd backend

python -m venv .venv
source .venv/bin/activate

pip install fastapi "uvicorn[standard]" influxdb-client pydantic-settings pyyaml
pip install pytest httpx
pip freeze > requirements.txt     # revisa que quede solo lo necesario
```

(En CachyOS/Arch: `sudo pacman -S python python-pip` si aún no están instalados.)

Crea `.gitignore` con al menos: `.venv/`, `__pycache__/`, `.env`.

### Paso 2 — Configuración y variables de entorno

`backend/.env.example`:

```text
BACKEND_MODO=real                  # real | demo
INFLUX_URL=http://localhost:8086
INFLUX_ORG=utec
INFLUX_BUCKET=gemelo
INFLUX_TOKEN_LECTURA=              # token de SOLO lectura
GRUPO=grupo1
SONDEO_S=2
CORS_ORIGENES=http://127.0.0.1:5500
```

Copia a `.env` y completa el token. `config.py` lee estas variables con `pydantic-settings`.

### Paso 3 — Registro de sensores

1. Crea `config/sensores.yaml` con los 2 sensores (sección 5), usando los nombres confirmados en el paso 0.
2. Implementa `registro.py`: carga el YAML y valida con Pydantic. Debe fallar al arrancar si hay ids repetidos o variables sin unidad.
3. Prueba: `pytest tests/test_registro.py`.

### Paso 4 — Reglas de estado

Implementa `estados.py` como funciones puras (sección 7) y cúbrelas con `tests/test_estados.py`. Casos mínimos:

- CO₂ `NORMAL`, `ALERTA`, `CRITICO`, `CALENTANDO`.
- `co2_ppm = -1` y `-2` → `falla`, con `valor = null`.
- Lectura más vieja que `caduca_s` → `sin_datos`.
- Audio con `calibrando = 1`; con `RUIDO_IMPACTO`; con `NINGUNA`.

### Paso 5 — Capa InfluxDB

Implementa `influx.py` con dos funciones: `ultima_lectura(sensor)` y `historial(sensor, variable, rango)`. Valida con el stack real que `ultima_lectura` devuelve lo que muestra el Data Explorer.

### Paso 6 — Servicio y rutas

1. `servicio.py`: combina registro + influx + estados y arma los objetos del contrato (sección 6), incluyendo el manejo de `-1/-2`.
2. `modelos.py`: esquemas de respuesta.
3. `rutas/`: `salud`, `sensores`, `lecturas`.
4. `main.py`: crea la app, activa CORS con `CORS_ORIGENES` y registra las rutas.

Ejecutar en desarrollo:

```bash
uvicorn app.main:app --reload --port 8000
```

Probar:

```bash
curl http://127.0.0.1:8000/api/v1/salud
curl http://127.0.0.1:8000/api/v1/sensores
curl http://127.0.0.1:8000/api/v1/lecturas/ultimas
curl "http://127.0.0.1:8000/api/v1/sensores/sensor-co2-01/historial?variable=co2_ppm&rango=1h"
```

La documentación interactiva queda en `http://127.0.0.1:8000/docs`.

### Paso 7 — Tiempo real (SSE)

Implementa `sondeo.py` y `rutas/stream.py` (sección 9). Prueba con:

```bash
curl -N http://127.0.0.1:8000/api/v1/stream
```

Deberías recibir una `lectura` por sensor al conectar y luego una cada vez que llegue un paquete nuevo.

### Paso 8 — Modo DEMO

Implementa `simulador.py` para que, con `BACKEND_MODO=demo`, el backend responda con el **mismo contrato** pero con `origen: "demo"`. Permite avanzar con el frontend sin el hardware encendido y cumple la exigencia de marcar los datos ficticios.

### Paso 9 — Probar fallos reales

| Prueba | Resultado esperado |
|---|---|
| Apagar el nodo de CO₂ | A los ~30 s, ese sensor pasa a `sin_datos`; `conexion` pasa a `parcial`. |
| Apagar el gateway | A los pocos segundos, todos `sin_datos`; `conexion = sin_datos`. |
| Detener InfluxDB | Rutas responden `503`; el stream no se cae; al volver InfluxDB, se recupera solo. |
| Reiniciar un nodo | `calentando` durante los primeros 3 min (CO₂) o `calibrando` ~5 s (audio). |

### Paso 10 — Contenedor y despliegue

Ver sección 12.

### Paso 11 — Conectar el frontend

Ver sección 13.

---

## 12. Despliegue

### 12.1 `backend/Dockerfile` (esquema)

- Imagen base `python:3.12-slim`.
- Instalar `requirements.txt`, copiar `app/` y `config/`.
- Ejecutar `uvicorn app.main:app --host 0.0.0.0 --port 8000`.

### 12.2 Servicio `api` en los `docker-compose.yml`

Se **agrega** un servicio; no se modifican los existentes.

```yaml
  api:
    build: ../backend
    container_name: api
    depends_on:
      - influxdb
    environment:
      BACKEND_MODO: real
      INFLUX_URL: http://influxdb:8086
      INFLUX_ORG: utec
      INFLUX_BUCKET: gemelo
      INFLUX_TOKEN_LECTURA: ${INFLUX_TOKEN_LECTURA}
      GRUPO: grupo1
    volumes:
      - ../web:/app/web:ro      # opcional: servir el frontend desde el mismo servicio
    restart: unless-stopped
```

- **`servidor_iot/` (laptop):** agrega `ports: ["8000:8000"]` para probar desde el navegador.
- **`servidor_iot_prod/` (VM):** **no publiques puertos**; el acceso será por Caddy.
- Agrega `INFLUX_TOKEN_LECTURA` al `.env` correspondiente (que no debe versionarse).

### 12.3 Caddy (producción)

Hoy el dominio principal sirve Grafana. Para no mezclarlo, usa un **subdominio** para el aula (requiere un registro DNS adicional):

```text
l419.{$DOMINIO} {
	encode gzip
	reverse_proxy api:8000 {
		flush_interval -1      # necesario para que el stream SSE no se acumule
	}
}
```

El backend puede servir también los archivos de `web/` (montados en el contenedor), de modo que una sola entrada atienda página y API en el mismo origen y no se necesite CORS. Si el stream llega con retraso, excluye `/api/v1/stream` de `encode`.

---

## 13. Integración con el frontend

Cambios previstos en `web/js/datos.js` (sin tocar la interfaz):

| Función | Qué hace |
|---|---|
| `cargarCatalogo()` | `GET /api/v1/sensores` al abrir la página. |
| `cargarUltimas()` | `GET /api/v1/lecturas/ultimas` para pintar el estado inicial. |
| `suscribirStream(callback)` | `EventSource` a `/api/v1/stream`; si falla, vuelve a consultar `/lecturas/ultimas` cada 5 s. |
| `cargarHistorial(id, variable, rango)` | Alimenta `graficos.js` (Chart.js). |

- Una constante `API_BASE` define el origen: vacía en producción (mismo origen) y `http://127.0.0.1:8000` en desarrollo con Live Server.
- `data/sensores-demo.js` queda como respaldo; la etiqueta DEMO se muestra cuando `origen === "demo"`.
- Los ids del SVG (`sensor-co2-01`, `sensor-audio-01`) deben coincidir con los `id` del YAML.
- El indicador del encabezado usa `conexion` de `/salud` y de los eventos `conexion`.
- Mostrar `temp_c` del nodo CO₂ solo como dato de diagnóstico del sensor, nunca como temperatura del aula.

---

## 14. Cómo agregar los 4 sensores restantes

### Caso A — Otro sensor de un tipo que ya existe (ej. un segundo nodo de CO₂)

1. Firmware: asignar un `NODO_ID` nuevo y único.
2. **Backend:** agregar una entrada en `sensores.yaml` con el mismo `medicion` y `regla`, otro `id`, `nodo` y `ubicacion`.
3. **Frontend:** agregar el marcador en el SVG con ese `id`.

No hay cambios en código del backend ni en Telegraf.

### Caso B — Un tipo de sensor nuevo

| # | Dónde | Qué hacer |
|---|---|---|
| 1 | `paquetes.h` | Agregar un `TIPO_*` y su `struct`. El archivo debe ser **idéntico** en las 5 copias (`gateway`, `gateway_nube`, `nodo_co2`, `nodo_audio` y el nodo nuevo). |
| 2 | Gateway (`gateway.ino` y `gateway_nube.ino`) | Agregar la rama que convierte el paquete a JSON y publica en `.../nodo<id>/<tipo>`. |
| 3 | `telegraf.conf` (**ambos**: `servidor_iot` y `servidor_iot_prod`) | Agregar el tópico `utec/gemelo/+/+/<tipo>`; si hay campos de texto nuevos, añadirlos a `json_string_fields`. Reiniciar Telegraf. |
| 4 | InfluxDB | Verificar en Data Explorer que aparece la nueva `_measurement` con sus fields. |
| 5 | `sensores.yaml` | Nueva entrada con sus variables, unidades y `agregacion`. |
| 6 | `estados.py` | Solo si el tipo necesita una regla de estado propia: agregar la función y registrarla en el diccionario `regla → función`. |
| 7 | Frontend | Marcador en el SVG y, si hace falta, estilo para el nuevo tipo. |

Los pasos 1 a 3 pertenecen a la adquisición existente: se hacen una vez por tipo de sensor, con la misma disciplina que el proyecto ya aplica (formato idéntico en todos los nodos).

---

## 15. Criterios para considerar terminado el backend

- [ ] Los nombres de measurements, tags y fields del YAML coinciden con los de InfluxDB (verificado en el paso 0).
- [ ] `GET /lecturas/ultimas` devuelve los 2 sensores con valor, unidad, estado y hora de actualización.
- [ ] Los valores `-1` / `-2` de CO₂ nunca se entregan como mediciones.
- [ ] El historial responde para cada variable declarada y rechaza variables o rangos no válidos.
- [ ] El stream SSE entrega lecturas nuevas y se recupera tras una caída de InfluxDB.
- [ ] Un nodo apagado pasa a `sin_datos` en el tiempo definido por `caduca_s`.
- [ ] El navegador nunca recibe tokens ni credenciales; el token usado es de solo lectura.
- [ ] El modo `demo` responde con `origen: "demo"` y el mismo contrato.
- [ ] Agregar un segundo sensor de un tipo existente solo requiere editar `sensores.yaml`.
- [ ] `pytest` pasa (registro, estados y API).
- [ ] No se modificó el firmware, el gateway ni la configuración de adquisición existente.

---

## 16. Decisiones pendientes

1. **Los 4 sensores restantes:** tipo, variable medida y unidad de cada uno (no están en el repositorio).
2. **Ubicación física:** coordenadas `x, y` de cada sensor sobre el SVG, cuando el plano esté listo.
3. **Dónde correrá el sistema final:** laptop (`servidor_iot`) o VM (`servidor_iot_prod`), y qué subdominio usar.
4. **Estado del gateway:** si se quiere distinguir "gateway apagado" de "sensor apagado", hay que suscribirse a `.../gateway/estado` (hoy no llega a InfluxDB). Eso implica un cliente MQTT de solo lectura y un usuario nuevo en el `acl` de Mosquitto. Por ahora se deduce de la antigüedad de las lecturas.
5. **Rotación de credenciales** del repositorio (sección 2.6), antes de desplegar.
6. **Texto de interfaz para `temp_c`:** confirmar si se muestra como diagnóstico o se oculta.
