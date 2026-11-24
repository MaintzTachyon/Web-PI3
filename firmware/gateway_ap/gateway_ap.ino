// Gateway ESP32 v5 — Opción B (sin broker ni internet)
// ESP-NOW (7 nodos) -> JSON -> memoria flash (LittleFS) -> laptop por Wi-Fi (HTTP)
//
// El gateway crea su propia red Wi-Fi. La laptop se conecta a ella y:
//   - ve las mediciones en vivo en http://192.168.4.1
//   - descarga los datos guardados con laptop_descarga.py (o desde el navegador)
// Los datos se guardan en el ESP32 aunque la laptop no esté conectada.
//
// Basado en gateway.ino (código de otro grupo del curso PI3): mismo paquetes.h y mismo JSON.
#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <LittleFS.h>
#include <time.h>
#include <sys/time.h>
#include <stdarg.h>
#include <esp_system.h>
#include "paquetes.h"

// ================= CONFIGURACIÓN =================
#define MODO_AP 1   // 1: el gateway crea su propia red (sin router)
                    // 0: el gateway se conecta a una red existente y la laptop entra por esa red

const char*   AP_SSID  = "GEMELO-L419";   // red que crea el gateway (poner este nombre en SSID_ROUTER de los nodos)
const char*   AP_PASS  = "gemelo2026";    // mínimo 8 caracteres
const uint8_t AP_CANAL = 1;               // igual a CANAL_DEFECTO de los nodos

const char* STA_SSID = "UTEC Proyectos";  // solo si MODO_AP = 0 (red de 2.4 GHz)
const char* STA_PASS = "TU_CLAVE";

const char* NOMBRE_MDNS = "gemelo-gateway";   // también accesible como http://gemelo-gateway.local

// Almacenamiento: dos archivos que rotan; al llenarse se descarta lo más antiguo
const size_t   MAX_ARCHIVO  = 600 * 1024;   // bytes por archivo (~1.2 MB en total)
const uint32_t FLUSH_MS     = 5000;         // escribir en flash cada 5 s (cuida la memoria)
const size_t   FLUSH_BYTES  = 4096;         // ... o cuando se acumulen 4 KB
const char*    ARCH_ACT = "/datos_act.jsonl";
const char*    ARCH_ANT = "/datos_ant.jsonl";

// ================= COLA DE RECEPCIÓN =================
struct Mensaje {
  uint8_t  mac[6];
  uint8_t  datos[64];
  int      len;
  int64_t  ts_ms;   // hora UTC de recepción (0 si aún no hay hora)
  uint32_t gw_ms;   // millis() del gateway al recibir
};
QueueHandle_t cola;
volatile uint32_t descartados = 0;

// ================= ESTADO =================
WebServer server(80);
uint32_t ultimoSeq[256];
bool     visto[256];
uint32_t perdidos[256];
uint32_t vistoMs[256];
String   ultimo[256];         // último JSON por nodo (para la vista en vivo)
uint32_t proximoId = 1;       // id correlativo de cada registro guardado
String   pendiente;           // registros aún no escritos en flash
uint32_t tFlush = 0;
bool     fsOk = false;
bool     horaOk = false;
bool     enDescarga = false;  // mientras se lee la flash no se escribe en ella
bool     restaurado[256];     // último dato recuperado de la flash tras un reinicio (aún sin datos nuevos)
const char* motivoReinicio = "?";

// ================= TEXTOS =================
const char* const NIVEL_CO2[] = {"NORMAL", "ALERTA", "CRITICO", "CALENTANDO", "SIN_DATO"};
const char* const AN_CO2[] = {"FALLO_SENSOR", "CO2_PICO_RAPIDO", "CO2_ALERTA_VENTILACION", "CO2_CRITICO"};
const char* const AN_AUD[] = {"FALLO_AUDIO", "RUIDO_IMPACTO", "RUIDO_FUERTE_SOSTENIDO", "RUIDO_MECANICO_CONSTANTE"};
const char* const AN_TER[] = {"FALLO_SENSOR", "CONTEO_CORREGIDO", "OBJETO_ESTATICO"};
const char* const AN_MAG[] = {"FALLO_SENSOR", "PUERTA_ABIERTA_PROLONGADA"};
const char* const AN_AMB[] = {"FALLO_SENSOR", "TEMP_FUERA_CONFORT", "HUMEDAD_ALTA", "CAMBIO_RAPIDO_TEMP"};
const char* const AN_LUZ[] = {"FALLO_SENSOR", "ILUMINACION_BAJA"};
const char* const AN_GAS[] = {"FALLO_SENSOR", "GAS_DETECTADO"};

// ================= JSON MÍNIMO (igual que gateway.ino) =================
struct Json {
  char b[600];
  size_t n = 0;
  bool primero = true;
  void add(const char* fmt, ...) {
    if (n >= sizeof(b)) return;
    va_list a; va_start(a, fmt);
    n += vsnprintf(b + n, sizeof(b) - n, fmt, a);
    va_end(a);
  }
  void clave(const char* k) { add(primero ? "\"%s\":" : ",\"%s\":", k); primero = false; }
  void num(const char* k, long long v) { clave(k); add("%lld", v); }
  void flo(const char* k, float v, int d) { clave(k); if (isnan(v)) add("null"); else add("%.*f", d, v); }
  void str(const char* k, const char* v) { clave(k); add("\"%s\"", v); }
  void nul(const char* k) { clave(k); add("null"); }
};

void anomalias(Json& j, uint8_t bits, const char* const nombres[], int nb) {
  j.clave("anomalias");
  j.add("\"");
  bool primera = true;
  for (int i = 0; i < nb; i++) {
    if (bits & (1 << i)) { j.add(primera ? "%s" : "|%s", nombres[i]); primera = false; }
  }
  if (primera) j.add("NINGUNA");
  j.add("\"");
  j.num("anom_bits", bits);
}

int64_t ahoraMs() {
  struct timeval tv;
  gettimeofday(&tv, nullptr);
  if (tv.tv_sec < 1700000000) return 0;   // aún sin hora
  return (int64_t)tv.tv_sec * 1000 + tv.tv_usec / 1000;
}

// ================= CALLBACK ESP-NOW =================
#if ESP_IDF_VERSION_MAJOR >= 5
void alRecibir(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
  const uint8_t *mac = info->src_addr;
#else
void alRecibir(const uint8_t *mac, const uint8_t *data, int len) {
#endif
  if (len <= 0 || len > (int)sizeof(Mensaje::datos)) { descartados = descartados + 1; return; }
  Mensaje m;
  memcpy(m.mac, mac, 6);
  memcpy(m.datos, data, len);
  m.len   = len;
  m.ts_ms = ahoraMs();
  m.gw_ms = millis();
  if (xQueueSend(cola, &m, 0) != pdTRUE) descartados = descartados + 1;
}

// ================= ALMACENAMIENTO =================
// Lee el último "id" guardado para no repetir ids tras un reinicio
uint32_t leerUltimoId(const char* ruta) {
  File f = LittleFS.open(ruta, "r");
  if (!f) return 0;
  size_t sz = f.size();
  if (sz == 0) { f.close(); return 0; }
  size_t desde = sz > 700 ? sz - 700 : 0;
  f.seek(desde);
  String cola_ = f.readString();
  f.close();
  int p = cola_.lastIndexOf("{\"id\":");
  if (p < 0) return 0;
  return (uint32_t)strtoul(cola_.c_str() + p + 6, nullptr, 10);
}

void rotarSiHaceFalta() {
  File f = LittleFS.open(ARCH_ACT, "r");
  size_t sz = f ? f.size() : 0;
  if (f) f.close();
  if (sz < MAX_ARCHIVO) return;
  LittleFS.remove(ARCH_ANT);
  LittleFS.rename(ARCH_ACT, ARCH_ANT);
  Serial.println("# almacenamiento: archivo rotado (se descartaron los datos más antiguos)");
}

void escribirPendiente() {
  tFlush = millis();
  if (!fsOk || pendiente.length() == 0) return;
  rotarSiHaceFalta();
  File f = LittleFS.open(ARCH_ACT, "a");
  if (!f) { Serial.println("# ERROR: no se pudo abrir el archivo de datos"); return; }
  f.print(pendiente);
  f.close();
  pendiente = "";
}

void guardar(const char* json) {
  pendiente += json;
  pendiente += '\n';
  if (!enDescarga && pendiente.length() >= FLUSH_BYTES) escribirPendiente();
}

// ================= PROCESAR PAQUETE (como gateway.ino + id y gw_ms) =================
void procesar(const Mensaje& m) {
  if (m.len < (int)sizeof(Cabecera)) { Serial.println("# paquete demasiado corto"); return; }
  Cabecera h;
  memcpy(&h, m.datos, sizeof(h));
  if (h.version != PROTO_VERSION) { Serial.printf("# version de protocolo %u desconocida\n", h.version); return; }

  uint8_t id = h.nodo_id;
  if (visto[id] && h.seq > ultimoSeq[id] + 1) perdidos[id] += h.seq - ultimoSeq[id] - 1;
  visto[id] = true;
  ultimoSeq[id] = h.seq;
  vistoMs[id] = m.gw_ms;

  char mac[18];
  snprintf(mac, sizeof(mac), "%02X:%02X:%02X:%02X:%02X:%02X",
           m.mac[0], m.mac[1], m.mac[2], m.mac[3], m.mac[4], m.mac[5]);

  Json j;
  j.add("{");
  j.num("id", proximoId);
  j.num("nodo", id);
  j.str("mac", mac);
  j.num("seq", h.seq);
  if (m.ts_ms) j.num("ts", m.ts_ms); else j.nul("ts");
  j.num("gw_ms", m.gw_ms);
  j.num("uptime_ms", h.uptime_ms);
  j.num("perdidos", perdidos[id]);

  if (h.tipo == TIPO_CO2 && m.len == (int)sizeof(PaqueteCO2)) {
    PaqueteCO2 p; memcpy(&p, m.datos, sizeof(p));
    j.str("tipo", "co2");
    j.num("co2_ppm", p.co2_ppm);
    j.num("delta_30s", p.delta_30s);
    if (p.temp_c == TEMP_SIN_DATO) j.nul("temp_c"); else j.num("temp_c", p.temp_c);
    j.num("calentando", p.calentando);
    j.str("nivel", p.nivel < 5 ? NIVEL_CO2[p.nivel] : "DESCONOCIDO");
    anomalias(j, p.anomalias, AN_CO2, 4);
  } else if (h.tipo == TIPO_AUDIO && m.len == (int)sizeof(PaqueteAudio)) {
    PaqueteAudio p; memcpy(&p, m.datos, sizeof(p));
    j.str("tipo", "audio");
    j.flo("leq_db", p.leq_db, 1);
    j.flo("lmax_db", p.lmax_db, 1);
    j.flo("pico_db", p.pico_db, 1);
    j.flo("base_db", p.base_db, 1);
    j.flo("freq_dom_hz", p.freq_dom_hz, 0);
    j.flo("tonal", p.tonal, 2);
    j.num("bloques_fuertes", p.bloques_fuertes);
    j.num("calibrando", p.calibrando);
    anomalias(j, p.anomalias, AN_AUD, 4);
  } else if (h.tipo == TIPO_TERMICO && m.len == (int)sizeof(PaqueteTermico)) {
    PaqueteTermico p; memcpy(&p, m.datos, sizeof(p));
    j.str("tipo", "termico");
    j.num("entradas", p.entradas);
    j.num("salidas", p.salidas);
    j.num("ocupacion_est", p.ocupacion_est);
    j.num("personas_en_vista", p.personas_en_vista);
    j.num("cruces_dudosos", p.cruces_dudosos);
    j.flo("t_fondo", p.t_fondo, 2);
    j.flo("t_max", p.t_max, 2);
    j.num("calibrando", p.calibrando);
    anomalias(j, p.anomalias, AN_TER, 3);
  } else if (h.tipo == TIPO_MAGNETICO && m.len == (int)sizeof(PaqueteMagnetico)) {
    PaqueteMagnetico p; memcpy(&p, m.datos, sizeof(p));
    j.str("tipo", "magnetico");
    j.num("puerta_abierta", p.puerta_abierta);
    j.num("aperturas", p.aperturas);
    j.flo("seg_abierta", p.seg_abierta, 1);
    j.num("campo_raw", p.campo_raw);
    anomalias(j, p.anomalias, AN_MAG, 2);
  } else if (h.tipo == TIPO_AMBIENTE && m.len == (int)sizeof(PaqueteAmbiente)) {
    PaqueteAmbiente p; memcpy(&p, m.datos, sizeof(p));
    j.str("tipo", "ambiente");
    j.flo("temp_c", p.temp_c, 2);
    j.flo("hum_pct", p.hum_pct, 1);
    j.flo("pres_hpa", p.pres_hpa, 2);
    anomalias(j, p.anomalias, AN_AMB, 4);
  } else if (h.tipo == TIPO_LUZ && m.len == (int)sizeof(PaqueteLuz)) {
    PaqueteLuz p; memcpy(&p, m.datos, sizeof(p));
    j.str("tipo", "luz");
    j.flo("lux", p.lux, 1);
    j.flo("lux_min", p.lux_min, 1);
    j.flo("lux_max", p.lux_max, 1);
    j.flo("lux_mesa_est", p.lux_mesa_est, 1);
    j.num("luces_cambio", p.luces_cambio);
    anomalias(j, p.anomalias, AN_LUZ, 2);
  } else if (h.tipo == TIPO_GAS && m.len == (int)sizeof(PaqueteGas)) {
    PaqueteGas p; memcpy(&p, m.datos, sizeof(p));
    j.str("tipo", "gas");
    j.flo("v_ao", p.v_ao, 3);
    j.flo("rs_r0", p.rs_r0, 3);
    j.num("do_alarma", p.do_alarma);
    j.num("calentando", p.calentando);
    anomalias(j, p.anomalias, AN_GAS, 2);
  } else {
    Serial.printf("# paquete invalido: tipo=%u len=%d (de %s)\n", h.tipo, m.len, mac);
    return;
  }
  j.add("}");

  proximoId++;
  Serial.println(j.b);
  ultimo[id] = j.b;
  restaurado[id] = false;
  guardar(j.b);
}

// Tras un reinicio, recupera de la flash el último mensaje de cada nodo para que la
// tabla no quede vacía (se muestran como "antes del reinicio" hasta que llegue un dato nuevo).
void restaurarUltimos() {
  for (const char* ruta : {ARCH_ANT, ARCH_ACT}) {
    File f = LittleFS.open(ruta, "r");
    if (!f) continue;
    size_t sz = f.size();
    if (sz > 16384) { f.seek(sz - 16384); f.readStringUntil('\n'); }
    while (f.available()) {
      String l = f.readStringUntil('\n');
      int p = l.indexOf(",\"nodo\":");
      if (!l.startsWith("{\"id\":") || p < 0) continue;
      int n = atoi(l.c_str() + p + 8);
      if (n < 0 || n > 255) continue;
      ultimo[n] = l;
      restaurado[n] = true;
    }
    f.close();
  }
}

// Posición del primer registro con id > desde. Búsqueda binaria: los ids crecen en el
// archivo, así no hay que leerlo entero en cada consulta (eso congelaba el servidor).
size_t buscarPos(File& f, uint32_t desde) {
  size_t lo = 0, hi = f.size();
  while (hi - lo > 1024) {
    size_t mid = lo + (hi - lo) / 2;
    f.seek(mid);
    f.readStringUntil('\n');                    // descartar la línea cortada
    if (!f.available()) { hi = mid; continue; }
    String l = f.readStringUntil('\n');
    uint32_t id = l.startsWith("{\"id\":") ? strtoul(l.c_str() + 6, nullptr, 10) : 0;
    if (id <= desde) lo = mid; else hi = mid;
  }
  return lo;
}

// ================= SERVIDOR WEB =================
const char PAGINA[] PROGMEM = R"HTML(<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Gateway Gemelo L419</title>
<style>body{font-family:system-ui,sans-serif;margin:16px;color:#222}h1{font-size:20px}
table{border-collapse:collapse;width:100%;font-size:13px}td,th{border:1px solid #ccc;padding:4px 6px;text-align:left;vertical-align:top}
th{background:#1f3864;color:#fff}.ok{color:#2e7d32}.mal{color:#c62828}code{font-size:12px;word-break:break-all}
a.b{display:inline-block;margin:6px 8px 6px 0;padding:6px 10px;background:#1f3864;color:#fff;border-radius:4px;text-decoration:none}</style></head>
<body><h1>Gateway — Gemelo digital L419</h1><div id="vivo">Conectando…</div><div id="estado">Cargando…</div>
<p><a class="b" href="/api/datos?desde=0&max=1000000&descargar=1">Descargar todo (JSONL)</a>
<a class="b" href="/api/estado">Estado (JSON)</a></p>
<table><thead><tr><th>Nodo</th><th>Tipo</th><th>Hace</th><th>Anomalías</th><th>Último mensaje</th></tr></thead><tbody id="t"></tbody></table>
<script>
// Una consulta a la vez, con tiempo límite: si el gateway tarda o la señal es débil,
// la consulta se cancela a los 4 s y se reintenta, sin acumular peticiones colgadas.
let ultOk=0;
async function pedir(url){
 const c=new AbortController(), to=setTimeout(()=>c.abort(),4000);
 try{ const r=await fetch(url,{signal:c.signal,cache:'no-store'}); return await r.json(); }
 finally{ clearTimeout(to); }
}
function enviarHora(){ pedir('/api/hora?epoch_ms='+Date.now()).catch(()=>{}); }
async function act(){try{
 const e=await pedir('/api/estado');
 if(!e.hora_ok) enviarHora();   // el gateway se reinició y perdió la hora
 document.getElementById('estado').innerHTML='Registros guardados: <b>'+e.id_ultimo+'</b> · Flash: '+Math.round(e.fs_usado/1024)+' / '+Math.round(e.fs_total/1024)+' KB · Hora: '+(e.hora_ok?'<span class=ok>OK</span>':'<span class=mal>sin hora</span>')+' · Descartados: '+e.descartados+
  '<br>Gateway encendido hace <b>'+Math.floor(e.encendido_s/60)+' min</b> · Último reinicio: <span class='+(e.reinicio.indexOf('BAJO')>=0||e.reinicio.indexOf('fallo')>=0||e.reinicio.indexOf('watchdog')>=0?'mal':'ok')+'>'+e.reinicio+'</span> · Memoria libre: '+Math.round(e.heap_libre/1024)+' KB';
 const u=await pedir('/api/ultimos');
 document.getElementById('t').innerHTML=u.map(r=>'<tr><td>'+r.nodo+'</td><td>'+r.tipo+'</td><td'+(r.hace_s<0||r.hace_s>30?' class=mal':'')+'>'+(r.hace_s<0?'antes del reinicio':r.hace_s+' s')+'</td><td>'+r.anomalias+'</td><td><code>'+JSON.stringify(r.msg)+'</code></td></tr>').join('');
 ultOk=Date.now();
}catch(x){ /* sin respuesta: se conserva la tabla y el indicador muestra "Reconectando" */ }
 setTimeout(act,2000);   // la siguiente consulta solo cuando terminó la anterior
}
// Indicador: distingue si falla la conexión con el gateway o si es un nodo el que no envía
setInterval(()=>{
 const v=document.getElementById('vivo');
 if(!ultOk){ v.innerHTML='<span class=mal>● Conectando con el gateway…</span>'; return; }
 const s=Math.round((Date.now()-ultOk)/1000);
 v.innerHTML= s<=6 ? '<span class=ok>● En vivo</span> · actualizado hace '+s+' s'
   : '<span class=mal>● Reconectando…</span> · sin respuesta del gateway hace '+s+' s (señal Wi-Fi débil o gateway ocupado)';
},1000);
enviarHora();act();
</script></body></html>)HTML";

// Permite que una interfaz web servida desde otro origen (p. ej. localhost) lea la API
void cors() { server.sendHeader("Access-Control-Allow-Origin", "*"); }

void hRaiz() { server.send_P(200, "text/html; charset=utf-8", PAGINA); }

void hEstado() {
  cors();
  String s = "{\"gw_ms\":" + String(millis());
  s += ",\"ts\":" + String((long long)ahoraMs());
  s += ",\"hora_ok\":" + String(ahoraMs() ? "true" : "false");
  s += ",\"id_ultimo\":" + String(proximoId - 1);
  s += ",\"pendientes_ram\":" + String(pendiente.length());
  s += ",\"fs_usado\":" + String(fsOk ? LittleFS.usedBytes() : 0);
  s += ",\"fs_total\":" + String(fsOk ? LittleFS.totalBytes() : 0);
  s += ",\"descartados\":" + String(descartados);
  s += ",\"encendido_s\":" + String(millis() / 1000);
  s += ",\"reinicio\":\"" + String(motivoReinicio) + "\"";
  s += ",\"heap_libre\":" + String(ESP.getFreeHeap());
  s += ",\"laptops\":" + String(MODO_AP ? WiFi.softAPgetStationNum() : -1);
  s += ",\"modo\":\"" + String(MODO_AP ? "AP" : "STA") + "\"}";
  server.send(200, "application/json", s);
}

void hUltimos() {
  cors();
  String s = "[";
  bool primero = true;
  for (int id = 0; id < 256; id++) {
    if (ultimo[id].length() == 0) continue;
    int p = ultimo[id].indexOf("\"tipo\":\"");
    String tipo = p >= 0 ? ultimo[id].substring(p + 8, ultimo[id].indexOf('"', p + 8)) : "?";
    int a = ultimo[id].indexOf("\"anomalias\":\"");
    String an = a >= 0 ? ultimo[id].substring(a + 13, ultimo[id].indexOf('"', a + 13)) : "";
    if (!primero) s += ",";
    primero = false;
    // hace_s = -1: dato recuperado de antes del último reinicio (todavía no llegó uno nuevo)
    long hace = restaurado[id] ? -1 : (long)((millis() - vistoMs[id]) / 1000);
    s += "{\"nodo\":" + String(id) + ",\"tipo\":\"" + tipo + "\",\"hace_s\":" + String(hace) +
         ",\"anomalias\":\"" + an + "\",\"msg\":" + ultimo[id] + "}";
  }
  s += "]";
  server.send(200, "application/json", s);
}

// La laptop envía su hora (ms Unix) para fechar los registros cuando no hay NTP
void hHora() {
  cors();
  if (server.hasArg("epoch_ms")) {
    long long ms = atoll(server.arg("epoch_ms").c_str());
    if (ms > 1700000000000LL) {
      struct timeval tv = {(time_t)(ms / 1000), (suseconds_t)((ms % 1000) * 1000)};
      settimeofday(&tv, nullptr);
      if (!horaOk) Serial.println("# hora recibida desde la laptop");
      horaOk = true;
    }
  }
  server.send(200, "application/json", "{\"ts\":" + String((long long)ahoraMs()) + "}");
}

// Devuelve en formato JSONL los registros con id > desde (máximo "max" líneas)
void hDatos() {
  cors();
  escribirPendiente();
  uint32_t desde = server.hasArg("desde") ? strtoul(server.arg("desde").c_str(), nullptr, 10) : 0;
  uint32_t maximo = server.hasArg("max") ? strtoul(server.arg("max").c_str(), nullptr, 10) : 2000;
  if (server.hasArg("descargar")) server.sendHeader("Content-Disposition", "attachment; filename=\"gemelo_l419.jsonl\"");
  server.setContentLength(CONTENT_LENGTH_UNKNOWN);
  server.send(200, "application/x-ndjson", "");
  enDescarga = true;
  uint32_t enviados = 0;
  String bloque;
  for (const char* ruta : {ARCH_ANT, ARCH_ACT}) {
    File f = LittleFS.open(ruta, "r");
    if (!f) continue;
    size_t pos = buscarPos(f, desde);
    f.seek(pos);
    if (pos > 0) f.readStringUntil('\n');      // empezar en una línea completa
    while (f.available() && enviados < maximo) {
      String linea = f.readStringUntil('\n');
      if (!linea.startsWith("{\"id\":")) continue;
      uint32_t id = strtoul(linea.c_str() + 6, nullptr, 10);
      if (id <= desde) continue;
      bloque += linea;
      bloque += '\n';
      enviados++;
      if (bloque.length() > 2048) { server.sendContent(bloque); bloque = ""; }
      if ((enviados & 63) == 0) {   // no descuidar la recepción durante descargas largas
        Mensaje m;
        while (xQueueReceive(cola, &m, 0) == pdTRUE) procesar(m);
      }
    }
    f.close();
  }
  if (bloque.length()) server.sendContent(bloque);
  server.sendContent("");
  enDescarga = false;
}

// Borra lo guardado (usar solo después de haber descargado en la laptop)
void hBorrar() {
  cors();
  if (server.arg("confirmar") != "si") {
    server.send(400, "text/plain", "Agregue ?confirmar=si para borrar los datos del gateway");
    return;
  }
  pendiente = "";
  LittleFS.remove(ARCH_ANT);
  LittleFS.remove(ARCH_ACT);
  server.send(200, "text/plain", "Datos borrados");
  Serial.println("# datos borrados a pedido de la laptop");
}

// ================= RED =================
void iniciarRed() {
#if MODO_AP
  // AP + STA: la laptop se conecta al AP y ESP-NOW sigue recibiendo en la MAC STA
  // (la que tienen los nodos en MAC_GATEWAY).
  WiFi.mode(WIFI_AP_STA);
  WiFi.setSleep(false);
  WiFi.softAP(AP_SSID, AP_PASS, AP_CANAL);
  // Máximo alcance: potencia al máximo y canal de 20 MHz (HT20). Un canal de 40 MHz
  // tiene menos alcance y sufre más interferencia de las redes vecinas.
  WiFi.setTxPower(WIFI_POWER_19_5dBm);
  esp_wifi_set_bandwidth(WIFI_IF_AP, WIFI_BW_HT20);
  esp_wifi_set_bandwidth(WIFI_IF_STA, WIFI_BW_HT20);
  Serial.printf("# Red propia: SSID=%s  canal=%d  IP=%s\n", AP_SSID, AP_CANAL, WiFi.softAPIP().toString().c_str());
#else
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.setAutoReconnect(true);
  WiFi.begin(STA_SSID, STA_PASS);
  Serial.print("# Conectando a WiFi");
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.printf("\n# WiFi OK  IP=%s  canal=%d\n", WiFi.localIP().toString().c_str(), WiFi.channel());
  configTime(0, 0, "pool.ntp.org", "time.google.com");
#endif
}

// Motivo del último reinicio del gateway (para diagnosticar cortes de energía o fallos)
const char* textoReinicio(int r) {
  switch (r) {
    case ESP_RST_POWERON:   return "encendido normal";
    case ESP_RST_SW:        return "reinicio por software";
    case ESP_RST_PANIC:     return "fallo del programa (panic)";
    case ESP_RST_INT_WDT:
    case ESP_RST_TASK_WDT:
    case ESP_RST_WDT:       return "watchdog (programa bloqueado)";
    case ESP_RST_BROWNOUT:  return "BAJO VOLTAJE (brownout): revisar cable/fuente USB";
    case ESP_RST_EXT:       return "boton EN / reset externo";
    case ESP_RST_DEEPSLEEP: return "salida de deep sleep";
    default:                return "desconocido";
  }
}

// ================= SETUP / LOOP =================
void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("# Gateway ESP32 v5 (opcion B: almacenamiento local + laptop por Wi-Fi)");
  motivoReinicio = textoReinicio((int)esp_reset_reason());
  Serial.printf("# Motivo del ultimo reinicio: %s\n", motivoReinicio);

  cola = xQueueCreate(64, sizeof(Mensaje));

  fsOk = LittleFS.begin(true);   // true: formatea la primera vez
  if (fsOk) {
    uint32_t ult = leerUltimoId(ARCH_ACT);
    if (ult == 0) ult = leerUltimoId(ARCH_ANT);
    proximoId = ult + 1;
    restaurarUltimos();
    Serial.printf("# LittleFS OK: %u / %u KB usados, ultimo id = %u\n",
                  (unsigned)(LittleFS.usedBytes() / 1024), (unsigned)(LittleFS.totalBytes() / 1024), (unsigned)ult);
  } else {
    Serial.println("# ERROR: LittleFS no disponible; solo vista en vivo");
  }

  iniciarRed();

  if (esp_now_init() != ESP_OK) {
    Serial.println("# ERROR: no se pudo iniciar ESP-NOW");
    while (1) delay(1000);
  }
  esp_now_register_recv_cb(alRecibir);

  server.on("/", hRaiz);
  server.on("/api/estado", hEstado);
  server.on("/api/ultimos", hUltimos);
  server.on("/api/hora", hHora);
  server.on("/api/datos", hDatos);
  server.on("/api/borrar", hBorrar);
  server.begin();
  if (MDNS.begin(NOMBRE_MDNS)) MDNS.addService("http", "tcp", 80);

  Serial.printf("# Listo. MAC STA (para los nodos)=%s  MAC AP=%s\n",
                WiFi.macAddress().c_str(), WiFi.softAPmacAddress().c_str());
}

void loop() {
  Mensaje m;
  while (xQueueReceive(cola, &m, 0) == pdTRUE) procesar(m);

  server.handleClient();
  if (millis() - tFlush > FLUSH_MS) escribirPendiente();

  static unsigned long tEstado = 0;
  if (millis() - tEstado > 30000) {
    tEstado = millis();
    Serial.printf("# estado: registros=%u  laptops conectadas=%d  hora=%s  descartados=%lu\n",
                  (unsigned)(proximoId - 1), MODO_AP ? WiFi.softAPgetStationNum() : -1,
                  ahoraMs() ? "OK" : "NO", (unsigned long)descartados);
  }
  delay(2);
}
