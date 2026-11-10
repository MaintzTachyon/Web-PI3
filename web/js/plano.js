import {
  SENSORES_CONFIG,
  obtenerUbicaciones,
} from "./sensores-config.js";

/**
 * Crea los marcadores de sensores dentro del SVG a partir de la configuración
 * centralizada. Las ubicaciones (x, y) viven en js/sensores-config.js: mover un
 * sensor es editar una coordenada ahí, no tocar este archivo ni el SVG.
 *
 * @param {Function} onSelect - callback(id) al seleccionar un marcador
 * @param {HTMLElement} contenedorSVG - elemento <svg> del plano
 */
export function configurarPlano(onSelect, contenedorSVG) {
  const grupo = contenedorSVG.querySelector("#marcadores-sensores");
  if (!grupo) return;

  // Limpiar marcadores previos (por si se vuelve a renderizar)
  grupo.replaceChildren();

  SENSORES_CONFIG.forEach((sensor) => {
    const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
    g.setAttribute("class", "sensor-marker");
    g.setAttribute("data-sensor-id", sensor.id);
    g.setAttribute("tabindex", "0");
    g.setAttribute("role", "button");
    g.setAttribute(
      "aria-label",
      `${sensor.etiqueta} sensor (${sensor.tipo})`
    );

    // Halo exterior
    const halo = document.createElementNS(
      "http://www.w3.org/2000/svg",
      "circle"
    );
    halo.setAttribute("class", "marker-halo");
    halo.setAttribute("cx", sensor.x);
    halo.setAttribute("cy", sensor.y);
    halo.setAttribute("r", "28");

    // Núcleo del marcador
    const core = document.createElementNS(
      "http://www.w3.org/2000/svg",
      "circle"
    );
    core.setAttribute("class", "marker-core");
    core.setAttribute("cx", sensor.x);
    core.setAttribute("cy", sensor.y);
    core.setAttribute("r", "19");

    // Símbolo del sensor
    const simbolo = document.createElementNS(
      "http://www.w3.org/2000/svg",
      "text"
    );
    simbolo.setAttribute("x", sensor.x);
    simbolo.setAttribute("y", sensor.y + 4);
    simbolo.setAttribute("text-anchor", "middle");
    simbolo.textContent = simboloPara(sensor.tipo);

    // Etiqueta debajo del marcador
    const label = document.createElementNS(
      "http://www.w3.org/2000/svg",
      "text"
    );
    label.setAttribute("class", "marker-label");
    label.setAttribute("x", sensor.x);
    label.setAttribute("y", sensor.y + 42);
    label.setAttribute("text-anchor", "middle");
    label.textContent = sensor.etiqueta;

    g.append(halo, core, simbolo, label);
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
    presencia: "↻",
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
