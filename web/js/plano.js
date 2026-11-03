export function configurarPlano(onSelect) {
  document.querySelectorAll(".sensor-marker").forEach((marker) => {
    marker.addEventListener("click", () => onSelect(marker.dataset.sensorId));
    marker.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onSelect(marker.dataset.sensorId); }
    });
  });
}

export function seleccionarMarcador(id) {
  document.querySelectorAll(".sensor-marker").forEach((marker) => marker.classList.toggle("selected", marker.dataset.sensorId === id));
}

export function actualizarMarcadores(readings) {
  readings.forEach((reading) => {
    const marker = document.querySelector(`[data-sensor-id="${CSS.escape(reading.id)}"]`);
    if (marker) { marker.dataset.state = reading.estado; marker.setAttribute("aria-label", `${reading.etiqueta}: ${reading.valor ?? "sin datos"} ${reading.unidad}`); }
  });
}
