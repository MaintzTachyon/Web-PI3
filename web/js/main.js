import { activarDemo, cargarCatalogo, cargarUltimas, desactivarDemo, suscribirStream } from "./datos.js";
import { limpiarGrafico } from "./graficos.js";
import { configurarPlano, actualizarMarcadores, seleccionarMarcador } from "./plano.js";
import {
  completarPendientes,
  descargarReporteCSV,
  lecturasSinDatos,
  limpiarSeleccion,
  renderSensorList,
  renderDetail,
  selectSensor,
  setCatalog,
  setReadings,
} from "./sensores.js";

const floorplan = document.querySelector("#floorplan");
const connection = document.querySelector("#connection-status");

const CONEXION = {
  en_linea: ["online", "En línea"],
  parcial: ["partial", "Conexión parcial"],
  sin_datos: ["offline", "Sin datos de sensores"],
};

let selectedId;
let cleanupStream;
let refreshTimer;

// De dónde lee el backend (GET /api/v1/sensores → fuente).
const FUENTES = {
  gateway: ["Gateway", "Gateway ESP32 (red GEMELO-L419)"],
  real: ["InfluxDB", "InfluxDB mediante API segura"],
  demo: ["Simulador", "Datos simulados (DEMO)"],
};
let fuente = FUENTES.gateway;

async function init() {
  // Los marcadores se dibujan desde la configuración centralizada en sensores-config.js.
  configurarPlano(select, floorplan);

  document.querySelector("#clear-selection").addEventListener("click", clearSelection);
  document.querySelector("#history-range").addEventListener("change", () => {
    if (selectedId) selectSensor(selectedId, document.querySelector("#history-range").value);
  });
  window.addEventListener("beforeunload", () => cleanupStream?.());

  let catalog;
  try {
    catalog = await cargarCatalogo();
  } catch {
    activarDemo();
    document.querySelector("#fuente-label").textContent = "Datos de ejemplo (API no disponible)";
    await refresh();
    setConnection("offline", "Modo DEMO · API no disponible");
    return;
  }
  setCatalog(catalog.sensores);
  fuente = FUENTES[catalog.fuente] ?? FUENTES.gateway;
  document.querySelector("#fuente-label").textContent = fuente[1];
  desactivarDemo();
  try {
    await refresh();
  } catch {
    pintar(lecturasSinDatos());
    setConnection("offline", `${fuente[0]} no disponible`);
  }
  cleanupStream = suscribirStream({ onReading: handleReading, onConnection: handleConnection, onError: handleStreamError });

  // Conectar botón de descarga de reporte CSV
  try {
    const btn = document.querySelector("#descargar-reporte");
    if (btn) {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        descargarReporteCSV();
      });
    }
  } catch {
    // El reporte CSV es opcional; si falla, la web sigue funcionando normalmente
  }
}

async function refresh() {
  const response = await cargarUltimas();
  pintar(response.sensores);
  document.querySelector("#origin-badge").hidden = response.origen !== "demo";
  document.querySelector("#last-updated").textContent = new Date(response.generado).toLocaleTimeString("es-PE");
  if (response.origen === "demo") setConnection("partial", "Datos DEMO");
  else handleConnection({ conexion: conexionDe(response.sensores) });
}

function pintar(lecturas) {
  setReadings(lecturas);
  const pendientes = completarPendientes();
  renderSensorList(select);
  actualizarMarcadores([...lecturas, ...pendientes]);
  if (selectedId) renderDetail();
}

function conexionDe(lecturas) {
  const conDatos = lecturas.filter((reading) => reading.estado !== "sin_datos").length;
  return conDatos && conDatos === lecturas.length ? "en_linea" : conDatos ? "parcial" : "sin_datos";
}

function handleReading(reading) {
  pintar([reading]);
  if (reading.actualizado) document.querySelector("#last-updated").textContent = new Date(reading.actualizado).toLocaleTimeString("es-PE");
}

function handleConnection(info) {
  if (info.influx === "no_disponible") return setConnection("offline", `${fuente[0]} no disponible`);
  const [state, label] = CONEXION[info.conexion] ?? CONEXION.sin_datos;
  setConnection(state, label);
}

function handleStreamError() {
  setConnection("partial", "Reconectando…");
  if (refreshTimer) return;
  refreshTimer = window.setTimeout(() => {
    refreshTimer = undefined;
    refresh().catch(() => {});
  }, 5000);
}

function setConnection(state, label) {
  connection.dataset.state = state;
  document.querySelector("#connection-label").textContent = label;
}

function select(id) {
  selectedId = id;
  seleccionarMarcador(id);
  selectSensor(id, document.querySelector("#history-range").value);
  renderSensorList(select);
}

function clearSelection() {
  selectedId = undefined;
  limpiarSeleccion();
  document.querySelector("#detail-empty").hidden = false;
  document.querySelector("#sensor-detail").hidden = true;
  document.querySelectorAll(".sensor-marker").forEach((marker) => marker.classList.remove("selected"));
  document.querySelectorAll(".sensor-item").forEach((item) => item.classList.remove("selected"));
  limpiarGrafico();
}

init();
