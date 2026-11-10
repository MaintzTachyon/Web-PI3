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

export function lecturasSinDatos() {
  return [...catalog.values()].map((sensor) => ({
    id: sensor.id, nodo: sensor.nodo, tipo: sensor.medicion ?? sensor.tipo, etiqueta: sensor.etiqueta,
    valor: null, unidad: sensor.variables[sensor.variable_principal]?.unidad ?? "", estado: "sin_datos", actualizado: null,
    variables: Object.fromEntries(Object.entries(sensor.variables).map(([name, variable]) => [name, { valor: null, unidad: variable.unidad, etiqueta: variable.etiqueta }])),
    anomalias: [], diagnostico: {},
  }));
}

/**
 * Renderiza una fila por sensor en el panel de monitorización.
 * No son tarjetas clonadas: filas compactas con jerarquía visual clara.
 * Solo el sensor seleccionado se destaca visualmente.
 */
export function renderSensorList(onSelect) {
  const container = document.querySelector("#sensor-list");
  container.replaceChildren();

  if (readings.size === 0) {
    container.insertAdjacentHTML("beforeend", `<div class="sensor-list-empty">Sin sensores disponibles</div>`);
    return;
  }

  readings.forEach((reading) => {
    const item = document.createElement("article");
    item.className = `sensor-item${reading.id === selectedId ? " selected" : ""}`;
    item.tabIndex = 0;
    item.setAttribute("aria-label", `${reading.etiqueta}: ${formatValue(reading.id, principal(reading), reading.valor)} ${reading.unidad}, ${reading.estado.replace("_", " ")}`);

    const valor = formatValue(reading.id, principal(reading), reading.valor);
    const estadoLabel = reading.estado.replace("_", " ");
    const updated = formatTime(reading.actualizado);

    item.innerHTML = `
      <div class="sensor-item-main">
        <span class="sensor-indicator ${reading.estado}" aria-hidden="true"></span>
        <div class="sensor-info">
          <div class="sensor-name">${reading.etiqueta}</div>
          <div class="sensor-meta">${reading.tipo} · nodo ${reading.nodo}</div>
        </div>
      </div>
      <div class="sensor-reading">
        <span class="sensor-value">${valor}</span>
        <span class="sensor-unit">${reading.unidad}</span>
      </div>
      <span class="sensor-updated">${updated}</span>
    `;

    item.addEventListener("click", () => onSelect(reading.id));
    item.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") onSelect(reading.id);
    });
    container.append(item);
  });
}

export async function selectSensor(id, range = "1h") {
  selectedId = id;
  seleccionarMarcador(id);
  renderSensorList(select);
  renderDetail();
  const reading = readings.get(id);
  if (!reading) return;
  const message = document.querySelector("#chart-message");
  message.textContent = "Cargando historial…";
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
  document.querySelector("#detail-value").textContent = formatValue(selectedId, principal(reading), reading.valor);
  document.querySelector("#detail-unit").textContent = reading.unidad;
  const status = document.querySelector("#detail-status");
  status.className = `status-badge ${reading.estado}`;
  status.textContent = reading.estado.replace("_", " ");
  const variables = document.querySelector("#detail-variables");
  variables.replaceChildren();
  Object.entries(reading.variables ?? {}).forEach(([name, variable]) => {
    const row = document.createElement("div");
    row.className = "variable-row";
    row.innerHTML = `<span class="variable-label">${variable.etiqueta || name}</span><span class="variable-value">${formatValue(selectedId, name, variable.valor)} <small>${variable.unidad}</small></span>`;
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
