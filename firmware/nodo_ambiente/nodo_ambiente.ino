// Nodo ambiente (GY-BME280) -> ESP-NOW -> Gateway ESP32 v4
// Temperatura, humedad relativa y presión del salón L418 (techo, centro).
#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_BME280.h>     // Librería "Adafruit BME280"
#include "paquetes.h"
#include "espnow_nodo.h"

// ================= RED =================
uint8_t MAC_GATEWAY[6] = {0x58, 0x2A, 0xBD, 0x72, 0x03, 0xDC}; // MAC STA del ESP32 que corre gateway_ap.ino
const char*   SSID_ROUTER   = "GEMELO-L419";   // red que crea gateway_ap.ino (AP_SSID); de ahí se toma el canal
const uint8_t CANAL_DEFECTO = 1;
const uint8_t NODO_ID       = 7;

// ================= PINES I2C =================
#define PIN_SDA 21
#define PIN_SCL 22

// ================= UMBRALES =================
const float CONFORT_T_MIN = 20.0;   // °C
const float CONFORT_T_MAX = 26.0;   // °C
const float HIST_T        = 0.5;    // la alarma se apaga 0.5 °C dentro del rango
const float HUM_ALTA      = 70.0;   // % HR
const float HIST_HUM      = 5.0;    // la alarma se apaga por debajo de 65 %
const float CAMBIO_T_MAX  = 1.5;    // °C de variación máxima en la ventana
const unsigned long VENTANA_CAMBIO_MS = 5UL * 60UL * 1000UL;   // 5 min
const unsigned long PERIODO_MS        = 10000;                 // una lectura y un envío cada 10 s
const int FALLOS_PARA_ALARMA = 3;

// ================= ESTADO =================
const int N_HIST = VENTANA_CAMBIO_MS / PERIODO_MS;   // 30 lecturas = 5 min
float histT[N_HIST];
int   histIdx = 0, histN = 0;

Adafruit_BME280 bme;
bool    sensorOk = false;
uint8_t direccion = 0;
bool    fueraConfort = false, humAlta = false;
int     fallosSeguidos = 0;
unsigned long tUltEnvio = 0, tUltReintento = 0;

// ================= SENSOR =================
// Lee el registro de identificación para diagnosticar módulos equivocados.
uint8_t leerChipId(uint8_t dir) {
  Wire.beginTransmission(dir);
  Wire.write(0xD0);
  if (Wire.endTransmission() != 0) return 0;
  if (Wire.requestFrom(dir, (uint8_t)1) != 1) return 0;
  return Wire.read();
}

// ---------- BMP280: se lee directamente (sin librería extra) ----------
// Los módulos "GY-BME/PMP280" pueden traer un BME280 (temp + humedad + presión)
// o un BMP280 (solo temp + presión). Con el BMP280 la humedad se envía como null.
bool esBmp = false;
uint16_t dig_T1, dig_P1;
int16_t  dig_T2, dig_T3, dig_P2, dig_P3, dig_P4, dig_P5, dig_P6, dig_P7, dig_P8, dig_P9;

bool i2cLeer(uint8_t dir, uint8_t reg, uint8_t *buf, uint8_t n) {
  Wire.beginTransmission(dir);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(dir, n) != n) return false;
  for (int i = 0; i < n; i++) buf[i] = Wire.read();
  return true;
}

bool i2cEscribir(uint8_t dir, uint8_t reg, uint8_t valor) {
  Wire.beginTransmission(dir);
  Wire.write(reg);
  Wire.write(valor);
  return Wire.endTransmission() == 0;
}

// Lee los coeficientes de calibración de fábrica del BMP280 (registros 0x88 a 0x9F)
bool bmpIniciar(uint8_t dir) {
  uint8_t c[24];
  if (!i2cLeer(dir, 0x88, c, 24)) return false;
  dig_T1 = c[0] | (c[1] << 8);            dig_T2 = (int16_t)(c[2] | (c[3] << 8));
  dig_T3 = (int16_t)(c[4] | (c[5] << 8));  dig_P1 = c[6] | (c[7] << 8);
  dig_P2 = (int16_t)(c[8] | (c[9] << 8));   dig_P3 = (int16_t)(c[10] | (c[11] << 8));
  dig_P4 = (int16_t)(c[12] | (c[13] << 8)); dig_P5 = (int16_t)(c[14] | (c[15] << 8));
  dig_P6 = (int16_t)(c[16] | (c[17] << 8)); dig_P7 = (int16_t)(c[18] | (c[19] << 8));
  dig_P8 = (int16_t)(c[20] | (c[21] << 8)); dig_P9 = (int16_t)(c[22] | (c[23] << 8));
  return dig_T1 != 0 && dig_P1 != 0 && i2cEscribir(dir, 0xF5, 0x00);   // config: sin filtro
}

// Una medición en modo forzado y compensación con las fórmulas del datasheet de Bosch
bool bmpLeer(float &t, float &p) {
  if (!i2cEscribir(direccion, 0xF4, (1 << 5) | (1 << 2) | 0x01)) return false;  // T x1, P x1, forzado
  delay(10);                                                                     // conversión ~7 ms
  uint8_t b[6];
  if (!i2cLeer(direccion, 0xF7, b, 6)) return false;
  int32_t adcP = ((int32_t)b[0] << 12) | ((int32_t)b[1] << 4) | (b[2] >> 4);
  int32_t adcT = ((int32_t)b[3] << 12) | ((int32_t)b[4] << 4) | (b[5] >> 4);
  if (adcT == 0x80000 || adcP == 0x80000) return false;   // sin medición

  int32_t v1 = ((((adcT >> 3) - ((int32_t)dig_T1 << 1))) * ((int32_t)dig_T2)) >> 11;
  int32_t v2 = (((((adcT >> 4) - ((int32_t)dig_T1)) * ((adcT >> 4) - ((int32_t)dig_T1))) >> 12) *
                ((int32_t)dig_T3)) >> 14;
  int32_t tFine = v1 + v2;
  t = ((tFine * 5 + 128) >> 8) / 100.0f;

  int64_t a = ((int64_t)tFine) - 128000;
  int64_t bb = a * a * (int64_t)dig_P6;
  bb = bb + ((a * (int64_t)dig_P5) << 17);
  bb = bb + (((int64_t)dig_P4) << 35);
  a = ((a * a * (int64_t)dig_P3) >> 8) + ((a * (int64_t)dig_P2) << 12);
  a = (((((int64_t)1) << 47) + a)) * ((int64_t)dig_P1) >> 33;
  if (a == 0) return false;
  int64_t pr = 1048576 - adcP;
  pr = (((pr << 31) - bb) * 3125) / a;
  a = (((int64_t)dig_P9) * (pr >> 13) * (pr >> 13)) >> 25;
  bb = (((int64_t)dig_P8) * pr) >> 19;
  pr = ((pr + a + bb) >> 8) + (((int64_t)dig_P7) << 4);
  p = (pr / 256.0f) / 100.0f;   // Pa -> hPa
  return true;
}

bool iniciarSensor() {
  const uint8_t dirs[2] = {0x76, 0x77};    // SDO a GND = 0x76, SDO a 3.3 V = 0x77
  for (uint8_t d : dirs) {
    uint8_t id = leerChipId(d);
    if (id == 0x60 && bme.begin(d, &Wire)) {          // BME280
      direccion = d;
      esBmp = false;
      // Modo forzado: mide solo cuando se le pide, así el sensor casi no se autocalienta.
      bme.setSampling(Adafruit_BME280::MODE_FORCED,
                      Adafruit_BME280::SAMPLING_X1,    // temperatura
                      Adafruit_BME280::SAMPLING_X1,    // presión
                      Adafruit_BME280::SAMPLING_X1,    // humedad
                      Adafruit_BME280::FILTER_OFF);
      return true;
    }
    if ((id == 0x58 || id == 0x56 || id == 0x57) && bmpIniciar(d)) {   // BMP280
      direccion = d;
      esBmp = true;
      return true;
    }
    if (id != 0) Serial.printf("# AVISO: en 0x%02X hay un chip desconocido (id=0x%02X)\n", d, id);
  }
  return false;
}

bool leer(float &t, float &h, float &p) {
  if (esBmp) {                                  // BMP280: sin humedad
    h = NAN;
    if (!bmpLeer(t, p)) return false;
    return !(t < -40 || t > 85 || p < 300 || p > 1100);
  }
  if (!bme.takeForcedMeasurement()) return false;
  t = bme.readTemperature();
  h = bme.readHumidity();
  p = bme.readPressure() / 100.0F;
  if (isnan(t) || isnan(h) || isnan(p)) return false;
  if (t < -40 || t > 85 || h < 0 || h > 100 || p < 300 || p > 1100) return false;   // fuera de rango físico
  return true;
}

// ================= ANOMALÍAS =================
uint8_t evaluar(float t, float h) {
  uint8_t an = 0;

  // Confort térmico con histéresis (evita que la alarma parpadee en el límite)
  if (!fueraConfort) fueraConfort = (t < CONFORT_T_MIN) || (t > CONFORT_T_MAX);
  else               fueraConfort = (t < CONFORT_T_MIN + HIST_T) || (t > CONFORT_T_MAX - HIST_T);
  if (fueraConfort) an |= AMB_BIT_TEMP_FUERA_CONFORT;

  if (isnan(h))      humAlta = false;           // BMP280: no mide humedad
  else if (!humAlta) humAlta = h > HUM_ALTA;
  else               humAlta = h > HUM_ALTA - HIST_HUM;
  if (humAlta) an |= AMB_BIT_HUMEDAD_ALTA;

  // Cambio rápido: comparación con la lectura de hace 5 minutos
  if (histN == N_HIST && fabsf(t - histT[histIdx]) > CAMBIO_T_MAX) an |= AMB_BIT_CAMBIO_RAPIDO_TEMP;
  histT[histIdx] = t;
  histIdx = (histIdx + 1) % N_HIST;
  if (histN < N_HIST) histN++;

  return an;
}

// ================= ENVÍO =================
void enviar(float t, float h, float p, uint8_t an) {
  PaqueteAmbiente pk = {};
  llenarCabecera(pk.h, TIPO_AMBIENTE, NODO_ID);
  pk.temp_c    = t;
  pk.hum_pct   = h;
  pk.pres_hpa  = p;
  pk.anomalias = an;
  espnowEnviar(&pk, sizeof(pk));

  Serial.printf("%lu,%.2f,%.1f,%.2f,0x%02X,%d\n", millis(), t, h, p, an, g_ultimoOk ? 1 : 0);
}

// ================= SETUP / LOOP =================
void setup() {
  Serial.begin(115200);
  delay(500);
  Wire.begin(PIN_SDA, PIN_SCL);

  if (!espnowIniciar(MAC_GATEWAY, SSID_ROUTER, CANAL_DEFECTO))
    Serial.println("# ERROR: no se pudo iniciar ESP-NOW");
  Serial.printf("# Nodo ambiente id=%d  MAC=%s  canal=%d\n",
                NODO_ID, WiFi.macAddress().c_str(), g_canal);

  sensorOk = iniciarSensor();
  if (sensorOk && esBmp) Serial.printf("# BMP280 encontrado en 0x%02X (temperatura y presion; SIN humedad)\n", direccion);
  else if (sensorOk)     Serial.printf("# BME280 encontrado en 0x%02X (temperatura, humedad y presion)\n", direccion);
  else                   Serial.println("# ERROR: no se detecta el sensor (revisar SDA=21, SCL=22, VCC=3.3V, GND)");
  Serial.println("ms,temp_c,hum_pct,pres_hpa,anomalias,envio_ok");

  tUltEnvio = millis() - PERIODO_MS;   // primera lectura inmediata
  nodoVigilanteIniciar();   // reinicio automático si el loop se traba > 5 s
}

void loop() {
  unsigned long ahora = millis();
  if (ahora - tUltEnvio < PERIODO_MS) return;
  tUltEnvio = ahora;

  if (!sensorOk && ahora - tUltReintento > 10000) {
    tUltReintento = ahora;
    sensorOk = iniciarSensor();
  }

  float t, h, p;
  if (sensorOk && leer(t, h, p)) {
    fallosSeguidos = 0;
    enviar(t, h, p, evaluar(t, h));
  } else {
    fallosSeguidos++;
    uint8_t an = (fallosSeguidos >= FALLOS_PARA_ALARMA || !sensorOk) ? AMB_BIT_FALLO : 0;
    enviar(NAN, NAN, NAN, an);
    if (fallosSeguidos >= FALLOS_PARA_ALARMA) sensorOk = false;   // reintentar iniciarlo
  }
}
