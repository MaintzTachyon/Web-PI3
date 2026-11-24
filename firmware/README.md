# Firmware ESP32

Sketches de Arduino/ESP32 del proyecto de adquisición. Este código se compila
y se flashea en los microcontroladores; **no se ejecuta en el servidor**. Sus
datos llegan al backend a través de MQTT, Telegraf e InfluxDB (ver
[`../infra/README.md`](../infra/README.md)).

## Contenido

| Carpeta | Nodo | Sensor / función |
|---|---|---|
| `gateway/` | Gateway | Recibe ESP-NOW de los seis nodos y publica JSON por MQTT o Serial (sin TLS, pensado para `infra/local/`). |
| `gateway_nube/` | Gateway | Variante con usuario/contraseña y TLS en el puerto `8883`, pensada para `infra/prod/`. |
| `nodo_co2/` | Nodo 1 | CO₂ (MH-Z1911A) por UART2. |
| `nodo_audio/` | Nodo 2 | Nivel de ruido (Leq en dB). |
| `nodo_luz/` | Nodo 4 | Luminosidad (lux). |
| `nodo_termico/` | Nodo 5 | Ocupación estimada con sensor térmico. |
| `nodo_magnetico/` | Nodo 6 | Puerta abierta/cerrada. |
| `nodo_ambiente/` | Nodo 7 | Temperatura y humedad. |

El nodo 3 (gas/humo con MQ-2) se retiró porque el sensor no se compró. Los
demás nodos conservan su número, así que no hay que reprogramarlos.

Cada nodo incluye `espnow_nodo.h` y `paquetes.h`. El gateway incluye
`paquetes.h`; las estructuras deben coincidir entre nodos y gateway.

## Antes de compilar

Los sketches traen valores de ejemplo. Ajustar en cada archivo:

- `WIFI_SSID` / `WIFI_PASS` (gateway) y `SSID_ROUTER` (nodos).
- `MAC_GATEWAY` en cada nodo: MAC STA del ESP32 del gateway.
- `NODO_ID` en cada nodo (1 a 7).
- `GRUPO` en el gateway (`grupo1` por defecto en producción).
- `MQTT_HOST`, `MQTT_PORT`, `MQTT_USER`, `MQTT_PASS`.
- En `gateway_nube/`, el certificado `ca.crt` generado por
  `infra/prod/preparar.sh`.

No subir contraseñas, claves WiFi ni certificados reales al repositorio.

## Compilación

1. Instalar el soporte de placas ESP32 en Arduino IDE.
2. Instalar `PubSubClient` (Nick O'Leary) para los gateways.
3. Abrir el `.ino` de la carpeta correspondiente y seleccionar la placa ESP32.
4. Compilar y flashear.
5. Verificar en el monitor Serial que el nodo encuentre el gateway y que el
   gateway publique en los tópicos `utec/gemelo/<grupo>/<nodo>/<tipo>`.

## Formato de datos

El gateway publica un JSON con los campos que espera Telegraf:

```text
utec/gemelo/<grupo>/nodo<id>/<tipo>
```

donde `<tipo>` es uno de `co2`, `audio`, `luz`, `termico`,
`magnetico` o `ambiente`. Los nombres de los fields coinciden con
`backend/config/sensores.yaml`, por lo que no hace falta tocar el backend al
reprogramar un nodo mientras se mantenga el contrato.
