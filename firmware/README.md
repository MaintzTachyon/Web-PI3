# Firmware ESP32

Sketches de Arduino/ESP32 del sistema de adquisición, tomados de
[josecarita/Gemelo-digital-L419-Gateway](https://github.com/josecarita/Gemelo-digital-L419-Gateway),
que es la base común de comunicación del curso. Se compilan y flashean en los
microcontroladores; **no se ejecutan en el servidor**.

## Cómo se comunican

```text
Nodos (ESP-NOW) ─► gateway_ap ─► memoria flash (LittleFS) ─► HTTP en su propia red Wi-Fi
```

El gateway **no usa MQTT ni internet**. Crea la red `GEMELO-L419`
(clave en `AP_PASS`), guarda cada mensaje en su flash aunque nadie esté
conectado y expone:

| Ruta | Devuelve |
|---|---|
| `http://192.168.4.1/` | página propia del gateway con la tabla en vivo |
| `/api/ultimos` | último JSON de cada nodo y `hace_s` (segundos desde que llegó; `-1` = recuperado tras un reinicio) |
| `/api/datos?desde=<id>&max=<n>` | registros guardados con `id > desde`, en JSONL |
| `/api/estado` | `gw_ms`, `hora_ok`, `id_ultimo`, uso de flash, motivo del último reinicio |
| `/api/hora?epoch_ms=<ms>` | fija la hora del gateway (no tiene NTP) |
| `/api/borrar?confirmar=si` | borra lo guardado (solo después de descargarlo) |

El backend (`BACKEND_MODO=gateway`) consulta estas rutas cada 2 s desde una
laptop conectada a `GEMELO-L419`; ver el [README principal](../README.md).

## Contenido

| Carpeta | Nodo | Sensor / función |
|---|---|---|
| `gateway_ap/` | Gateway | ESP-NOW → JSON → flash → API HTTP. Incluye `Guia_gateway_AP.docx`. |
| `nodo_co2/` | Nodo 1 | CO₂ (MH-Z1911A) por UART2. |
| `nodo_audio/` | Nodo 2 | Nivel de ruido (INMP441, Leq en dB). |
| `nodo_luz/` | Nodo 4 | Iluminación (BH1750). |
| `nodo_termico/` | Nodo 5 | Conteo de personas (MLX90640). |
| `nodo_magnetico/` | Nodo 6 | Puerta abierta/cerrada (KY-024). |
| `nodo_ambiente/` | Nodo 7 | Temperatura, humedad y presión (BME280). |
| `obtener_mac.ino` | — | Imprime la MAC STA de un ESP32 (para `MAC_GATEWAY`). |

El nodo 3 (gas MQ-2) no existe porque el sensor no se compró. `paquetes.h`
conserva su estructura para no cambiar los números de los demás tipos.

Cada nodo incluye `espnow_nodo.h` y `paquetes.h`; `paquetes.h` debe ser
idéntico en todos los nodos y en el gateway.

## Antes de compilar

- **Gateway:** `AP_SSID`, `AP_PASS` y `AP_CANAL` (o `MODO_AP 0` con
  `STA_SSID`/`STA_PASS` para usar una red existente).
- **Cada nodo:** `MAC_GATEWAY` = MAC STA del ESP32 del gateway (usar
  `obtener_mac.ino`), `SSID_ROUTER` = `AP_SSID` del gateway y
  `CANAL_DEFECTO` = `AP_CANAL`.
- `NODO_ID` ya viene fijado en cada nodo (1, 2, 4, 5, 6, 7) y coincide con
  `backend/config/sensores.yaml`.

> `nodo_co2.ino` trae `SSID_ROUTER = "UTEC-Proyectos"`, a diferencia de los
> demás nodos (`"GEMELO-L419"`). Funciona igual porque, si no encuentra la red,
> usa `CANAL_DEFECTO = 1`, que es el canal del gateway; conviene igualarlo.

## Compilación

1. Instalar el soporte de placas ESP32 en Arduino IDE.
2. Librerías: `Adafruit BME280` (ambiente), `BH1750` de Christopher Laws (luz)
   y `Adafruit MLX90640` (térmico). El gateway solo usa librerías del core.
3. Abrir el `.ino` de la carpeta, seleccionar la placa ESP32, compilar y flashear.
4. Verificar en el monitor Serial que el gateway imprima los JSON de cada nodo
   y abrir `http://192.168.4.1` desde la laptop conectada a `GEMELO-L419`.

## Formato de datos

Cada mensaje es un JSON con `id`, `nodo`, `mac`, `seq`, `ts`, `gw_ms`,
`uptime_ms`, `perdidos`, `tipo` (`co2`, `audio`, `luz`, `termico`,
`magnetico` o `ambiente`), los campos de la medición, `anomalias` (`"A|B"` o
`"NINGUNA"`) y `anom_bits`. Los nombres de los campos coinciden con
`backend/config/sensores.yaml`, así que no hace falta tocar el backend al
reprogramar un nodo mientras no cambie su JSON.
