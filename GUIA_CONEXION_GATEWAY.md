# Guía de conexión local al gateway ESP32

Este documento explica cómo conectar tu laptop a la red Wi-Fi que crea el ESP32 gateway y ejecutar el backend para visualizar los datos reales de los sensores en la web L418.

**Importante:** No necesitas tocar Arduino IDE ni flashear nada. El firmware ya está cargado en los ESP32 por otro encargado. Tú solo te conectas a la red Wi-Fi del gateway y levantas el backend.

---

## Qué necesitas

- Laptop con Wi-Fi y terminal (Linux)
- El repositorio `Web-PI3` clonado
- Entorno virtual de Python activado (`.venv`)
- El ESP32 gateway encendido y funcionando (ya flasheado)

---

## Paso 1: Encender el gateway ESP32

Conecta el ESP32 gateway (procesador central) a una fuente de energía:
- Cargador de celular USB
- Powerbank
- Cualquier puerto USB de 5V

Espera 10 a 20 segundos. Al encenderse, el gateway crea automáticamente una red Wi-Fi llamada:

```
GEMELO-L419
```

La dirección IP del gateway dentro de esa red es:
```
http://192.168.4.1
```

---

## Paso 2: Conectar tu laptop a la red del gateway

Desde tu terminal, busca y conéctate a la red:

```bash
# Listar redes disponibles (opcional)
nmcli device wifi list | grep GEMELO

# Conectar a la red del gateway
nmcli device wifi connect "GEMELO-L419"
```

> **Nota:** Al conectarte a esta red, tu laptop perderá el acceso a internet normal, porque el ESP32 no provee internet, solo su propia red local. Si necesitas descargar algo, hazlo antes de conectarte.

### Verificar que obtuviste una IP

```bash
ip addr show wlan0 | grep inet
```

Debes ver algo como:
```
inet 192.168.4.2/24
```

Tu laptop debe tener una IP en el rango `192.168.4.x`. El gateway está en `192.168.4.1`.

---

## Paso 3: Verificar que el gateway responde

Desde tu laptop, prueba si el gateway está activo y enviando datos:

```bash
curl -s http://192.168.4.1/api/estado
```

Deberías obtener una respuesta similar a:
```json
{"gw_ms":123456,"hora_ok":true,"id_ultimo":6}
```

Si obtienes respuesta, el gateway está funcionando y recibiendo datos de los nodos.

---

## Paso 4: Verificar la configuración del backend

El archivo `backend/.env` ya viene preconfigurado para modo gateway. Verifica que contenga:

```env
BACKEND_MODO=gateway
GATEWAY_URL=http://192.168.4.1
DATOS_DB=datos/gemelo.sqlite
SONDEO_S=2
CORS_ORIGENES=http://127.0.0.1:5500,http://localhost:5500,http://192.168.4.2:8000
```

> Si tu laptop obtuvo otra IP (por ejemplo `192.168.4.5`), cambia la última línea por `http://192.168.4.5:8000`.

---

## Paso 5: Levantar el backend

Desde la carpeta `backend` del proyecto:

```bash
cd /home/armas/Escritorio/L419/Web-PI3/backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Esto iniciará el backend que:
1. Se conecta al gateway ESP32 en `http://192.168.4.1`
2. Descarga los datos de los sensores cada 2 segundos
3. Los guarda en SQLite local (`backend/datos/gemelo.sqlite`)
4. Sirve la web L418 en el puerto 8000

---

## Paso 6: Abrir la web

Desde la misma laptop que corre el backend:

```
http://127.0.0.1:8000
```

Desde cualquier otro dispositivo conectado a la red `GEMELO-L419`:

```
http://192.168.4.2:8000
```

(Cambia `192.168.4.2` por la IP real que obtuviste en el Paso 2.)

---

## Comandos rápidos para copiar y pegar

```bash
# 1. Conectar a la red del gateway
nmcli device wifi connect "GEMELO-L419"

# 2. Verificar IP obtenida
ip addr show wlan0 | grep inet

# 3. Probar que el gateway responde
curl -s http://192.168.4.1/api/estado

# 4. Levantar el backend
cd /home/armas/Escritorio/L419/Web-PI3/backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Luego abre `http://127.0.0.1:8000` en tu navegador.

---

## Qué verás en la web

- Los **6 sensores** activos: CO₂, audio, luz, ocupación, puerta y ambiente.
- Cada sensor muestra su valor actual, unidad y estado (normal, alerta, falla, etc.).
- El historial se puede consultar en rangos de **15 min, 1 h, 6 h, 24 h, 7 días**.
- El botón **"Descargar reporte CSV"** genera un archivo con los datos del historial.

---

## Solución de problemas

| Problema | Qué hacer |
|---|---|
| No aparece la red `GEMELO-L419` | El gateway no está encendido o no tiene el firmware cargado. Pregunta a quien flasheó los ESP32. |
| `curl http://192.168.4.1/api/estado` no responde | Tu laptop no está conectada a la red Wi-Fi correcta, o el gateway aún no terminó de iniciarse. Espera 20 segundos y vuelve a intentar. |
| El backend dice `Gateway no disponible` | Verifica que `GATEWAY_URL=http://192.168.4.1` esté en `backend/.env` y que estés conectado a la red Wi-Fi `GEMELO-L419`. |
| La web carga pero los sensores dicen "sin datos" | Los nodos ESP32 pueden no estar enviando aún. Verifica que estén encendidos y dentro de alcance del gateway. |
| Pierdes internet al conectarte al Wi-Fi | Es normal. El ESP32 no da internet. Si necesitas internet, desconéctate de `GEMELO-L419` y vuelve a tu red normal. |

---

## Flujo de datos (sin terceros)

```text
Nodos ESP32 → ESP-NOW → Gateway ESP32 v4 (Wi-Fi AP, 192.168.4.1)
                                                    ↓
                                           Backend FastAPI (HTTP directo)
                                                    ↓
                                           Frontend web L418 (puerto 8000)
```

**No necesitas:** InfluxDB, Mosquitto, Telegraf, Grafana, AWS, Docker, ni ningún servicio en la nube. Todo corre localmente entre el gateway, tu laptop y el navegador.