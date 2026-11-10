import {
  SENSORES_CONFIG,
} from "./sensores-config.js";

/**
 * Crea los marcadores de sensores dentro del plano SVG a partir de la
 * configuración centralizada (js/sensores-config.js).
 *
 * Mover un sensor de ubicación es editar sus coordenadas (x, y) en ese archivo.
 * No hay que tocar este archivo ni el SVG.
 *
 * @param {Function} onSelect - callback(id) al seleccionar un marcador
 * @param {SVGElement} svg - elemento <svg> del plano
 */
export function configurarPlano(onSelect, svg) {
  const grupo = svg.querySelector("#sensores-marcadores");
  if (!grupo) return;

  grupo.replaceChildren();

  SENSORES_CONFIG.forEach((sensor) => {
    const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
    g.setAttribute("class", "sensor-marker");
    g.setAttribute("data-sensor-id", sensor.id);
    g.setAttribute("tabindex", "0");
    g.setAttribute("role", "button");
    g.setAttribute(
      "aria-label",
      `${sensor.etiqueta} — sensor de ${sensor.tipo}`
    );

    // Anillo exterior (discreto)
    const ring = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    ring.setAttribute("class", "marker-ring");
    ring.setAttribute("cx", sensor.x);
    ring.setAttribute("cy", sensor.y);
    ring.setAttribute("r", "20");

    // Núcleo del marcador (color según estado)
    const core = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    core.setAttribute("class", "marker-core");
    core.setAttribute("cx", sensor.x);
    core.setAttribute("cy", sensor.y);
    core.setAttribute("r", "10");

    // Símbolo del sensor
    const simbolo = document.createElementNS("http://www.w3.org/2000/svg", "text");
    simbolo.setAttribute("class", "symbol");
    simbolo.setAttribute("x", sensor.x);
    simbolo.setAttribute("y", String(sensor.y + 3));
    simbolo.setAttribute("text-anchor", "middle");
    simbolo.textContent = simboloPara(sensor.tipo);

    // Etiqueta discreta debajo
    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("class", "sensor-label");
    label.setAttribute("x", sensor.x);
    label.setAttribute("y", String(sensor.y + 22));
    label.setAttribute("text-anchor", "middle");
    label.textContent = sensor.etiqueta;

    g.append(ring, core, simbolo, label);
    grupo.append(g);

    g.addEventListener("click", () => onSelect(sensor.id));
    g.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        onSelect(sensor.id);
      }
    });
  });
}

function simboloPara(tipo) {
  const simbolos = {
    co2: "CO₂",
    audio: "dB",
    temperatura: "°C",
    humedad: "%",
    luminosidad: "lx",
    presencia: "⌁",
  };
  return simbolos[tipo] || "?";
}

export function seleccionarMarcador(id) {
  document.querySelectorAll(".sensor-marker").forEach((marker) =>
    marker.classList.toggle("selected", marker.dataset.sensorId === id)
  );
}

export function actualizarMarcadores(readings) {
  readings.forEach((reading) => {
    const marker = document.querySelector(
      `[data-sensor-id="${CSS.escape(reading.id)}"]`
    );
    if (!marker) return;
    marker.dataset.state = reading.estado;
    marker.setAttribute(
      "aria-label",
      `${reading.etiqueta}: ${reading.valor ?? "sin datos"} ${reading.unidad}`
    );
  });
}
