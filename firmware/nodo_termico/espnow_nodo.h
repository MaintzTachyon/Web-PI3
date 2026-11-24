// espnow_nodo.h — Envío ESP-NOW desde un nodo sensor hacia el gateway
// v2: radio sin ahorro de energía, potencia moderada (menos picos de corriente con
//     batería), re-escaneo de canal corto y limitado, y vigilante (watchdog) del loop.
#pragma once
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include "paquetes.h"

// Potencia de transmisión: máxima (19.5 dBm) para cubrir toda el aula. Con 11 dBm los nodos
// lejos del gateway perdían la conexión. Con batería baja puede bajarse a WIFI_POWER_15dBm.
#ifndef ESPNOW_TX_POWER
#define ESPNOW_TX_POWER WIFI_POWER_19_5dBm
#endif
const unsigned long REESCANEO_MIN_MS = 30000;   // como mucho un re-escaneo de canal cada 30 s

static uint8_t       g_macGateway[6];
static const char*   g_ssid = nullptr;
static uint8_t       g_canal = 1;
static uint32_t      g_seq = 0;
static volatile bool g_ultimoOk = false;
static volatile int  g_fallosSeguidos = 0;
static unsigned long g_tReescaneo = 0;

// Confirmación de entrega (ACK de capa MAC).
// La firma del callback cambió en ESP-IDF 5.5 (core Arduino 3.3+).
#if ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(5, 5, 0)
static void alEnviar(const esp_now_send_info_t *info, esp_now_send_status_t st) {
#else
static void alEnviar(const uint8_t *mac, esp_now_send_status_t st) {
#endif
  g_ultimoOk = (st == ESP_NOW_SEND_SUCCESS);
  if (g_ultimoOk) g_fallosSeguidos = 0;
  else            g_fallosSeguidos = g_fallosSeguidos + 1;
}

// Busca el canal de la red del gateway. Escaneo corto (100 ms por canal, ~1.3 s en total)
// y filtrado por nombre, para no bloquear el nodo varios segundos.
static int g_rssi = 0;   // señal del gateway en el último escaneo (dBm; 0 = no encontrado)
static uint8_t buscarCanal(const char* ssid, uint8_t porDefecto) {
  int n = WiFi.scanNetworks(false, false, false, 100, 0, ssid);
  uint8_t canal = porDefecto;
  g_rssi = 0;
  for (int i = 0; i < n; i++) {
    if (WiFi.SSID(i) == ssid) { canal = WiFi.channel(i); g_rssi = WiFi.RSSI(i); break; }
  }
  WiFi.scanDelete();
  return canal;
}

// Imprime qué tan bien se recibe al gateway (para ubicar el nodo)
static void informarSenal(const char* ssid) {
  if (g_rssi == 0)
    Serial.printf("# AVISO: no se encontro la red %s. Gateway apagado o MUY lejos.\n", ssid);
  else
    Serial.printf("# Senal del gateway: %d dBm -> %s\n", g_rssi,
                  g_rssi > -70 ? "buena" : g_rssi > -80 ? "regular (acercar el nodo)"
                                                         : "MUY DEBIL: acercar el nodo al gateway");
}

static void fijarCanal(uint8_t canal) {
  esp_wifi_set_promiscuous(true);
  esp_wifi_set_channel(canal, WIFI_SECOND_CHAN_NONE);
  esp_wifi_set_promiscuous(false);
  g_canal = canal;
}

static bool espnowIniciar(const uint8_t mac[6], const char* ssid, uint8_t canalDefecto) {
  memcpy(g_macGateway, mac, 6);
  g_ssid = ssid;

  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);                    // radio siempre activa: no perder ACK ni canal
  WiFi.disconnect();                       // no se conecta al router, solo usa su canal
  WiFi.setTxPower(ESPNOW_TX_POWER);
  fijarCanal(buscarCanal(ssid, canalDefecto));
  informarSenal(ssid);
  g_tReescaneo = millis();

  if (esp_now_init() != ESP_OK) return false;
  esp_now_register_send_cb(alEnviar);

  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, mac, 6);
  peer.channel = 0;                        // 0 = canal actual
  peer.encrypt = false;
  return esp_now_add_peer(&peer) == ESP_OK;
}

// Vigilante: si el loop() se queda trabado más de ~5 s (sensor colgado, bus I2C
// bloqueado), el ESP32 se reinicia solo y el nodo vuelve a enviar.
// Llamar al FINAL de setup().
static void nodoVigilanteIniciar() {
  enableLoopWDT();
}

static void llenarCabecera(Cabecera &h, uint8_t tipo, uint8_t nodoId) {
  h.version   = PROTO_VERSION;
  h.tipo      = tipo;
  h.nodo_id   = nodoId;
  h.seq       = g_seq++;
  h.uptime_ms = millis();
}

static void espnowEnviar(const void* datos, size_t len) {
  esp_now_send(g_macGateway, (const uint8_t*)datos, len);

  // Muchos fallos seguidos: quizá cambió el canal o el gateway se reinició.
  // Re-escanear, pero como mucho cada REESCANEO_MIN_MS para no congelar el nodo.
  if (g_fallosSeguidos >= 10 && g_ssid && millis() - g_tReescaneo >= REESCANEO_MIN_MS) {
    g_fallosSeguidos = 0;
    g_tReescaneo = millis();
    fijarCanal(buscarCanal(g_ssid, g_canal));
  }
}
