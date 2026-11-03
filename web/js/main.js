import { activarDemo, cargarCatalogo, cargarUltimas, desactivarDemo, suscribirStream } from "./datos.js";
import { limpiarGrafico } from "./graficos.js";
import { configurarPlano, actualizarMarcadores } from "./plano.js";
import { getReading, getSelectedId, renderCards, renderDetail, selectSensor, setCatalog, setReadings } from "./sensores.js";

const connection = document.querySelector("#connection-status");
let selectedId;
let cleanupStream;

async function init() {
  try {
    const catalog = await cargarCatalogo();
    setCatalog(catalog.sensores);
    desactivarDemo();
    await refresh();
    cleanupStream = suscribirStream({ onReading: handleReading, onConnection: handleConnection, onError: handleStreamError });
  } catch {
    activarDemo();
    await refresh();
    setConnection("offline", "Modo DEMO · API no disponible");
  }
  configurarPlano(select);
  document.querySelector("#clear-selection").addEventListener("click", clearSelection);
  document.querySelector("#history-range").addEventListener("change", () => selectedId && selectSensor(selectedId, document.querySelector("#history-range").value));
  window.addEventListener("beforeunload", () => cleanupStream?.());
}

async function refresh() {
  const response = await cargarUltimas();
  setReadings(response.sensores);
  document.querySelector("#origin-badge").hidden = response.origen !== "demo";
  renderCards(select);
  actualizarMarcadores(response.sensores);
  document.querySelector("#last-updated").textContent = new Date(response.generado).toLocaleTimeString("es-PE");
  setConnection(response.origen === "demo" ? "partial" : "online", response.origen === "demo" ? "Datos DEMO" : "En línea");
  if (selectedId) renderDetail();
}

function handleReading(reading) {
  setReadings([reading]);
  renderCards(select);
  actualizarMarcadores([reading]);
  document.querySelector("#last-updated").textContent = new Date(reading.actualizado).toLocaleTimeString("es-PE");
  if (selectedId === reading.id) renderDetail();
}

function handleConnection(info) {
  setConnection(info.conexion === "en_linea" ? "online" : info.conexion === "parcial" ? "partial" : "offline", info.conexion.replace("_", " "));
}

function handleStreamError() {
  setConnection("partial", "Reconectando...");
  window.setTimeout(() => refresh().catch(() => {}), 5000);
}

function setConnection(state, label) {
  connection.dataset.state = state;
  document.querySelector("#connection-label").textContent = label;
}

function select(id) {
  selectedId = id;
  selectSensor(id, document.querySelector("#history-range").value);
  renderCards(select);
}

function clearSelection() {
  selectedId = undefined;
  document.querySelector("#detail-empty").hidden = false;
  document.querySelector("#sensor-detail").hidden = true;
  document.querySelectorAll(".sensor-marker").forEach((marker) => marker.classList.remove("selected"));
  limpiarGrafico();
}

init();
