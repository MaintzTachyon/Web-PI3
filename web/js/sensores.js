import { cargarHistorial } from "./datos.js";
import { actualizarGrafico } from "./graficos.js";
import { seleccionarMarcador } from "./plano.js";

let readings = new Map();
let selectedId;
let catalog = new Map();

export function setCatalog(items) { catalog = new Map(items.map((item) => [item.id, item])); }
export function setReadings(items) { items.forEach((item) => readings.set(item.id, item)); }
export function getReading(id) { return readings.get(id); }
export function getSelectedId() { return selectedId; }

// Lecturas vacías a partir del catálogo, para cuando la API responde pero InfluxDB no.
export function lecturasSinDatos() {
  return [...catalog.values()].map((sensor) => ({
    id: sensor.id, nodo: sensor.nodo, tipo: sensor.medicion ?? sensor.tipo, etiqueta: sensor.etiqueta,
    valor: null, unidad: sensor.variables[sensor.variable_principal]?.unidad ?? "", estado: "sin_datos", actualizado: null,
    variables: Object.fromEntries(Object.entries(sensor.variables).map(([name, variable]) => [name, { valor: null, unidad: variable.unidad, etiqueta: variable.etiqueta }])),
    anomalias: [], diagnostico: {},
  }));
}

export function renderCards(onSelect) {
  const container = document.querySelector("#sensor-cards");
  container.replaceChildren();
  readings.forEach((reading) => {
    const card = document.createElement("article");
    card.className = `sensor-card${reading.id === selectedId ? " selected" : ""}`;
    card.tabIndex = 0;
    card.innerHTML = `<div class="sensor-card-header"><span>${reading.tipo.toUpperCase()}</span><span class="status-badge ${reading.estado}">${reading.estado.replace("_", " ")}</span></div><div class="sensor-card-reading"><strong class="sensor-card-value">${formatValue(reading.id, principal(reading), reading.valor)}</strong><span class="sensor-card-unit">${reading.unidad}</span></div><div class="sensor-card-footer"><span>${reading.etiqueta}</span><span>${formatTime(reading.actualizado)}</span></div>`;
    card.addEventListener("click", () => onSelect(reading.id));
    card.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") onSelect(reading.id); });
    container.append(card);
  });
}

export async function selectSensor(id, range = "1h") {
  selectedId = id;
  seleccionarMarcador(id);
  renderDetail();
  const reading = readings.get(id);
  if (!reading) return;
  const message = document.querySelector("#chart-message");
  message.textContent = "Cargando historial...";
  try {
    const history = await cargarHistorial(id, principal(reading), range);
    actualizarGrafico(document.querySelector("#history-chart"), history, reading.etiqueta);
    message.textContent = history.puntos.length ? "" : "No hay datos históricos para este rango.";
  } catch { message.textContent = "No se pudo cargar el historial."; }
}

export function renderDetail() {
  const reading = readings.get(selectedId);
  if (!reading) return;
  document.querySelector("#detail-empty").hidden = true;
  document.querySelector("#sensor-detail").hidden = false;
  document.querySelector("#detail-title").textContent = reading.etiqueta;
  document.querySelector("#detail-meta").textContent = `Nodo ${reading.nodo} · Actualizado ${formatTime(reading.actualizado)}`;
  document.querySelector("#detail-value").textContent = formatValue(reading.id, principal(reading), reading.valor);
  document.querySelector("#detail-unit").textContent = reading.unidad;
  const status = document.querySelector("#detail-status");
  status.className = `status-badge ${reading.estado}`;
  status.textContent = reading.estado.replace("_", " ");
  const variables = document.querySelector("#detail-variables");
  variables.replaceChildren();
  Object.entries(reading.variables ?? {}).forEach(([name, variable]) => {
    const row = document.createElement("div");
    row.className = "variable-row";
    row.innerHTML = `<span class="variable-label">${variable.etiqueta || name}</span><span class="variable-value">${formatValue(reading.id, name, variable.valor)} <small>${variable.unidad}</small></span>`;
    variables.append(row);
  });
  if (reading.anomalias?.length) {
    const row = document.createElement("div");
    row.className = "variable-row";
    const label = document.createElement("span");
    label.className = "variable-label";
    label.textContent = "Anomalías";
    const value = document.createElement("span");
    value.className = "variable-value";
    value.textContent = reading.anomalias.map((item) => item.replaceAll("_", " ").toLowerCase()).join(", ");
    row.append(label, value);
    variables.append(row);
  }
}

function principal(reading) {
  return catalog.get(reading.id)?.variable_principal ?? Object.keys(reading.variables ?? {})[0];
}

function formatValue(id, variable, value) {
  if (typeof value !== "number") return value ?? "—";
  const decimales = catalog.get(id)?.variables?.[variable]?.decimales ?? 1;
  return value.toLocaleString("es-PE", { minimumFractionDigits: decimales, maximumFractionDigits: decimales });
}

function formatTime(value) {
  return value ? new Date(value).toLocaleTimeString("es-PE", { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "sin datos";
}
